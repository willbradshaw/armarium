"""Shared scope, template and safe-write operations for record creation.

Command modules prepare type-specific contents. These helpers resolve the local
vault conventions and validate each new record; the CLI validates the whole vault.
"""

import re
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from armarium.lib import CAMPAIGN_NAME, find_files, find_vault, parse_directories
from armarium.logging import logger
from armarium.parse import Record
from armarium.validate import validate


def select_vault(vault: Path | None) -> Path:
    """Resolve an explicit vault root or discover it from the working directory.

    Reject explicit paths inside a vault rather than silently changing their scope.
    """
    selected = vault.expanduser().resolve() if vault is not None else Path.cwd()
    root = find_vault(selected)
    if vault is not None and selected != root:
        raise ValueError("--vault must name the vault root")
    return root


def infer_campaign(root: Path, campaign: int | None) -> int | None:
    """Prefer an explicit campaign; otherwise infer one only inside this vault."""
    working_directory = Path.cwd().resolve()
    if campaign is None and working_directory.is_relative_to(root):
        parts = working_directory.relative_to(root).parts
        if (
            len(parts) >= 2
            and parts[0] == "campaigns"
            and CAMPAIGN_NAME.fullmatch(parts[1])
        ):
            campaign = int(parts[1].removeprefix("campaign_"))
    return campaign


def require_campaign(root: Path, campaign: int | None) -> int:
    """Select a positive campaign number, raising when none can be inferred."""
    campaign = infer_campaign(root, campaign)
    if campaign is None:
        raise ValueError("specify --campaign or run inside a campaign directory")
    if campaign < 1:
        raise ValueError("campaign number must be positive")
    return campaign


def check_name(name: str) -> None:
    """Reject names that are empty, non-plain, path-like or include .md."""
    if (
        not name
        or name != " ".join(name.split())
        or name.startswith(".")
        or name.endswith(".")
        or name.lower().endswith(".md")
        or any(c in name for c in '/\\\x00[]#|:*?"<>')
        or any(ord(c) < 32 for c in name)
    ):
        raise ValueError(
            "name must be a plain record name without .md, path separators, or reserved characters"
        )


def record_directory(root: Path, kind: str, campaign: int | str | None) -> Path:
    """Read a Type's scoped directory and require a real, existing write path.

    None selects shared scope. An integer selects campaign_N; a folder name
    preserves a campaign already identified by an existing record.
    """
    definition, failures = Record.parse(root / f"reference/types/{kind}.md", root)
    if definition is None:
        raise ValueError(f"cannot read {kind} Type: {failures[0].message}")
    declarations = parse_directories(definition.frontmatter.get("directories"))
    scope = "shared" if campaign is None else "campaign"
    if scope not in declarations:
        raise ValueError(f"{kind} Type declares no {scope} directory")
    if isinstance(campaign, int):
        campaign = f"campaign_{campaign}"
    base = root if campaign is None else root / "campaigns" / campaign
    directory = base / declarations[scope]
    for path in (directory, *directory.parents):
        if path == root:
            break
        if not path.is_dir() or path.is_symlink():
            raise ValueError(f"{path} must be an existing real directory")
    return directory


def check_destination(destination: Path, *, normalize: bool = False) -> None:
    """Refuse case-equivalent entries, optionally normalizing Unicode names.

    Plain user-supplied record names use NFC normalization. Numbered filenames
    use their existing case-insensitive comparison. Exclusive writing also
    protects against a destination created after this check.
    """
    names = [destination.name, *(p.name for p in destination.parent.iterdir())]
    if normalize:
        names = [unicodedata.normalize("NFC", name) for name in names]
    if names[0].casefold() in {name.casefold() for name in names[1:]}:
        raise FileExistsError(f"record already exists: {destination}")


def read_template(root: Path, kind: str, *, check_reference: bool = False) -> Record:
    """Parse a local template of the expected type, rejecting symlinked inputs.

    check_reference also rejects a symlink at the reference directory, for
    callers that require that component to be a real directory.
    """
    path = root / f"reference/templates/{kind}.md"
    paths = (
        (path, path.parent, path.parent.parent)
        if check_reference
        else (path, path.parent)
    )
    if any(p.is_symlink() for p in paths):
        raise ValueError(f"{kind} template must be a regular file in the vault")
    template, failures = Record.parse(path, root)
    if template is None:
        raise ValueError(f"cannot read {kind} template: {failures[0].message}")
    if template.frontmatter.type != kind:
        raise ValueError(f"{kind} template must declare the {kind} type")
    return template


def record_text(metadata: Mapping[str, Any], body: str) -> str:
    """Serialize frontmatter without reordering fields and append the given body."""
    return (
        "---\n"
        + yaml.safe_dump(dict(metadata), sort_keys=False, allow_unicode=True)
        + "---\n"
        + body
    )


def write_record(destination: Path, text: str, root: Path, kind: str) -> Path:
    """Exclusively create and validate a record, removing it on any failure.

    Log the destination and validation diagnostics. A failed exclusive open
    leaves an existing entry untouched. After a successful open, write errors,
    failed validation and interruptions remove only the newly created record.
    Whole-vault validation is the caller's responsibility.
    """
    logger.info("Adding new %s record at %s", kind, destination)
    stream = destination.open("x", encoding="utf-8")
    try:
        with stream:
            stream.write(text)
        result = validate(destination, root)
        if result.failed:
            for diagnostic in result.diagnostics:
                diagnostic.report()
            raise ValueError(
                f"generated {kind} record failed validation; no record created"
            )
    except BaseException:
        destination.unlink()
        raise
    return destination


def record_number(
    directory: Path,
    campaign: int,
    number: int | None,
    *,
    kind: str,
    prefix: str,
    digits: int,
) -> int:
    """Choose an unused bounded number, including records in archive directories.

    When omitted, use the largest existing number plus one. Explicit numbers
    must be unused and in the range representable by the filename's digits.
    """
    pattern = re.compile(rf"{prefix}-{campaign}-([0-9]{{{digits}}})\.md", re.IGNORECASE)
    existing = {
        int(match[1])
        for path in find_files(directory)
        if (match := pattern.fullmatch(path.name))
    }
    if number is None:
        number = max(existing, default=0) + 1
    maximum = 10**digits - 1
    if not 1 <= number <= maximum:
        raise ValueError(f"{kind} number must be between 1 and {maximum}")
    if number in existing:
        raise ValueError(
            f"{kind} number {number} already exists in campaign {campaign}"
        )
    return number
