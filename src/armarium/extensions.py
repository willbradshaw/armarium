"""Install optional reference files and load vault-local extension declarations."""

import json
import re
import shutil
import tempfile
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib.metadata import version
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from packaging.version import Version

from armarium.lib import (
    CAMPAIGN_NAME,
    IGNORED,
    REFERENCE_SUBTYPES,
    SUBTYPES,
    relative_parts,
    select_vault,
)
from armarium.logging import logger
from armarium.parse import Record
from armarium.schemas import Schema
from armarium.targets import LINK_TARGETS, RECORD_LINK_TARGETS, Target

CONFIG = Path("reference/extensions.json")
# Where a vault keeps its skills; an extension's addenda install below it.
SKILLS = ".agents/skills"


class ExtensionDeclaration(TypedDict):
    """Rules and installation state for one locally registered extension."""

    rules: list[dict[str, Any]]
    subtypes: NotRequired[dict[str, list[str]]]
    checks: NotRequired[list[str]]
    installed: NotRequired[bool]
    armarium_version: NotRequired[str]


# The form of reference/extensions.json and of an extension's extension.json.
DECLARATION = json.loads(
    files("armarium").joinpath("extensions.schema.json").read_text(encoding="utf-8")
)


@dataclass(frozen=True)
class ExtensionRule:
    """An additional schema and optional template for one type/subtype selector.

    yaml_blocks names fenced code block info strings, such as ``statblock``,
    whose contents must parse as a YAML mapping in matching records. links
    maps top-level frontmatter fields to the records their links must name.
    """

    extension: str
    kind: str
    subtype: str | None
    schema: Schema
    template: Path | None
    yaml_blocks: tuple[str, ...] = ()
    links: Mapping[str, Target] = field(default_factory=dict)

    def matches(self, kind: str, subtype: str | None) -> bool:
        """Return whether this rule applies to the requested record."""
        return self.kind == kind and (self.subtype is None or self.subtype == subtype)

    def overlaps(self, kind: str, subtype: str | None) -> bool:
        """Return whether some record could match both this rule and the selector."""
        return self.kind == kind and (
            self.subtype is None or subtype is None or self.subtype == subtype
        )


def _core_link_fields(kind: str, subtype: str | None) -> set[str]:
    """Name the fields whose link targets the core fixes for a rule's records.

    Args:
        kind: Record type the rule selects.
        subtype: Subtype the rule selects, or None for every subtype.

    Returns:
        set[str]: Fields bound on every record, on the type, and on the
            selected subtype; on every subtype of the type when none is selected.
    """
    fields = set(LINK_TARGETS)
    for (bound, selector), targets in RECORD_LINK_TARGETS.items():
        if bound == kind and (selector is None or subtype in (None, selector)):
            fields |= set(targets)
    return fields


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


@dataclass(frozen=True)
class ExtensionSet:
    """A vault's enabled extension rules, permitted subtypes and turned-on checks.

    Attributes:
        rules: The enabled rules.
        subtypes: The Content subtypes the vault permits.
        checks: Names of Armarium's optional checks that enabled extensions
            turn on, as ``checks`` declares them.
    """

    rules: list[ExtensionRule]
    subtypes: tuple[str, ...]
    checks: frozenset[str] = frozenset()

    def subtypes_of(self, kind: str | None) -> tuple[str, ...]:
        """Return the subtypes a type permits.

        Args:
            kind: The type's name, or None for an untyped record.

        Returns:
            tuple[str, ...]: The core Content subtypes followed by those
                enabled extensions declare, the core Reference subtypes, or
                none for a type without subtypes.
        """
        if kind == "Content":
            return self.subtypes
        return REFERENCE_SUBTYPES if kind == "Reference" else ()


def load_extension_set(root: Path) -> ExtensionSet:
    """Load enabled rules and subtypes, checking every declared schema and template.

    Missing configuration means no extensions and only the core subtypes. Paths
    are relative to reference/. Conflicting template selectors are errors;
    additional schema constraints can be combined freely. A declared Content
    subtype must be new to the vault and have a template from its own extension;
    a Content or Reference rule must select a permitted subtype. A declared link
    target must bind a field that neither the core nor another rule binds for
    the same records, never a Content campaign_N block, and may name only
    permitted subtypes of Content or Reference. Invalid or missing files
    raise ValueError or OSError, never silently disabling an extension.
    """
    config = _local_path(root, "reference", "extensions.json")
    if not config.exists():
        return ExtensionSet([], SUBTYPES)
    rules: list[ExtensionRule] = []
    declared: dict[str, str] = {}
    checks: set[str] = set()
    for extension, declarations in _declarations(config).items():
        checks.update(declarations.get("checks", []))
        for name in declarations.get("subtypes", {}).get("Content", []):
            if name in SUBTYPES:
                raise ValueError(
                    f"extension {extension} declares core Content subtype {name}"
                )
            if name in declared:
                raise ValueError(
                    f"extensions {declared[name]} and {extension} both declare "
                    f"Content subtype {name}"
                )
            declared[name] = extension
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
                    r.template is not None and r.overlaps(kind, subtype) for r in rules
                ):
                    raise ValueError(
                        f"conflicting extension templates for {kind}/{subtype}"
                    )
            links: dict[str, Target] = {}
            for name, link in declaration.get("links", {}).items():
                if name in _core_link_fields(kind, subtype) or (
                    kind == "Content" and CAMPAIGN_NAME.fullmatch(name)
                ):
                    raise ValueError(
                        f"extension {extension} declares a link target for core "
                        f"field {name}"
                    )
                if any(name in r.links and r.overlaps(kind, subtype) for r in rules):
                    raise ValueError(
                        f"conflicting extension link targets for {kind}/{subtype} "
                        f"field {name}"
                    )
                if "subtypes" in link and link["type"] not in ("Content", "Reference"):
                    raise ValueError(
                        f"extension {extension} names subtypes of {link['type']} "
                        f"for field {name}; only Content and Reference have subtypes"
                    )
                links[name] = Target(
                    link["type"], frozenset(link.get("subtypes", ())), local=True
                )
            rules.append(
                ExtensionRule(
                    extension,
                    kind,
                    subtype,
                    schema,
                    template,
                    tuple(declaration.get("yaml_blocks", ())),
                    links,
                )
            )
    extension_set = ExtensionSet(rules, (*SUBTYPES, *declared), frozenset(checks))
    for rule in rules:
        for name, target in rule.links.items():
            permitted = extension_set.subtypes_of(target.record_type)
            unknown = sorted(target.subtypes - set(permitted))
            if unknown:
                raise ValueError(
                    f"extension {rule.extension} names unknown {target.record_type} subtype "
                    f"{unknown[0]} for field {name}"
                )
        permitted = extension_set.subtypes_of(rule.kind)
        if permitted and rule.subtype not in (None, *permitted):
            raise ValueError(
                f"extension {rule.extension} selects unknown {rule.kind} subtype "
                f"{rule.subtype}"
            )
    for subtype, extension in declared.items():
        if not any(
            r.extension == extension and r.matches("Content", subtype) and r.template
            for r in rules
        ):
            raise ValueError(
                f"extension {extension} declares Content subtype {subtype} "
                "without a template for it"
            )
    return extension_set


def load_extensions(root: Path) -> list[ExtensionRule]:
    """Load enabled rules; see load_extension_set for the checks applied."""
    return load_extension_set(root).rules


def content_subtypes(root: Path) -> tuple[str, ...]:
    """Return the core Content subtypes followed by those enabled extensions declare."""
    return load_extension_set(root).subtypes


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


def armarium_version() -> str:
    """Identify the release supplying resources, or the checkout's project version."""
    if files("armarium").joinpath("extensions").is_dir():
        return version("armarium")
    project = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with project.open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def _addenda(root: Path, name: str) -> dict[Path, bytes]:
    """Read the skill addenda an extension has installed in a vault.

    Args:
        root: Vault root.
        name: Extension name.

    Returns:
        dict[Path, bytes]: The contents of each skill's ``addenda/NAME.md``, by
            path.

    Raises:
        ValueError: An addendum is reached through a symlink.
    """
    return {
        _local_path(root, SKILLS, f"{path.parts[-3]}/addenda/{name}.md"): (
            path.read_bytes()
        )
        for path in sorted((root / SKILLS).glob(f"*/addenda/{name}.md"))
    }


def installed_extensions(root: Path) -> list[str]:
    """Name the extensions installed in a vault, as opposed to registered locally.

    Raises:
        ValueError: The configuration is invalid or reached through a symlink.
        OSError: The configuration cannot be read.
    """
    config = _local_path(root, "reference", "extensions.json")
    if not config.exists():
        return []
    return [
        name
        for name, declaration in _declarations(config).items()
        if declaration.get("installed", False)
    ]


def installed_files(root: Path, name: str) -> dict[str, bytes]:
    """Read the files and skill addenda an extension has installed in a vault.

    Args:
        root: Vault root.
        name: Extension name.

    Returns:
        dict[str, bytes]: Each file's contents by its vault-relative POSIX path.

    Raises:
        ValueError: The installation is reached through a symlink.
    """
    directory = _local_path(root, "reference/extensions", name)
    contents = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and not IGNORED.intersection(path.relative_to(root).parts)
    }
    for path, content in _addenda(root, name).items():
        contents[path.relative_to(root).as_posix()] = content
    return contents


def supplied_files(root: Path, name: str) -> dict[str, bytes]:
    """Read the files the running Armarium installs for an extension in a vault.

    Args:
        root: Vault root, whose skills decide which addenda install.
        name: Extension name.

    Returns:
        dict[str, bytes]: Each file's contents by the vault-relative POSIX
            path it installs at, as installed_files reads them.

    Raises:
        ValueError: Armarium does not supply the extension.
    """
    contents: dict[str, bytes] = {}
    with as_file(_extension(name)) as source:
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source)
            if not path.is_file() or IGNORED.intersection(relative.parts):
                continue
            if relative.parts[0] != "skills":
                contents[f"reference/extensions/{name}/{relative.as_posix()}"] = (
                    path.read_bytes()
                )
            elif (
                len(relative.parts) == 2
                and path.suffix == ".md"
                and (root / SKILLS / path.stem / "SKILL.md").is_file()
            ):
                contents[f"{SKILLS}/{path.stem}/addenda/{name}.md"] = path.read_bytes()
    return contents


def _set_addenda(root: Path, name: str, contents: Mapping[Path, bytes]) -> None:
    """Make the skill addenda an extension has installed exactly the ones given.

    Delete its other addenda, and each ``addenda`` directory that leaves empty.
    Other files in those directories, such as the vault's own addenda, are
    untouched.

    Args:
        root: Vault root.
        name: Extension name.
        contents: The addenda to leave installed, as _addenda returns them;
            empty to remove them all.
    """
    for path in _addenda(root, name):
        if path not in contents:
            path.unlink()
            if not any(path.parent.iterdir()):
                path.parent.rmdir()
    for path, content in contents.items():
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(content)


def _install_addenda(source: Path, root: Path, name: str) -> None:
    """Install an extension's skill addenda, replacing those it installed before.

    Each ``skills/SKILL.md`` in the extension becomes ``addenda/NAME.md`` in
    the vault's skill of that name. A skill the vault lacks gets no addendum,
    and a warning says so.

    Args:
        source: Extension directory to install from.
        root: Vault root.
        name: Extension name.

    Raises:
        ValueError: An addendum's destination is reached through a symlink.
    """
    contents: dict[Path, bytes] = {}
    for addendum in sorted((source / "skills").glob("*.md")):
        skill = addendum.stem
        if (root / SKILLS / skill / "SKILL.md").is_file():
            path = _local_path(root, SKILLS, f"{skill}/addenda/{name}.md")
            contents[path] = addendum.read_bytes()
        else:
            logger.warning(
                "Vault has no %s skill; its %s addendum is not installed", skill, name
            )
    _set_addenda(root, name, contents)


def enable_extension(name: str, vault: Path | None = None) -> Path:
    """Install a complete extension directory and register its rules.

    Refuse existing registrations or directories. Failed installation removes
    its new directory and restores the previous configuration. Callers validate
    existing records after installation.
    """
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
    rules referencing this extension remain usable during an update. The
    extension's ``skills`` directory installs as skill addenda, not with its
    reference files; a failure restores the addenda found beforehand.
    """
    config = root / CONFIG
    original = config.read_bytes() if config.exists() else None
    addenda = _addenda(root, name)
    with as_file(_extension(name)) as source:
        addition = _declarations(source / "extension.json")
        if set(addition) != {name}:
            raise ValueError("extension declaration does not match its name")
        directory = _local_path(root, "reference/extensions", name)
        parent_existed = directory.parent.exists()
        directory.mkdir(parents=True)
        registered = False
        try:
            shutil.copytree(
                source,
                directory,
                dirs_exist_ok=True,
                ignore=lambda parent, _: ["skills"] if Path(parent) == source else [],
            )
            _install_addenda(source, root, name)
            for rule in addition[name]["rules"]:
                for field in ("schema", "template"):
                    if field in rule:
                        _local_path(root, f"reference/extensions/{name}", rule[field])
                        rule[field] = f"extensions/{name}/{rule[field]}"
            addition[name]["installed"] = True
            addition[name]["armarium_version"] = armarium_version()
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
            _set_addenda(root, name, addenda)
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

    Records are unchanged. Explicit dependencies prevent removal. An installed
    extension's skill addenda are deleted with it. A failed change restores the
    directory, addenda and configuration; failed restoration keeps the backup
    for recovery. Local declarations without an installation are unregistered
    without deleting their files.
    """
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
    addenda = _addenda(root, name) if installed else {}
    workspace = Path(tempfile.mkdtemp(prefix=".armarium-extension-", dir=root))
    backup = workspace / "extension"
    registered = False
    committed = False
    try:
        if installed:
            directory.rename(backup)
            _set_addenda(root, name, {})
        _write_config(config, json.dumps(declarations, indent=2).encode() + b"\n")
        registered = True
        load_extensions(root)
        committed = True
    except BaseException:
        if registered:
            _write_config(config, original)
        if backup.exists():
            backup.rename(directory)
        _set_addenda(root, name, addenda)
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
    Its skill addenda are replaced with it, dropping any it no longer supplies.
    Preserve the old directory and declaration until replacement succeeds,
    including when versions match. Downgrades require allow_downgrade.
    Failed restoration retains the backup.
    Local registrations are not installed extensions and cannot be updated.
    Callers validate records afterward; no record migration is performed.
    """
    root = select_vault(vault)
    config = _local_path(root, "reference", "extensions.json")
    declarations = _declarations(config) if config.exists() else {}
    if name not in declarations or not declarations[name].get("installed", False):
        raise ValueError(f"extension is not installed: {name}")
    previous = declarations[name]["armarium_version"]
    available = armarium_version()
    if Version(previous) > Version(available) and not allow_downgrade:
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
    relative = Path(*relative_parts(path, root))
    return relative.is_relative_to("reference/templates") or (
        len(relative.parts) >= 5
        and relative.parts[:2] == ("reference", "extensions")
        and relative.parts[3] == "templates"
    )
