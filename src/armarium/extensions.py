"""Install optional reference files and load vault-local extension declarations."""

import json
import re
import shutil
import tempfile
import tomllib
from dataclasses import dataclass
from importlib.metadata import version
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import NotRequired, TypedDict, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from packaging.version import Version

from armarium.parse import Record
from armarium.schemas import Schema

CONFIG = Path("reference/extensions.json")


class ExtensionDeclaration(TypedDict):
    """Rules and installation state for one locally registered extension."""

    rules: list[dict[str, str]]
    installed: NotRequired[bool]
    armarium_version: NotRequired[str]


DECLARATION = {
    "type": "object",
    "patternProperties": {
        "^[a-z0-9]+(?:-[a-z0-9]+)*$": {
            "type": "object",
            "required": ["rules"],
            "properties": {
                "rules": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["type", "schema"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "pattern": "^[A-Za-z][A-Za-z0-9]*$",
                            },
                            "subtype": {"type": "string", "minLength": 1},
                            "schema": {"type": "string", "minLength": 1},
                            "template": {"type": "string", "minLength": 1},
                        },
                        "additionalProperties": False,
                    },
                },
                "installed": {"type": "boolean"},
                "armarium_version": {"type": "string", "pattern": "\\S"},
            },
            "additionalProperties": False,
        }
    },
    "additionalProperties": False,
}


@dataclass(frozen=True)
class ExtensionRule:
    """An additional schema and optional template for one type/subtype selector."""

    extension: str
    kind: str
    subtype: str | None
    schema: Schema
    template: Path | None

    def matches(self, kind: str, subtype: str | None) -> bool:
        """Return whether this rule applies to the requested record."""
        return self.kind == kind and (self.subtype is None or self.subtype == subtype)


def _local_path(root: Path, directory: str, name: str) -> Path:
    """Resolve a relative file below a reference directory; reject all symlinks."""
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"extension path must stay inside {directory}: {name}")
    path = root / directory / relative
    if any(
        p.is_symlink()
        for p in (path, *path.parents)
        if p != root and p.is_relative_to(root)
    ):
        raise ValueError(f"extension path must not use symlinks: {path}")
    return path


def _declarations(path: Path) -> dict[str, ExtensionDeclaration]:
    """Read and validate a declaration, failing closed on malformed configuration."""
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(DECLARATION).iter_errors(data))
    if errors:
        raise ValueError(f"invalid extension declaration {path}: {errors[0].message}")
    return cast(dict[str, ExtensionDeclaration], data)


def load_extensions(root: Path) -> list[ExtensionRule]:
    """Load enabled rules and check every declared schema and template.

    Missing configuration means no extensions. Paths are relative to reference/.
    Conflicting template selectors are errors;
    additional schema constraints can be combined freely. Invalid or missing
    files raise ValueError or OSError, never silently disabling an extension.
    """
    config = _local_path(root, "reference", "extensions.json")
    if not config.exists():
        return []
    rules: list[ExtensionRule] = []
    for extension, declarations in _declarations(config).items():
        for declaration in declarations["rules"]:
            kind, subtype = declaration["type"], declaration.get("subtype")
            try:
                schema = Schema.load(
                    _local_path(root, "reference", declaration["schema"]), root
                )
            except SchemaError as exc:
                raise ValueError(f"invalid extension schema: {exc.message}") from exc
            template = None
            if "template" in declaration:
                template = _local_path(root, "reference", declaration["template"])
                if not is_template(template, root):
                    raise ValueError(
                        f"extension template must be in a templates directory: {template}"
                    )
                record, errors = Record.parse(template, root)
                if record is None:
                    raise ValueError(
                        f"invalid extension template {template}: {errors[0].message}"
                    )
                if record.frontmatter.type != kind or (
                    subtype is not None and record.frontmatter.get("subtype") != subtype
                ):
                    raise ValueError(
                        f"extension template {template} has the wrong type/subtype"
                    )
                if any(
                    r.template is not None
                    and r.kind == kind
                    and (r.subtype is None or subtype is None or r.subtype == subtype)
                    for r in rules
                ):
                    raise ValueError(
                        f"conflicting extension templates for {kind}/{subtype}"
                    )
            rules.append(ExtensionRule(extension, kind, subtype, schema, template))
    return rules


def _extension(name: str) -> Traversable:
    """Find an extension shipped in the installation or development checkout."""
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError("invalid extension name")
    packaged = files("armarium").joinpath("extensions", name)
    if packaged.is_dir():
        return packaged
    checkout = Path(__file__).resolve().parents[2] / "extensions" / name
    if checkout.is_dir():
        return checkout
    raise ValueError(f"unknown extension: {name}")


def _armarium_version() -> str:
    """Identify the release supplying resources, or the checkout's project version."""
    if files("armarium").joinpath("extensions").is_dir():
        return version("armarium")
    project = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with project.open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def enable_extension(name: str, vault: Path | None = None) -> Path:
    """Install a complete extension directory and register its rules.

    Refuse existing registrations or directories. Failed installation removes
    its new directory and restores the previous configuration. Callers validate
    existing records after installation.
    """
    from armarium.add import select_vault

    root = select_vault(vault)
    load_extensions(root)
    config = root / CONFIG
    declarations = _declarations(config) if config.exists() else {}
    if name in declarations:
        raise ValueError(f"extension already enabled: {name}")
    _install_extension(name, root, declarations)
    return root


def _install_extension(
    name: str, root: Path, declarations: dict[str, ExtensionDeclaration]
) -> None:
    """Install files and register rules against the complete resulting configuration.

    Enable checks existing rules first; update checks them after replacement so
    rules referencing this extension remain usable during an update.
    """
    config = root / CONFIG
    original = config.read_bytes() if config.exists() else None
    with as_file(_extension(name)) as source:
        addition = _declarations(source / "extension.json")
        if set(addition) != {name}:
            raise ValueError("extension declaration does not match its name")
        directory = _local_path(root, "reference/extensions", name)
        parent_existed = directory.parent.exists()
        directory.mkdir(parents=True)
        registered = False
        try:
            shutil.copytree(source, directory, dirs_exist_ok=True)
            for rule in addition[name]["rules"]:
                for field in ("schema", "template"):
                    if field in rule:
                        _local_path(root, f"reference/extensions/{name}", rule[field])
                        rule[field] = f"extensions/{name}/{rule[field]}"
            addition[name]["installed"] = True
            addition[name]["armarium_version"] = _armarium_version()
            declarations.update(addition)
            _write_config(config, json.dumps(declarations, indent=2).encode() + b"\n")
            registered = True
            load_extensions(root)
        except BaseException:
            if registered:
                if original is None:
                    config.unlink()
                else:
                    _write_config(config, original)
            shutil.rmtree(directory)
            if not parent_existed:
                directory.parent.rmdir()
            raise


def _write_config(path: Path, contents: bytes) -> None:
    """Replace configuration atomically, preserving it on failed writes."""
    temporary = path.with_suffix(".json.tmp")
    with temporary.open("xb") as stream:
        try:
            stream.write(contents)
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def remove_extension(name: str, vault: Path | None = None) -> Path:
    """Unregister an extension and delete its installation, including local edits.

    Records are unchanged. Explicit dependencies prevent removal. A failed
    change restores the directory and configuration; failed restoration keeps
    the backup for recovery. Local declarations without an installation are
    unregistered without deleting their files.
    """
    from armarium.add import select_vault

    root = select_vault(vault)
    config = _local_path(root, "reference", "extensions.json")
    declarations = _declarations(config) if config.exists() else {}
    if name not in declarations:
        raise ValueError(f"extension is not enabled: {name}")
    original = config.read_bytes()
    removed = declarations.pop(name)
    directory = _local_path(root, "reference/extensions", name)
    installed = removed.get("installed", False) and directory.exists()
    if installed:
        for declaration in declarations.values():
            for rule in declaration["rules"]:
                for field in ("schema", "template"):
                    if field in rule and _local_path(
                        root, "reference", rule[field]
                    ).is_relative_to(directory):
                        raise ValueError(
                            "extension files are used by another enabled extension"
                        )
    workspace = Path(tempfile.mkdtemp(prefix=".armarium-extension-", dir=root))
    backup = workspace / "extension"
    registered = False
    committed = False
    try:
        if installed:
            directory.rename(backup)
        _write_config(config, json.dumps(declarations, indent=2).encode() + b"\n")
        registered = True
        load_extensions(root)
        committed = True
    except BaseException:
        if registered:
            _write_config(config, original)
        if backup.exists():
            backup.rename(directory)
        raise
    finally:
        if committed or not backup.exists():
            shutil.rmtree(workspace)
    return root


def update_extension(
    name: str, vault: Path | None = None, *, allow_downgrade: bool = False
) -> Path:
    """Replace an installed extension with files from the current Armarium.

    Reuse installation checks without requiring the old extension to be valid.
    Preserve the old directory and declaration until replacement succeeds,
    including when versions match. Downgrades require allow_downgrade.
    Failed restoration retains the backup.
    Local registrations are not installed extensions and cannot be updated.
    Callers validate records afterward; no record migration is performed.
    """
    from armarium.add import select_vault

    root = select_vault(vault)
    config = _local_path(root, "reference", "extensions.json")
    declarations = _declarations(config) if config.exists() else {}
    if name not in declarations or not declarations[name].get("installed", False):
        raise ValueError(f"extension is not installed: {name}")
    previous = declarations[name].get("armarium_version")
    available = _armarium_version()
    if (
        previous is not None
        and Version(previous) > Version(available)
        and not allow_downgrade
    ):
        raise ValueError(
            f"extension {name} was installed with newer Armarium {previous}; "
            f"current version is {available}. Use --allow-downgrade to replace it."
        )
    original = config.read_bytes()
    declarations.pop(name)
    directory = _local_path(root, "reference/extensions", name)
    workspace = Path(tempfile.mkdtemp(prefix=".armarium-update-", dir=root))
    backup = workspace / "extension"
    unregistered = False
    committed = False
    try:
        if directory.exists():
            directory.rename(backup)
        _write_config(config, json.dumps(declarations, indent=2).encode() + b"\n")
        unregistered = True
        _install_extension(name, root, declarations)
        committed = True
    except BaseException:
        if unregistered and directory.exists():
            shutil.rmtree(directory)
        if unregistered:
            _write_config(config, original)
        if backup.exists():
            backup.rename(directory)
        raise
    finally:
        if committed or not backup.exists():
            shutil.rmtree(workspace)
    return root


def is_template(path: Path, root: Path) -> bool:
    """Recognize core and extension template directories without loading records."""
    relative = path.relative_to(root)
    return relative.is_relative_to("reference/templates") or (
        len(relative.parts) >= 5
        and relative.parts[:2] == ("reference", "extensions")
        and relative.parts[3] == "templates"
    )
