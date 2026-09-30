"""Create valid Content stubs from vault-local templates and declarations."""

import re
from pathlib import Path
from typing import Any

from armarium.add import (
    check_destination,
    check_name,
    infer_campaign,
    read_template,
    record_directory,
    record_text,
    select_vault,
    write_record,
)
from armarium.index import VaultIndex
from armarium.lib import CAMPAIGN_NAME, parse_wikilink
from armarium.parse import Record

SUBTYPES = ("NPC", "PC", "Location", "Faction", "Object", "Lore", "Date", "Gear")


def _content_frontmatter(
    template: Record,
    subtype: str,
    campaign: int | None,
    player: str | None,
    reckoning: str | None = None,
    scale: str | None = None,
) -> dict[str, Any]:
    """Fill a Content template's metadata for a new shared or campaign record.

    Args:
        template: Parsed local Content template.
        subtype: Selected built-in subtype.
        campaign: Campaign number, or None for shared content.
        player: Canonical Player link override, or None to use the template value.
        reckoning: Calendar Lore link override, or None to use the template.
        scale: Date scale override, or None to use the template.

    Returns:
        dict[str, Any]: Metadata retaining custom fields, with required nullable
            fields supplied. Campaign 1 is the template's campaign-state placeholder.

    Raises:
        ValueError: A required PC/Date field is missing or template campaign state
            is malformed.
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
    if player is not None:
        data["player"] = player
    if subtype == "PC" and not data.get("player"):
        raise ValueError(
            "PC requires --player naming an existing Player, or a player in the template"
        )
    if subtype == "Date":
        for field, value in (("reckoning", reckoning), ("scale", scale)):
            if value is not None:
                data[field] = value
            if not data.get(field):
                raise ValueError(f"Date requires --{field} or {field} in the template")
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
    return data


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
    player: str | None = None,
    reckoning: str | None = None,
    scale: str | None = None,
) -> Path:
    """Create one Content record, refusing overwrites and invalid generated records.

    Args:
        name: Record filename without .md; spaces are permitted.
        subtype: NPC, PC, Location, Faction, Object, Lore, Date or Gear.
        vault: Vault root, or None to discover it from the working directory.
        campaign: Existing campaign number. When omitted, infer from the working
            directory inside the selected vault, otherwise create shared content.
        player: Player name, path or canonical wikilink, for PCs only.
        reckoning: Calendar Lore name, path or wikilink, for Dates only.
        scale: Nonblank calendar-defined period name, for Dates only.

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
    if subtype not in SUBTYPES:
        raise ValueError(f"subtype must be one of {', '.join(SUBTYPES)}")
    if campaign is not None and campaign < 1:
        raise ValueError("campaign number must be positive")
    if player is not None and subtype != "PC":
        raise ValueError("--player is only valid for PC content")
    if subtype != "Date" and (reckoning is not None or scale is not None):
        raise ValueError("--reckoning and --scale are only valid for Date content")
    root = select_vault(vault)
    campaign = infer_campaign(root, campaign)
    directory = record_directory(root, "Content", campaign)
    destination = directory / f"{name}.md"
    check_destination(destination, normalize=True)
    template = read_template(root, "Content")
    links = {"player": player, "reckoning": reckoning}
    for field, value in links.items():
        if value is None:
            continue
        target = parse_wikilink(
            value if value.startswith("[[") else f"[[{value}]]", canonical=True
        )
        resolved, problem = VaultIndex(root).resolve(target, destination)
        if problem or resolved is None:
            kind = "Player" if field == "player" else "calendar Lore record"
            raise ValueError(
                f"--{field} must uniquely identify an existing {kind}; use a vault-relative path"
            )
        links[field] = f"[[{resolved.relative_to(root).with_suffix('').as_posix()}]]"
    metadata = _content_frontmatter(
        template, subtype, campaign, links["player"], links["reckoning"], scale
    )
    text = record_text(metadata, _content_body(template.body.text, subtype))
    return write_record(destination, text, root, "Content")
