"""Create numbered Clue records using a vault's local template."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from armarium.add import (
    check_destination,
    merge_frontmatter,
    read_template,
    record_directory,
    record_number,
    record_text,
    require_campaign,
    select_vault,
    write_record,
)
from armarium.index import VaultIndex
from armarium.lib import (
    find_campaign,
    iter_wikilinks,
)


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
    frontmatter: Mapping[str, Any] | None = None,
) -> Path:
    """Create and validate a Clue stub without modifying existing records.

    Args:
        vault: Vault root, or None to discover it from the working directory.
        campaign: Existing campaign number, or None to infer the current campaign.
        number: Clue number, or None for the largest existing number plus one.
        frontmatter: Fields to merge into template defaults; generated identity is protected.

    Returns:
        Path: Resolved path of the new C-N-NNNN.md record after its schema and
            contextual checks pass. Initial values come from the local template.

    Raises:
        ValueError: No campaign is selected, numbering or scaffolding is invalid,
            or the generated record fails validation. Diagnostics are logged.
        OSError: A destination exists or a filesystem operation fails.
        KeyboardInterrupt: The partial record is removed before propagating.
    """
    root = select_vault(vault)
    campaign = require_campaign(root, campaign)
    directory = record_directory(root, "Clue", campaign)
    number = record_number(
        directory, campaign, number, kind="clue", prefix="C", digits=4
    )
    destination = directory / f"C-{campaign}-{number:04}.md"
    check_destination(destination)
    template = read_template(root, "Clue")
    metadata = merge_frontmatter(template.frontmatter, frontmatter)
    clue_text = metadata.get("text")
    if not isinstance(clue_text, str) or not clue_text.strip():
        raise ValueError(
            "provide nonblank text in frontmatter or the local Clue template"
        )
    metadata["text"] = clue_text
    metadata["subjects"] = _clue_subjects(clue_text, destination, VaultIndex(root))
    metadata = merge_frontmatter(metadata, frontmatter, protected=("type", "subjects"))
    for field in ("first_session", "last_session"):
        metadata.setdefault(field, None)
    text = record_text(metadata, template.body.text)
    return write_record(destination, text, root, "Clue")
