"""Create numbered Session records using a vault's local template."""

from pathlib import Path

from armarium.creation import (
    check_destination,
    read_template,
    record_directory,
    record_number,
    record_text,
    require_campaign,
    select_vault,
    write_record,
)


def add_session(
    vault: Path | None = None, *, campaign: int | None = None, number: int | None = None
) -> Path:
    """Create and validate a Session stub without modifying existing records.

    Args:
        vault: Vault root, or None to discover it from the working directory.
        campaign: Existing campaign number, or None to infer the current campaign.
        number: Session number, or None for the largest existing number plus one.

    Returns:
        Path: Resolved path of the new S-N-NNN.md record after its schema and
            contextual checks pass. Initial values come from the local template.

    Raises:
        ValueError: No campaign is selected, numbering or scaffolding is invalid,
            or the generated record fails validation. Diagnostics are logged.
        OSError: A destination exists or a filesystem operation fails.
        KeyboardInterrupt: The partial record is removed before propagating.
    """
    root = select_vault(vault)
    campaign = require_campaign(root, campaign)
    directory = record_directory(root, "Session", campaign)
    number = record_number(
        directory, campaign, number, kind="session", prefix="S", digits=3
    )
    destination = directory / f"S-{campaign}-{number:03}.md"
    check_destination(destination)
    template = read_template(root, "Session")
    metadata = dict(template.frontmatter)
    metadata["campaign"] = f"[[campaign_{campaign}/reference/Campaign]]"
    metadata["session_number"] = number
    for field in ("date", "players_absent", "in_game_start_date", "in_game_end_date"):
        metadata.setdefault(field, None)
    text = record_text(metadata, template.body.text)
    return write_record(destination, text, root, "Session")
