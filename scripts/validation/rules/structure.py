"""Placement rules for typed records within shared-world and campaign scope."""

from ..context import ValidationContext
from ..parsing import Page
from ..schema import CAMPAIGN_ONLY, CONTENT_FOLDERS


def check_placement(page: Page, context: ValidationContext) -> None:
    kind = context.kind(page)
    if page.is_template or page.is_definition or kind is None or kind not in CONTENT_FOLDERS:
        return
    expected_folder = CONTENT_FOLDERS[kind]
    parts = page.parts
    in_expected_folder = len(parts) >= 3 and parts[1] == expected_folder

    if parts[0] == "world" and (kind in CAMPAIGN_ONLY or not in_expected_folder):
        scope = "campaign_<number>" if kind in CAMPAIGN_ONLY else "world"
        context.report(
            page, "structure.placement", f"Place {kind} under {scope}/{expected_folder}/.",
        )
    elif page.campaign and not in_expected_folder:
        context.report(
            page, "structure.placement",
            f"Place {kind} under {page.campaign}/{expected_folder}/.",
        )
