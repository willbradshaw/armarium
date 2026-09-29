"""Create valid Content stubs from vault-local templates and declarations."""

import unicodedata
from pathlib import Path
from typing import Any

import yaml

from armarium.index import VaultIndex
from armarium.lib import CAMPAIGN_NAME, find_vault, parse_directories, parse_wikilink
from armarium.logging import logger
from armarium.parse import Record
from armarium.validate import validate

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
    if subtype not in SUBTYPES:
        raise ValueError(f"subtype must be one of {', '.join(SUBTYPES)}")
    if campaign is not None and campaign < 1:
        raise ValueError("campaign number must be positive")
    if player is not None and subtype != "PC":
        raise ValueError("--player is only valid for PC content")
    selected = vault.expanduser().resolve() if vault is not None else Path.cwd()
    root = find_vault(selected)
    if vault is not None and root != selected:
        raise ValueError("--vault must name the vault root")
    working_directory = Path.cwd().resolve()
    if campaign is None and working_directory.is_relative_to(root):
        parts = working_directory.relative_to(root).parts
        if (
            len(parts) >= 2
            and parts[0] == "campaigns"
            and CAMPAIGN_NAME.fullmatch(parts[1])
        ):
            campaign = int(parts[1].removeprefix("campaign_"))
    definition, failures = Record.parse(root / "reference/types/Content.md", root)
    if definition is None:
        raise ValueError(f"cannot read Content Type: {failures[0].message}")
    declarations = parse_directories(definition.frontmatter.get("directories"))
    scope = "shared" if campaign is None else "campaign"
    if scope not in declarations:
        raise ValueError(f"Content Type declares no {scope} directory")
    base = root if campaign is None else root / "campaigns" / f"campaign_{campaign}"
    directory = base / declarations[scope]
    # Refuse missing directories and symlinks in every component of the write path.
    for path in (directory, *directory.parents):
        if path == root:
            break
        if not path.is_dir() or path.is_symlink():
            raise ValueError(f"{path} must be an existing real directory")
    destination = directory / f"{name}.md"
    key = unicodedata.normalize("NFC", destination.name).casefold()
    if any(
        unicodedata.normalize("NFC", p.name).casefold() == key
        for p in directory.iterdir()
    ):
        raise FileExistsError(f"record already exists: {destination}")
    template_path = root / "reference/templates/Content.md"
    if template_path.is_symlink() or template_path.parent.is_symlink():
        raise ValueError("Content template must be a regular file in the vault")
    template, failures = Record.parse(template_path, root)
    if template is None:
        raise ValueError(f"cannot read Content template: {failures[0].message}")
    if template.frontmatter.type != "Content":
        raise ValueError("Content template must declare the Content type")
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
    text = (
        "---\n"
        + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
        + "---\n"
        + template.body.text
    )
    logger.info("Adding new Content record at %s", destination)
    stream = destination.open("x", encoding="utf-8")
    try:
        with stream:
            stream.write(text)
        result = validate(destination, root)
        if result.failed:
            for diagnostic in result.diagnostics:
                diagnostic.report()
            raise ValueError(
                "generated Content record failed validation; no record created"
            )
    except BaseException:
        destination.unlink()
        raise
    return destination
