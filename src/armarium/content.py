"""Create valid Content stubs from vault-local templates and declarations."""

import re
import unicodedata
from collections.abc import Collection, Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any

from armarium.add import (
    check_destination,
    check_name,
    infer_campaign,
    merge_frontmatter,
    read_template,
    record_directory,
    record_text,
    select_vault,
    write_record,
)
from armarium.extensions import content_subtypes
from armarium.lib import CAMPAIGN_NAME, parse_subtype_directories
from armarium.parse import Record


def _content_frontmatter(
    template: Record,
    subtype: str,
    campaign: int | None,
    frontmatter: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fill a Content template's metadata for a new shared or campaign record.

    Args:
        template: Parsed local Content template.
        subtype: Selected core or extension subtype.
        campaign: Campaign number, or None for shared content.
        frontmatter: Fields applied after campaign adaptation.

    Returns:
        dict[str, Any]: Metadata retaining custom fields, with required nullable
            fields supplied. Campaign 1 is the template's campaign-state placeholder.

    Raises:
        ValueError: Template campaign state is malformed or supplied identity conflicts.
    """
    data = {
        key: value
        for key, value in template.frontmatter.items()
        if not CAMPAIGN_NAME.fullmatch(key)
    }
    data["subtype"] = subtype
    data.setdefault("summary", None)
    nullable = {
        "NPC": "stats",
        "Location": "parent_location",
        "Faction": "members",
        "Gear": "source",
    }
    if subtype in nullable:
        data.setdefault(nullable[subtype], None)
    if campaign is not None:
        state = template.frontmatter.get("campaign_1", {})
        if not isinstance(state, dict):
            raise ValueError("template campaign_1 must be a mapping")
        state = dict(state)
        state.setdefault("first_session", None)
        state.setdefault("last_session", None)
        if subtype in {"Object", "Gear"}:
            state.setdefault("held_by", None)
        data[f"campaign_{campaign}"] = state
    return merge_frontmatter(data, frontmatter, protected=("type", "subtype"))


def _content_body(body: str, subtype: str) -> str:
    """Preserve the template body, adding a rules callout for a new Gear stub.

    Args:
        body: Markdown from the vault-local Content template.
        subtype: Selected Content subtype.

    Returns:
        str: Original body, prefixed with an empty rules callout when Gear lacks
            one. Existing callouts are preserved; schema validation checks placement.
    """
    if subtype == "Gear" and not re.search(r"(?m)^>[ \t]+\[!rules\]", body):
        return "> [!rules]\n>\n\n" + body
    return body


def _subtype_directory(
    root: Path, directory: Path, subtype: str, subtypes: Collection[str]
) -> Path:
    """Select where the Content Type record files a new record of a subtype.

    Args:
        root: Resolved vault directory.
        directory: The Content directory for the record's scope.
        subtype: Selected Content subtype.
        subtypes: Content subtypes the vault permits.

    Returns:
        Path: The subfolder declared for the subtype in subtype_directories,
            which need not exist yet, or the Content directory itself when the
            subtype has none.

    Raises:
        ValueError: The Content Type record cannot be read or its
            subtype_directories declaration is invalid.
    """
    definition, failures = Record.parse(root / "reference/types/Content.md", root)
    if definition is None:
        raise ValueError(f"cannot read Content Type: {failures[0].message}")
    declared = parse_subtype_directories(
        definition.frontmatter.get("subtype_directories"), subtypes
    )
    return directory / declared[subtype] if subtype in declared else directory


def _create_directories(directory: Path, base: Path) -> list[Path]:
    """Create the missing folders between an existing directory and a subfolder.

    Args:
        directory: Subfolder to create, at or below base.
        base: Existing real directory.

    Returns:
        list[Path]: The folders created, outermost first; empty when the
            subfolder already exists.

    Raises:
        ValueError: An existing entry on the way is a file or symlink, or
            differs from the declared name only by case or Unicode form.
            Folders created before the failure are removed.
        OSError: A folder cannot be created; earlier ones are removed.
    """
    created: list[Path] = []
    current = base
    try:
        for part in directory.relative_to(base).parts:
            key = unicodedata.normalize("NFC", part).casefold()
            match = next(
                (
                    entry
                    for entry in current.iterdir()
                    if unicodedata.normalize("NFC", entry.name).casefold() == key
                ),
                None,
            )
            current = current / part
            if match is None:
                current.mkdir()
                created.append(current)
            elif match.name != part or match.is_symlink() or not match.is_dir():
                raise ValueError(
                    f"{current} must be a real directory; found {match.name}"
                )
    except BaseException:
        _remove_directories(created)
        raise
    return created


def _remove_directories(created: list[Path]) -> None:
    """Remove folders made by _create_directories, leaving any that hold entries.

    Args:
        created: Folders to remove, outermost first.
    """
    for path in reversed(created):
        with suppress(OSError):
            path.rmdir()


def add_content(
    name: str,
    subtype: str,
    vault: Path | None = None,
    *,
    campaign: int | None = None,
    frontmatter: Mapping[str, Any] | None = None,
) -> Path:
    """Create one Content record, refusing overwrites and invalid generated records.

    Args:
        name: Record filename without .md; spaces are permitted.
        subtype: NPC, PC, Location, Faction, Object, Lore, Date, Gear, or a
            subtype declared by an extension enabled in the vault.
        vault: Vault root, or None to discover it from the working directory.
        campaign: Existing campaign number. When omitted, infer from the working
            directory inside the selected vault, otherwise create shared content.
        frontmatter: Fields to merge into template defaults; generated identity is protected.

    Returns:
        Path: Absolute path of the new record after it passes local schema and
            contextual validation: in the subfolder the Content Type record's
            subtype_directories declares for the subtype, created when missing,
            otherwise directly in the Content directory. Existing records and
            templates are unchanged.

    Raises:
        ValueError: Arguments, scaffolding, Player resolution or the generated
            record are invalid. Record diagnostics are logged before removal.
        OSError: The destination exists or a filesystem operation fails.
        KeyboardInterrupt: The partial file is removed before propagating.
            Any failure also removes a subfolder this call created.
    """
    check_name(name)
    if campaign is not None and campaign < 1:
        raise ValueError("campaign number must be positive")
    root = select_vault(vault)
    subtypes = content_subtypes(root)
    if subtype not in subtypes:
        raise ValueError(f"subtype must be one of {', '.join(subtypes)}")
    campaign = infer_campaign(root, campaign)
    base = record_directory(root, "Content", campaign)
    directory = _subtype_directory(root, base, subtype, subtypes)
    created = _create_directories(directory, base)
    try:
        destination = directory / f"{name}.md"
        check_destination(destination, normalize=True)
        template = read_template(root, "Content", subtype=subtype)
        metadata = _content_frontmatter(template, subtype, campaign, frontmatter)
        text = record_text(metadata, _content_body(template.body.text, subtype))
        return write_record(destination, text, root, "Content")
    except BaseException:
        _remove_directories(created)
        raise
