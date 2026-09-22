"""Mechanical history reconciliation; mentions never imply appearances or canon."""

import re
from pathlib import Path
from typing import Any

from armarium.context import campaign
from armarium.index import VaultIndex
from armarium.lib import Diagnostic
from armarium.markdown import links, values, visible_lines
from armarium.parse import Note


def resolved(value: Any, note: Note, index: VaultIndex) -> set[Path]:
    """Canonical identities in a value; unresolved links are handled by context."""
    found: set[Path] = set()
    for _, text in values(value):
        for target in links(text):
            path, _ = index.resolve(target, note.path)
            if path is not None:
                found.add(path)
    return found


def check(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Check Content history ranges and Clue subject synchronization."""
    relative = note.path.relative_to(index.root).as_posix()
    errors: list[Diagnostic] = []

    def error(rule: str, message: str, field: str = "", line: int = 0) -> None:
        errors.append(Diagnostic(relative, rule, message, field, line))

    if note.kind == "Clue":
        subjects = resolved(note.frontmatter.get("subjects"), note, index)
        text_content = set()
        for path in resolved(note.frontmatter.get("text"), note, index):
            if path.suffix.lower() == ".md":
                target, _ = index.note(path)
                if target and target.kind == "Content":
                    text_content.add(path)
        if subjects != text_content:
            error(
                "clue.subjects",
                "subjects must match canonical Content links in text",
                "subjects",
            )
        first = resolved(note.frontmatter.get("first_session"), note, index)
        last = resolved(note.frontmatter.get("last_session"), note, index)
        if first and last and min(p.stem for p in last) < min(p.stem for p in first):
            error(
                "history.order", "last_session precedes first_session", "last_session"
            )
        return errors
    if note.kind != "Content":
        return errors
    histories: dict[str, list[tuple[int, Path]]] = {}
    active = False
    section_scope: str | None = None
    scope = campaign(note.path, index.root)
    for number, line in visible_lines(note.body, queries=False):
        if line.startswith("## "):
            active = line.strip() == "## Appearances"
            continue
        if not active or not line.strip() or line.strip() == "- N/A":
            continue
        heading = re.fullmatch(r"### (campaign_\d+)\s*", line)
        if heading:
            section_scope = heading[1]
            continue
        match = re.fullmatch(r"- (\[\[[^\[\]|#]+\]\]):\s*(\S.*)", line)
        if not match:
            error(
                "history.format",
                "use - [[Session]]: description under Appearances",
                line=note.body_start_line + number - 1,
            )
            continue
        targets = resolved(match[1], note, index)
        for path in targets:
            session, _ = index.note(path)
            target_scope = campaign(path, index.root)
            ordinal = session.frontmatter.get("session_number") if session else None
            if (
                not session
                or session.kind != "Session"
                or type(ordinal) is not int
                or not target_scope
            ):
                error("target.kind", "appearance must reference a numbered Session")
                continue
            if (scope and scope != target_scope) or (
                section_scope and section_scope != target_scope
            ):
                error(
                    "history.campaign",
                    "appearance disagrees with containing campaign or heading",
                )
            histories.setdefault(target_scope, []).append((ordinal, path))
    blocks = {
        key: value
        for key, value in note.frontmatter.items()
        if re.fullmatch(r"campaign_\d+", key)
    }
    for name in sorted(histories.keys() | blocks.keys()):
        history = histories.get(name, [])
        ordinals = [ordinal for ordinal, _ in history]
        paths = [path for _, path in history]
        if ordinals != sorted(ordinals):
            error("history.order", f"{name} appearances must be chronological")
        if len(paths) != len(set(paths)):
            error("history.duplicate", f"{name} contains duplicate Session appearances")
        block = blocks.get(name)
        if not isinstance(block, dict):
            error("history.block", f"appearances require a {name} mapping", name)
            continue
        ordered = sorted(history)
        for field, expected in [
            ("first_session", ordered[0][1] if ordered else None),
            ("last_session", ordered[-1][1] if ordered else None),
        ]:
            actual = resolved(block.get(field), note, index)
            if actual != ({expected} if expected else set()) or (
                not expected and block.get(field) is not None
            ):
                error(
                    "history.range",
                    f"{name}.{field} must match recorded Appearances "
                    + (f"({expected.stem})" if expected else "(empty)"),
                    f"{name}.{field}",
                )
    return errors
