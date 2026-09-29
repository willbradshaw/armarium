"""Create valid Content stubs from vault-local templates and declarations."""

from pathlib import Path
from typing import Any

from armarium.creation import (
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

SUBTYPES = ("NPC", "PC", "Location", "Faction", "Object", "Lore")


def _content_frontmatter(
    template: Record,
    subtype: str,
    campaign: int | None,
    player: str | None,
) -> dict[str, Any]:
    """Fill a Content template's metadata for a new shared or campaign record.

    Args:
        template: Parsed local Content template.
        subtype: Selected built-in subtype.
        campaign: Campaign number, or None for shared content.
        player: Canonical Player link override, or None to use the template value.

    Returns:
        dict[str, Any]: Metadata retaining custom fields, with required nullable
            fields supplied. Campaign 1 is the template's campaign-state placeholder.

    Raises:
        ValueError: A PC has no Player or the template campaign state is malformed.
    """
    data = {
        key: value
        for key, value in template.frontmatter.items()
        if not CAMPAIGN_NAME.fullmatch(key)
    }
    data["subtype"] = subtype
    data.setdefault("summary", None)
    nullable = {"NPC": "stats", "Location": "parent_location", "Faction": "members"}
    if subtype in nullable:
        data.setdefault(nullable[subtype], None)
    if player is not None:
        data["player"] = player
    if subtype == "PC" and not data.get("player"):
        raise ValueError(
            "PC requires --player naming an existing Player, or a player in the template"
        )
    if campaign is not None:
        state = template.frontmatter.get("campaign_1", {})
        if not isinstance(state, dict):
            raise ValueError("template campaign_1 must be a mapping")
        state = dict(state)
        state.setdefault("first_session", None)
        state.setdefault("last_session", None)
        if subtype == "Object":
            state.setdefault("held_by", None)
        data[f"campaign_{campaign}"] = state
    return data


def add_content(
    name: str,
    subtype: str,
    vault: Path | None = None,
    *,
    campaign: int | None = None,
    player: str | None = None,
) -> Path:
    """Create one Content record, refusing overwrites and invalid generated records.

    Args:
        name: Record filename without .md; spaces are permitted.
        subtype: NPC, PC, Location, Faction, Object or Lore.
        vault: Vault root, or None to discover it from the working directory.
        campaign: Existing campaign number. When omitted, infer from the working
            directory inside the selected vault, otherwise create shared content.
        player: Player name, path or canonical wikilink, for PCs only.

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
    root = select_vault(vault)
    campaign = infer_campaign(root, campaign)
    directory = record_directory(root, "Content", campaign)
    destination = directory / f"{name}.md"
    check_destination(destination, normalize=True)
    template = read_template(root, "Content")
    if player is not None:
        target = parse_wikilink(
            player if player.startswith("[[") else f"[[{player}]]", canonical=True
        )
        resolved, problem = VaultIndex(root).resolve(target, destination)
        if problem or resolved is None:
            raise ValueError(
                "--player must uniquely identify an existing Player; use a vault-relative path"
            )
        player = f"[[{resolved.relative_to(root).with_suffix('').as_posix()}]]"
    metadata = _content_frontmatter(template, subtype, campaign, player)
    text = record_text(metadata, template.body.text)
    return write_record(destination, text, root, "Content")
