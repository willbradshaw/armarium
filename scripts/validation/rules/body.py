"""Required headings and their order; query text and extra content are unrestricted."""

import re

from ..context import ValidationContext
from ..parsing import Page, markdown_lines
from ..schema import ENTITY_FOLDERS, ENTITY_HEADINGS, SESSION_HEADINGS, Heading


def required_headings(page: Page, kind: str | None) -> tuple[Heading, ...]:
    if page.is_definition:
        return ()
    if kind in ENTITY_FOLDERS or (page.is_template and page.stem == "Content"):
        return ENTITY_HEADINGS
    match kind:
        case "Session":
            return SESSION_HEADINGS
        case "Clue":
            return ((2, "Sessions"),)
        case _:
            return ()


def check_body_sections(page: Page, context: ValidationContext) -> None:
    required = required_headings(page, context.kind(page))
    if not required:
        return
    headings: list[Heading] = []
    for _, line, prose in markdown_lines(page.body):
        if prose and (match := re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)):
            headings.append((len(match[1]), match[2]))

    positions = []
    for heading in required:
        if heading not in headings:
            level, title = heading
            context.report(page, "body.section", f"Add {'#' * level} {title}.")
        else:
            positions.append(headings.index(heading))
    if positions != sorted(positions):
        context.report(page, "body.order", "Keep required sections in the documented order.")
