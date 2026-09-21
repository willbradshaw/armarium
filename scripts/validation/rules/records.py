"""Identity of actual Sessions/Clues and applicability of Clue statuses."""

import re

from ..context import ValidationContext
from ..parsing import Page
from ..schema import CAMPAIGN
from .campaigns import check_session_campaign


def check_status_applicability(page: Page, context: ValidationContext) -> None:
    if page.is_definition or context.kind(page) != "Clue":
        return
    status_path = context.target(page.data.get("status"), page)
    if status_path is None:
        return
    status = context.pages.get(status_path)
    if status is None:
        return  # Missing links and incorrect field shapes have their own diagnostics.
    applies_to = context.target(status.data.get("applies_to"), status)
    if applies_to != "types/Clue.md":
        context.report(
            page, "status.applicability",
            "Choose a status whose applies_to resolves to types/Clue.", field="status",
        )


def check_record_identity(page: Page, context: ValidationContext) -> None:
    kind = context.kind(page)
    if page.is_template or page.is_definition or kind not in {"Session", "Clue"}:
        return

    prefix, width = ("S", 3) if kind == "Session" else ("C", 4)
    match = re.fullmatch(rf"{prefix}-([0-9]+)-([0-9]{{{width}}})", page.stem)
    if match is None:
        context.report(
            page, "identity.filename", f"Name this record {prefix}-<campaign>-{'N' * width}.md.",
        )
    campaign_match = CAMPAIGN.fullmatch(page.campaign) if page.campaign else None
    campaign_id = campaign_match[1] if campaign_match else None
    if campaign_id is None or (match and match[1] != campaign_id):
        context.report(
            page, "identity.campaign",
            "Filename campaign ID must agree with the containing campaign_<number> directory.",
        )

    if kind == "Session":
        number = page.data.get("session_number")
        if type(number) is not int or (match and number != int(match[2])):
            context.report(
                page, "identity.session-number",
                "Set session_number to the integer in the filename.", field="session_number",
            )
        campaign_path = context.target(page.data.get("campaign"), page)
        if campaign_path and campaign_path != f"{page.campaign}/Campaign.md":
            context.report(
                page, "identity.campaign",
                "Campaign link must resolve to the containing campaign's Campaign.md.",
                field="campaign",
            )

    for field in ("first_session", "last_session"):
        target = context.target(page.data.get(field), page)
        if target:
            check_session_campaign(page, context, target, page.campaign, field)
