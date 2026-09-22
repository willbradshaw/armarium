"""Canonical relationship ledgers, campaign isolation and bounded cycle checks."""

import re
from pathlib import Path
from typing import Any

from armarium.consistency import resolved
from armarium.context import campaign
from armarium.index import VaultIndex
from armarium.lib import Diagnostic, parse_wikilink
from armarium.markdown import links, values, visible_lines
from armarium.parse import Note


def check(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Validate declared relationship identities without inferring narrative facts."""
    root = index.root
    relative = note.path.relative_to(root).as_posix()
    scope = campaign(note.path, root)
    errors: list[Diagnostic] = []

    def error(rule: str, message: str, field: str = "") -> None:
        errors.append(Diagnostic(relative, rule, message, field))

    def ledger(value: Any, field: str) -> None:
        items = value if isinstance(value, list) else [value]
        seen: set[Path] = set()
        for item in items:
            try:
                parse_wikilink(item, canonical=True)
            except ValueError as exc:
                error("relationship.canonical", str(exc), field)
                continue
            targets = resolved(item, note, index)
            if seen & targets:
                error("relationship.duplicate", "duplicate canonical target", field)
            seen.update(targets)

    for field in ("subjects", "members", "plays", "players_absent"):
        value = note.frontmatter.get(field)
        if value is not None:
            if not isinstance(value, list):
                error(
                    "relationship.shape",
                    "expected a list of canonical links or null",
                    field,
                )
            else:
                ledger(value, field)
    for field in (
        "session",
        "campaign",
        "player",
        "parent_location",
        "superseded_by",
        "first_session",
        "last_session",
        "status",
    ):
        value = note.frontmatter.get(field)
        if value is not None:
            ledger(value, field)
    if scope:
        for field in note.frontmatter:
            if re.fullmatch(r"campaign_\d+", field) and field != scope:
                error(
                    "campaign.isolation",
                    "campaign block disagrees with record placement",
                    field,
                )
        texts = list(values(note.frontmatter))
        texts += [("", line) for _, line in visible_lines(note.body)]
        for field, text in texts:
            for path in resolved(text, note, index):
                target_scope = campaign(path, root)
                if target_scope and target_scope != scope:
                    error(
                        "campaign.isolation",
                        f"target belongs to {target_scope}, not {scope}",
                        field,
                    )
    if note.kind == "Transcript":
        targets = resolved(note.frontmatter.get("session"), note, index)
        if len(targets) != 1:
            error(
                "transcript.session", "Transcript requires one Session link", "session"
            )
        elif note.path.stem != f"{next(iter(targets)).stem} Transcript":
            error(
                "record.identity",
                "Transcript filename must be <Session ID> Transcript.md",
            )
    if note.kind == "Clue":
        statuses = resolved(note.frontmatter.get("status"), note, index)
        if (
            root / "reference/statuses/Superseded.md" in statuses
            and not note.frontmatter.get("superseded_by")
        ):
            error(
                "clue.replacement",
                "Superseded Clue requires superseded_by",
                "superseded_by",
            )
        for path in resolved(note.frontmatter.get("superseded_by"), note, index):
            target, _ = index.note(path)
            if not target or target.kind != "Clue" or campaign(path, root) != scope:
                error(
                    "clue.replacement",
                    "replacement must be a Clue in this campaign",
                    "superseded_by",
                )
    relationship = (
        "parent_location"
        if note.kind == "Content" and note.frontmatter.get("subtype") == "Location"
        else "superseded_by"
        if note.kind == "Clue"
        else None
    )
    if relationship:
        seen = {note.path}
        current = note
        while True:
            targets = resolved(current.frontmatter.get(relationship), current, index)
            if len(targets) != 1:
                break
            path = next(iter(targets))
            if path in seen:
                error(
                    "relationship.cycle",
                    f"{relationship} chain contains a cycle",
                    relationship,
                )
                break
            seen.add(path)
            if path.suffix.lower() != ".md":
                break
            following, failures = index.note(path)
            if failures:
                error(
                    "link.malformed",
                    f"{relationship} chain contains a malformed note",
                    relationship,
                )
            if following is None:
                break
            current = following
    for number, line in visible_lines(note.body):
        if line.lstrip().startswith("|"):
            for match in re.finditer(r"\[\[[^\[\]]*(?<!\\)\|[^\[\]]*\]\]", line):
                if links(match[0]):
                    errors.append(
                        Diagnostic(
                            relative,
                            "link.table-pipe",
                            "escape the display-alias pipe as \\| in tables",
                            line=note.body_start_line + number - 1,
                        )
                    )
    return errors
