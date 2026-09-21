"""Required properties, nullable value shapes, and typed property links."""

from datetime import date

from ..context import ValidationContext
from ..parsing import Page
from ..schema import (
    CONTENT_FOLDERS, DEFINITION_LINK_FIELDS, LINK_LIST_FIELDS,
    RECORD_LINK_FIELDS, REQUIRED_FIELDS,
)


def check_required_properties(page: Page, context: ValidationContext) -> None:
    content_folder = (
        (page.parts[0] == "world" or page.campaign is not None)
        and len(page.parts) >= 3 and page.parts[1] in CONTENT_FOLDERS.values()
    )
    supported_template = page.is_template and page.stem in REQUIRED_FIELDS
    if content_folder or supported_template:
        context.require(page, page.data, ("type",))
    if page.parts[0] == "statuses":
        context.require(page, page.data, ("applies_to",))
    kind = context.kind(page)
    if not page.is_definition and kind is not None:
        context.require(page, page.data, REQUIRED_FIELDS.get(kind, ()))


def shape_error(field: str, value: object, *, template: bool) -> str | None:
    """Return the expected shape for a bad known value; null means unknown."""
    if value is None:
        return None
    match field:
        case "summary" | "text" | "pronouns":
            if not isinstance(value, str):
                return "text"
        case "aliases":
            if not isinstance(value, list) or not all(
                isinstance(alias, str) or (template and alias is None) for alias in value
            ):
                return "a list of strings"
        case "stats":
            if not isinstance(value, str | dict):
                return "text/a link or a system-specific mapping"
        case "birth_year":
            if not (type(value) is int or isinstance(value, str)):
                return "an integer or calendar-neutral text"
        case "date" | "in_game_start_date" | "in_game_end_date":
            if not (isinstance(value, str | date) or type(value) is int):
                return "date text or an integer (no calendar validation)"
        case "session_number":
            if type(value) is not int or value <= 0:
                return "a positive integer"
    return None


def check_property_values(page: Page, context: ValidationContext) -> None:
    """Extra properties are accepted; known shapes apply wherever supplied."""
    for field, value in page.data.items():
        if not isinstance(field, str):
            continue
        expected = shape_error(field, value, template=page.is_template)
        if expected:
            context.report(
                page, "field.shape", f"Expected {expected}, or null for unknown.",
                field=field,
            )
        if field in DEFINITION_LINK_FIELDS:
            context.check_link(
                page, value, field, directory=DEFINITION_LINK_FIELDS[field], nullable=False,
            )
        if field in RECORD_LINK_FIELDS:
            context.check_link(
                page, value, field, kinds=RECORD_LINK_FIELDS[field],
                nullable=field != "campaign",
            )
        if field in LINK_LIST_FIELDS:
            context.check_link_list(page, value, field, LINK_LIST_FIELDS[field])
