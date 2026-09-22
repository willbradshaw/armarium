"""Small explicit structural checks supplement, but do not replace, local schemas."""

import re

from armarium.index import VaultIndex
from armarium.lib import Diagnostic
from armarium.markdown import visible_lines
from armarium.parse import Note


def check(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Check real headings and template-declared keys without constraining views."""
    errors: list[Diagnostic] = []
    relative = note.path.relative_to(index.root).as_posix()

    def error(rule: str, message: str, field: str = "") -> None:
        errors.append(Diagnostic(relative, rule, message, field))

    if note.path.stem != note.path.stem.strip():
        error("record.filename", "remove leading/trailing filename whitespace")
    if note.kind in {"Session", "Clue", "Player", "Transcript"}:
        template_path = index.root / "reference/templates" / f"{note.kind}.md"
        if template_path.is_file():
            template, failures = index.note(template_path)
            if failures:
                error("template.invalid", "record template cannot be parsed")
            elif template:
                # Keys come from the current vault, avoiding a second schema registry.
                for field in sorted(
                    template.frontmatter.keys() - note.frontmatter.keys()
                ):
                    error(
                        "record.required",
                        f"missing template-declared field {field}",
                        field,
                    )
    headings = [
        line.rstrip()
        for _, line in visible_lines(note.body, queries=False)
        if re.match(r"^#{1,6} ", line)
    ]
    if note.kind == "Content":
        top = [line for line in headings if line.startswith("## ")]
        if top != ["## Notes", "## Active Clues", "## Appearances"]:
            error(
                "body.headings",
                "require Notes, Active Clues and Appearances once, in order",
            )
    elif note.kind == "Clue":
        if headings != ["## Sessions"]:
            error(
                "body.headings", "Clue body requires only the Sessions heading and view"
            )
    elif note.kind == "Session":
        top = [line for line in headings if line.startswith("# ")]
        if top != ["# Preparation", "# Notes"]:
            error("body.headings", "Session requires Preparation then Notes, once each")
        required = ["## Preamble", "## Events", "## Rewards"]
        if "# Notes" in headings:
            notes = headings[headings.index("# Notes") + 1 :]
            if [line for line in notes if line in required] != required:
                error(
                    "body.headings",
                    "Notes requires Preamble, Events and Rewards in order",
                )
    elif note.kind == "Transcript":
        if not any(line.startswith("## ") for line in headings):
            error("body.headings", "Transcript requires content section headings")
    return errors
