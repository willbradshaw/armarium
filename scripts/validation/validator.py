"""Read a user vault, run the rule checklist, and return ordered diagnostics."""

from collections.abc import Callable
from pathlib import Path

from .context import ValidationContext
from .discovery import read_vault
from .parsing import Diagnostic, Page, Resolver
from .rules.body import check_body_sections
from .rules.campaigns import check_campaign_state
from .rules.properties import check_property_values, check_required_properties
from .rules.records import check_record_identity, check_status_applicability
from .rules.structure import check_placement
from .rules.wikilinks import check_wikilinks
from .schema import CAMPAIGN

type Rule = Callable[[Page, ValidationContext], None]

# This is the complete page-rule checklist; YAML/read errors come from read_vault.
PAGE_RULES: tuple[Rule, ...] = (
    check_wikilinks,
    check_placement,
    check_required_properties,
    check_property_values,
    check_campaign_state,
    check_status_applicability,
    check_record_identity,
    check_body_sections,
)


def validate_vault(vault: str | Path) -> list[Diagnostic]:
    root = Path(vault).resolve()
    if not root.is_dir():
        return [Diagnostic(".", "structure.root", "Choose an existing vault directory.")]

    contents = read_vault(root)
    context = ValidationContext(
        pages=contents.pages,
        resolver=Resolver(contents.files, contents.pages),
        campaigns={path for path in contents.directories if CAMPAIGN.fullmatch(path)},
        errors=contents.errors,
    )
    for page in contents.pages.values():
        for check in PAGE_RULES:
            check(page, context)
    return sorted(
        context.errors,
        key=lambda error: (error.path, error.line or 0, error.field or "", error.rule),
    )
