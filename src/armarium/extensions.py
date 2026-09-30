"""Install optional reference files and load vault-local extension declarations."""

import json
import re
from dataclasses import dataclass
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from armarium.parse import Record
from armarium.schemas import Schema

CONFIG = Path("reference/extensions.json")
DECLARATION = {
    "type": "object",
    "patternProperties": {
        "^[a-z0-9]+(?:-[a-z0-9]+)*$": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["type", "schema"],
                "properties": {
                    "type": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9]*$"},
                    "subtype": {"type": "string", "minLength": 1},
                    "schema": {"type": "string", "minLength": 1},
                    "template": {"type": "string", "minLength": 1},
                },
                "additionalProperties": False,
            },
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


def _declarations(path: Path) -> dict[str, list[dict[str, str]]]:
    """Read and validate a declaration, failing closed on malformed configuration."""
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(DECLARATION).iter_errors(data))
    if errors:
        raise ValueError(f"invalid extension declaration {path}: {errors[0].message}")
    return cast(dict[str, list[dict[str, str]]], data)


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
        for declaration in declarations:
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
            declarations.update(addition)
            # Write via a sibling temporary file so interruption cannot truncate
            # an existing configuration. Restore it if declaration checks fail.
            temporary = config.with_suffix(".json.tmp")
            with temporary.open("x", encoding="utf-8") as stream:
                created.append(temporary)
                stream.write(json.dumps(declarations, indent=2) + "\n")
            temporary.replace(config)
            try:
                load_extensions(root)
            except BaseException:
                if original is None:
                    config.unlink()
                else:
                    config.write_bytes(original)
                raise
        except BaseException:
            for path in reversed(created):
                path.unlink(missing_ok=True)
            for directory in reversed(directories):
                directory.rmdir()
            raise
    return root
