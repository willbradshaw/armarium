"""Create campaigns using a vault's own Type declarations and templates."""

import re
import shutil
from pathlib import Path

from armarium.creation import select_vault
from armarium.lib import CAMPAIGN_NAME, find_files, parse_directories
from armarium.logging import logger
from armarium.parse import Record
from armarium.validate import CAMPAIGN_DIRECTORIES


def _campaign_directories(root: Path) -> set[str]:
    """Collect required campaign directories and locally declared additions.

    Args:
        root: Resolved vault directory.

    Returns:
        set[str]: Paths relative to each campaign directory.

    Raises:
        ValueError: A Type record cannot be parsed or its directories are invalid.
        OSError: Type records cannot be read.
    """
    directories = set(CAMPAIGN_DIRECTORIES)
    for path in find_files(root / "reference/types"):
        if path.suffix.lower() != ".md":
            continue
        record, diagnostics = Record.parse(path, root)
        if record is None:
            raise ValueError(f"{path}: {diagnostics[0].message}")
        declarations = parse_directories(record.frontmatter.get("directories"))
        if "campaign" in declarations:
            directories.add(declarations["campaign"])
    return directories


def _render_campaign(text: str, number: int) -> str:
    """Adapt the campaign-1 examples in a local campaign template.

    Args:
        text: Template contents; campaign_1 denotes the new campaign.
        number: Campaign number to put in directory names and clue ID examples.

    Returns:
        str: Text with campaign_1 and C-1-NNNN/C-1-XXXX tokens updated. Other
            campaign references and surrounding formatting are preserved.
    """
    text = re.sub(r"\bcampaign_1\b", f"campaign_{number}", text)
    return re.sub(r"\bC-1-(?=\d{4}\b|XXXX\b)", f"C-{number}-", text)


def add_campaign(vault: Path | None = None, *, number: int | None = None) -> Path:
    """Create an empty campaign from the selected vault's local scaffolding.

    Args:
        vault: Vault root, or None to discover it from the working directory.
        number: Positive campaign number; defaults to the largest existing
            campaign number plus one, or 1 when there are no campaigns.

    Returns:
        Path: Resolved absolute path of the new campaign. Existing files and
            shared templates are unchanged; callers can validate the whole vault.

    Raises:
        ValueError: The vault cannot be identified, the number is invalid or
            already used, or the local scaffolding is invalid.
        OSError: A required template is missing, the destination exists, or
            creation fails. A partial campaign is removed on write failure.
        KeyboardInterrupt: Interrupted creation is cleaned up before propagating.
    """
    root = select_vault(vault)
    for directory in ("campaigns", "reference/types", "reference/templates"):
        path = root / directory
        if not path.is_dir() or path.is_symlink():
            raise ValueError(f"{path} must be a real directory")
    existing = {
        int(path.name.removeprefix("campaign_"))
        for path in (root / "campaigns").iterdir()
        if CAMPAIGN_NAME.fullmatch(path.name) and path.is_dir()
    }
    if number is None:
        number = max(existing, default=0) + 1
    if number < 1:
        raise ValueError("campaign number must be positive")
    if number in existing:
        raise ValueError(f"campaign number {number} already exists")
    destination = root / "campaigns" / f"campaign_{number}"
    directories = _campaign_directories(root)
    records: dict[str, str] = {}
    for template, relative in (
        ("Campaign", "reference/Campaign.md"),
        ("Clues", "reference/indexes/Clues.md"),
    ):
        path = root / f"reference/templates/{template}.md"
        if path.is_symlink():
            raise ValueError(f"{path} must be a regular template file")
        records[relative] = _render_campaign(path.read_text(encoding="utf-8"), number)
    logger.info("Adding new campaign at %s", destination)
    destination.mkdir()
    try:
        for directory in sorted(directories):
            (destination / directory).mkdir(parents=True, exist_ok=True)
        for relative, text in records.items():
            (destination / relative).write_text(text, encoding="utf-8")
        for directory in sorted(directories):
            path = destination / directory
            if not any(path.iterdir()):
                (path / ".gitkeep").write_text("", encoding="utf-8")
    except BaseException:
        shutil.rmtree(destination)
        raise
    return destination
