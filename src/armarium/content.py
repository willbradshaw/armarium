"""Create valid Content stubs from vault-local templates and declarations."""

import re
from collections.abc import Mapping
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
from armarium.lib import CAMPAIGN_NAME
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
            contextual validation. Existing records and templates are unchanged.

    Raises:
        ValueError: Arguments, scaffolding, Player resolution or the generated
            record are invalid. Record diagnostics are logged before removal.
        OSError: The destination exists or a filesystem operation fails.
        KeyboardInterrupt: The partial file is removed before propagating.
    """
    check_name(name)
    if campaign is not None and campaign < 1:
        raise ValueError("campaign number must be positive")
    root = select_vault(vault)
    subtypes = content_subtypes(root)
    if subtype not in subtypes:
        raise ValueError(f"subtype must be one of {', '.join(subtypes)}")
    campaign = infer_campaign(root, campaign)
    directory = record_directory(root, "Content", campaign)
    destination = directory / f"{name}.md"
    check_destination(destination, normalize=True)
    template = read_template(root, "Content", subtype=subtype)
    metadata = _content_frontmatter(template, subtype, campaign, frontmatter)
    text = record_text(metadata, _content_body(template.body.text, subtype))
    return write_record(destination, text, root, "Content")
