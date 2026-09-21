"""Campaign state is required in campaign scope and optional for shared entities."""

from pathlib import PurePosixPath

from ..context import ValidationContext
from ..parsing import Page
from ..schema import CAMPAIGN, ENTITY_FOLDERS, STATE_LINK_FIELDS


def check_campaign_state(page: Page, context: ValidationContext) -> None:
    if page.is_definition:
        return
    kind = context.kind(page)
    if kind in ENTITY_FOLDERS and page.campaign and page.campaign not in page.data:
        context.report(
            page, "identity.campaign", f"Add state for containing {page.campaign}.",
            field=page.campaign,
        )

    for campaign, state in page.data.items():
        if not isinstance(campaign, str) or not CAMPAIGN.fullmatch(campaign):
            continue
        if campaign not in context.campaigns:
            context.report(
                page, "identity.campaign", f"No {campaign}/ directory exists.", field=campaign,
            )
        if not isinstance(state, dict):
            context.report(
                page, "field.shape", "Campaign state must be a mapping with nullable values.",
                field=campaign,
            )
            continue
        required = ("first_session", "last_session")
        if kind == "Object":
            required += ("held_by",)
        context.require(page, state, required, prefix=campaign + ".")
        for field, kinds in STATE_LINK_FIELDS.items():
            if field not in state:
                continue
            target = context.check_link(page, state[field], f"{campaign}.{field}", kinds=kinds)
            if target and field in {"first_session", "last_session"}:
                check_session_campaign(page, context, target, campaign, f"{campaign}.{field}")


def check_session_campaign(
    page: Page, context: ValidationContext, target: str, campaign: str | None, field: str,
) -> None:
    if PurePosixPath(target).parts[0] != campaign:
        context.report(
            page, "identity.campaign", f"Session must belong to {campaign or 'the containing campaign'}.",
            field=field,
        )
