"""Install optional reference files and load vault-local extension declarations."""

import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import NotRequired, TypedDict, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from armarium.parse import Record
from armarium.schemas import Schema

CONFIG = Path("reference/extensions.json")


class ExtensionDeclaration(TypedDict):
    """Rules and installation hashes for one locally registered extension."""

    rules: list[dict[str, str]]
    files: NotRequired[dict[str, str]]


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
                "files": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "string",
                        "pattern": "^[a-f0-9]{64}$",
                    },
                },
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

    Missing configuration means no extensions. Paths are relative to schemas/
    and templates/ respectively. Conflicting template selectors are errors;
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
                    _local_path(root, "reference/schemas", declaration["schema"]), root
                )
            except SchemaError as exc:
                raise ValueError(f"invalid extension schema: {exc.message}") from exc
            template = None
            if "template" in declaration:
                template = _local_path(
                    root, "reference/templates", declaration["template"]
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


def enable_extension(name: str, vault: Path | None = None) -> Path:
    """Install reference files without overwrites and register the extension last.

    Existing declarations are preserved. Re-enabling is refused so local edits
    cannot be overwritten. A failed or interrupted installation removes its new
    files and directories. Existing records are not changed; callers validate
    them afterward so required migrations remain available for inspection.
    """
    from armarium.add import select_vault

    root = select_vault(vault)
    load_extensions(root)
    config = root / CONFIG
    original = config.read_bytes() if config.exists() else None
    declarations = _declarations(config) if original is not None else {}
    if name in declarations:
        raise ValueError(f"extension already enabled: {name}")
    created: list[Path] = []
    directories: list[Path] = []
    with as_file(_extension(name)) as source:
        addition = _declarations(source / "extension.json")
        if set(addition) != {name}:
            raise ValueError("extension declaration does not match its name")
        sources = sorted(p for p in (source / "reference").rglob("*") if p.is_file())
        destinations = [
            _local_path(
                root, "reference", p.relative_to(source / "reference").as_posix()
            )
            for p in sources
        ]
        for destination in destinations:
            if destination.exists():
                raise FileExistsError(f"extension file already exists: {destination}")
        try:
            for source_file, destination in zip(sources, destinations, strict=True):
                missing = []
                parent = destination.parent
                while not parent.exists():
                    missing.append(parent)
                    parent = parent.parent
                for directory in reversed(missing):
                    directory.mkdir()
                    directories.append(directory)
                with destination.open("xb") as stream:
                    created.append(destination)
                    stream.write(source_file.read_bytes())
            addition[name]["files"] = {
                path.relative_to(root / "reference").as_posix(): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in destinations
            }
            declarations.update(addition)
            _write_config(config, json.dumps(declarations, indent=2).encode() + b"\n")
            try:
                load_extensions(root)
            except BaseException:
                if original is None:
                    config.unlink()
                else:
                    _write_config(config, original)
                raise
        except BaseException:
            for path in reversed(created):
                path.unlink(missing_ok=True)
            for directory in reversed(directories):
                directory.rmdir()
            raise
    return root


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
    """Remove registration and unchanged installed files, preserving records.

    Installation hashes identify files independently of the current package.
    Edited files and files declared by other extensions prevent removal. Missing
    installed files are tolerated, allowing an incomplete extension to be removed.
    Failures restore moved files and the original configuration. Declarations
    without installation hashes are unregistered without deleting any files.
    """
    from armarium.add import select_vault

    root = select_vault(vault)
    config = _local_path(root, "reference", "extensions.json")
    declarations = _declarations(config) if config.exists() else {}
    if name not in declarations:
        raise ValueError(f"extension is not enabled: {name}")
    original = config.read_bytes()
    removed = declarations.pop(name)
    paths: list[Path] = []
    for relative, digest in removed.get("files", {}).items():
        path = _local_path(root, "reference", relative)
        if path == config:
            raise ValueError("extension cannot own its configuration file")
        if not path.exists():
            continue
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise ValueError(
                f"extension file has local changes; preserve or restore it before removal: {path}"
            )
        paths.append(path)
    # Preserve explicitly shared files, including manually edited declarations.
    for declaration in declarations.values():
        used = {_local_path(root, "reference", p) for p in declaration.get("files", {})}
        for rule in declaration["rules"]:
            used.add(_local_path(root, "reference/schemas", rule["schema"]))
            if "template" in rule:
                used.add(_local_path(root, "reference/templates", rule["template"]))
        if used.intersection(paths):
            raise ValueError("extension files are used by another enabled extension")
    workspace = Path(tempfile.mkdtemp(prefix=".armarium-extension-", dir=root))
    moved: list[tuple[Path, Path]] = []
    registered = False
    committed = False
    try:
        for index, path in enumerate(paths):
            backup = workspace / str(index)
            path.rename(backup)
            moved.append((path, backup))
        _write_config(config, json.dumps(declarations, indent=2).encode() + b"\n")
        registered = True
        load_extensions(root)
        committed = True
    except BaseException:
        if registered:
            _write_config(config, original)
        for path, backup in reversed(moved):
            backup.rename(path)
        raise
    finally:
        # If restoration itself fails, retain backups for recovery.
        if committed or not any(workspace.iterdir()):
            shutil.rmtree(workspace)
    # Empty extension directories are no longer needed; preserve vault scaffolding.
    boundaries = {
        root / "reference",
        root / "reference/schemas",
        root / "reference/templates",
    }
    for path in paths:
        parent = path.parent
        while parent not in boundaries:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    return root
