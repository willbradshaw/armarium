"""Create numbered Session records using a vault's local template."""

import re
from pathlib import Path

import yaml

from armarium.lib import CAMPAIGN_NAME, find_files, find_vault, parse_directories
from armarium.logging import logger
from armarium.parse import Record
from armarium.validate import validate


def _session_number(directory: Path, campaign: int, number: int | None) -> int:
    """Select an unused session number within a campaign's Session directory.

    Args:
        directory: Existing Session directory, including any archive subfolders.
        campaign: Campaign number appearing in session filenames.
        number: Explicit number, or None for one greater than the largest found.

    Returns:
        int: Unused number from 1 through 999, matching the three-digit convention.

    Raises:
        ValueError: The number is used, outside the supported range, or automatic
            numbering has reached 999. Directory traversal can also fail.
        OSError: Existing files cannot be listed.
    """
    pattern = re.compile(rf"S-{campaign}-([0-9]{{3}})\.md", re.IGNORECASE)
    existing = {
        int(match[1])
        for path in find_files(directory)
        if (match := pattern.fullmatch(path.name))
    }
    if number is None:
        number = max(existing, default=0) + 1
    if not 1 <= number <= 999:
        raise ValueError("session number must be between 1 and 999")
    if number in existing:
        raise ValueError(
            f"session number {number} already exists in campaign {campaign}"
        )
    return number


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
    selected = vault.expanduser().resolve() if vault is not None else Path.cwd()
    root = find_vault(selected)
    if vault is not None and selected != root:
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
    if campaign is None:
        raise ValueError("specify --campaign or run inside a campaign directory")
    if campaign < 1:
        raise ValueError("campaign number must be positive")
    definition, failures = Record.parse(root / "reference/types/Session.md", root)
    if definition is None:
        raise ValueError(f"cannot read Session Type: {failures[0].message}")
    declarations = parse_directories(definition.frontmatter.get("directories"))
    if "campaign" not in declarations:
        raise ValueError("Session Type declares no campaign directory")
    directory = root / "campaigns" / f"campaign_{campaign}" / declarations["campaign"]
    for path in (directory, *directory.parents):
        if path == root:
            break
        if not path.is_dir() or path.is_symlink():
            raise ValueError(f"{path} must be an existing real directory")
    number = _session_number(directory, campaign, number)
    destination = directory / f"S-{campaign}-{number:03}.md"
    if any(
        path.name.casefold() == destination.name.casefold()
        for path in directory.iterdir()
    ):
        raise FileExistsError(f"record already exists: {destination}")
    template_path = root / "reference/templates/Session.md"
    if template_path.is_symlink() or template_path.parent.is_symlink():
        raise ValueError("Session template must be a regular file in the vault")
    template, failures = Record.parse(template_path, root)
    if template is None:
        raise ValueError(f"cannot read Session template: {failures[0].message}")
    if template.frontmatter.type != "Session":
        raise ValueError("Session template must declare the Session type")
    metadata = dict(template.frontmatter)
    metadata["campaign"] = f"[[campaign_{campaign}/reference/Campaign]]"
    metadata["session_number"] = number
    for field in ("date", "players_absent", "in_game_start_date", "in_game_end_date"):
        metadata.setdefault(field, None)
    text = (
        "---\n"
        + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
        + "---\n"
        + template.body.text
    )
    logger.info("Adding new Session record at %s", destination)
    stream = destination.open("x", encoding="utf-8")
    try:
        with stream:
            stream.write(text)
        result = validate(destination, root)
        if result.failed:
            for diagnostic in result.diagnostics:
                diagnostic.report()
            raise ValueError(
                "generated Session record failed validation; no record created"
            )
    except BaseException:
        destination.unlink()
        raise
    return destination
