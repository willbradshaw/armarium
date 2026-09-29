"""Create shared or campaign Notes from the selected vault's local template."""

from pathlib import Path

from armarium.creation import (
    check_destination,
    check_name,
    infer_campaign,
    read_template,
    record_directory,
    select_vault,
    write_record,
)


def add_note(
    name: str, vault: Path | None = None, *, campaign: int | None = None
) -> Path:
    """Create and validate a Note without changing existing records.

    Args:
        name: Plain record name without .md; spaces are permitted.
        vault: Vault root, or None to discover it from the working directory.
        campaign: Existing campaign number; infer from the working directory
            within the selected vault when omitted, otherwise use shared scope.

    Returns:
        Path: Absolute destination after local schema and contextual validation.
            The caller can then validate the whole vault.

    Raises:
        ValueError: Invalid name, scope, local scaffolding or generated record.
        OSError: Destination collision or filesystem failure.
        KeyboardInterrupt: Partial creation is removed before propagating.
    """
    check_name(name)
    if campaign is not None and campaign < 1:
        raise ValueError("campaign number must be positive")
    root = select_vault(vault)
    campaign = infer_campaign(root, campaign)
    directory = record_directory(root, "Note", campaign)
    destination = directory / f"{name}.md"
    check_destination(destination, normalize=True)
    template = read_template(root, "Note", check_reference=True)
    text = template.path.read_text(encoding="utf-8")
    return write_record(destination, text, root, "Note")
