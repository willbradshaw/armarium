"""Create numbered Clue records using a vault's local template."""

import re
from pathlib import Path

import yaml

from armarium.index import VaultIndex
from armarium.lib import (
    CAMPAIGN_NAME,
    find_campaign,
    find_files,
    find_vault,
    iter_wikilinks,
    parse_directories,
)
from armarium.logging import logger
from armarium.parse import Record
from armarium.validate import validate


def _clue_number(directory: Path, campaign: int, number: int | None) -> int:
    """Select an unused clue number within a campaign's Clue directory.

    Args:
        directory: Existing Clue directory, including any archive subfolders.
        campaign: Campaign number appearing in clue filenames.
        number: Explicit number, or None for one greater than the largest found.

    Returns:
        int: Unused number from 1 through 9999, matching the four-digit convention.

    Raises:
        ValueError: The number is used, outside the supported range, or automatic
            numbering has reached 9999. Directory traversal can also fail.
        OSError: Existing files cannot be listed.
    """
    pattern = re.compile(rf"C-{campaign}-([0-9]{{4}})\.md", re.IGNORECASE)
    existing = {
        int(match[1])
        for path in find_files(directory)
        if (match := pattern.fullmatch(path.name))
    }
    if number is None:
        number = max(existing, default=0) + 1
    if not 1 <= number <= 9999:
        raise ValueError("clue number must be between 1 and 9999")
    if number in existing:
        raise ValueError(f"clue number {number} already exists in campaign {campaign}")
    return number


def _clue_subjects(text: str, destination: Path, index: VaultIndex) -> list[str]:
    """Return canonical Content links in first-mention order, without duplicates.

    Resolve text with the existing wikilink parser and vault index. Targets must
    be shared or in the destination campaign. Malformed, missing, ambiguous or
    ineligible targets raise ValueError before any record is written.
    """
    subjects: list[str] = []
    for link in iter_wikilinks(text):
        if isinstance(link, ValueError):
            raise ValueError(f"invalid clue text link: {link}")
        target, problem = index.resolve(link[0], destination)
        if problem or target is None:
            raise ValueError(
                f"clue text [[{link[0]}]]: {problem}; use a unique Content path"
            )
        record = index.parse(target)[0] if target.suffix.lower() == ".md" else None
        if record is None or record.frontmatter.type != "Content":
            raise ValueError(f"clue text [[{link[0]}]] must target Content")
        if find_campaign(target, index.root) not in {
            None,
            find_campaign(destination, index.root),
        }:
            raise ValueError(f"clue text [[{link[0]}]] targets another campaign")
        canonical = f"[[{target.relative_to(index.root).with_suffix('').as_posix()}]]"
        if canonical not in subjects:
            subjects.append(canonical)
    return subjects


def add_clue(
    vault: Path | None = None,
    *,
    campaign: int | None = None,
    number: int | None = None,
    text: str | None = None,
) -> Path:
    """Create and validate a Clue stub without modifying existing records.

    Args:
        vault: Vault root, or None to discover it from the working directory.
        campaign: Existing campaign number, or None to infer the current campaign.
        number: Clue number, or None for the largest existing number plus one.
        text: Nonblank clue text, or None to use the local template text.

    Returns:
        Path: Resolved path of the new C-N-NNNN.md record after its schema and
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
    definition, failures = Record.parse(root / "reference/types/Clue.md", root)
    if definition is None:
        raise ValueError(f"cannot read Clue Type: {failures[0].message}")
    declarations = parse_directories(definition.frontmatter.get("directories"))
    if "campaign" not in declarations:
        raise ValueError("Clue Type declares no campaign directory")
    directory = root / "campaigns" / f"campaign_{campaign}" / declarations["campaign"]
    for path in (directory, *directory.parents):
        if path == root:
            break
        if not path.is_dir() or path.is_symlink():
            raise ValueError(f"{path} must be an existing real directory")
    number = _clue_number(directory, campaign, number)
    destination = directory / f"C-{campaign}-{number:04}.md"
    if any(
        path.name.casefold() == destination.name.casefold()
        for path in directory.iterdir()
    ):
        raise FileExistsError(f"record already exists: {destination}")
    template_path = root / "reference/templates/Clue.md"
    if template_path.is_symlink() or template_path.parent.is_symlink():
        raise ValueError("Clue template must be a regular file in the vault")
    template, failures = Record.parse(template_path, root)
    if template is None:
        raise ValueError(f"cannot read Clue template: {failures[0].message}")
    if template.frontmatter.type != "Clue":
        raise ValueError("Clue template must declare the Clue type")
    metadata = dict(template.frontmatter)
    clue_text = text if text is not None else metadata.get("text")
    if not isinstance(clue_text, str) or not clue_text.strip():
        raise ValueError(
            "provide nonblank --text or set text in the local Clue template"
        )
    metadata["text"] = clue_text
    metadata["subjects"] = _clue_subjects(clue_text, destination, VaultIndex(root))
    for field in ("first_session", "last_session"):
        metadata.setdefault(field, None)
    text = (
        "---\n"
        + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
        + "---\n"
        + template.body.text
    )
    logger.info("Adding new Clue record at %s", destination)
    stream = destination.open("x", encoding="utf-8")
    try:
        with stream:
            stream.write(text)
        result = validate(destination, root)
        if result.failed:
            for diagnostic in result.diagnostics:
                diagnostic.report()
            raise ValueError(
                "generated Clue record failed validation; no record created"
            )
    except BaseException:
        destination.unlink()
        raise
    return destination
