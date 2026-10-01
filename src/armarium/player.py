"""Create Player records using vault-local templates and directory declarations."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from armarium.add import (
    check_destination,
    check_name,
    merge_frontmatter,
    read_template,
    record_directory,
    record_text,
    require_campaign,
    select_vault,
    write_record,
)


def add_player(
    name: str,
    vault: Path | None = None,
    *,
    campaign: int | None = None,
    frontmatter: Mapping[str, Any] | None = None,
) -> Path:
    """Create and validate a Player without changing PCs or other records.

    Args:
        name: Plain record name without .md; spaces are permitted.
        vault: Vault root, or None to discover it from the working directory.
        campaign: Existing campaign number, or None to infer the current campaign.
        frontmatter: Fields to merge into template defaults; generated identity is protected.

    Returns:
        Path: Absolute destination after schema and contextual validation.
            Initial values and body are preserved from the local Player template.

    Raises:
        ValueError: The name, scope, scaffolding or generated record is invalid.
        OSError: The destination exists or a filesystem operation fails.
        KeyboardInterrupt: The partial record is removed before propagating.
    """
    check_name(name)
    root = select_vault(vault)
    campaign = require_campaign(root, campaign)
    directory = record_directory(root, "Player", campaign)
    destination = directory / f"{name}.md"
    check_destination(destination, normalize=True)
    template = read_template(root, "Player")
    metadata = merge_frontmatter(template.frontmatter, frontmatter)
    text = record_text(metadata, template.body.text)
    return write_record(destination, text, root, "Player")
