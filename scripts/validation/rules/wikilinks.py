"""Check syntax and canonical targets in frontmatter, prose and Dataview."""

from ..context import ValidationContext
from ..parsing import Page, scan_links


def check_wikilinks(page: Page, context: ValidationContext) -> None:
    links, errors = scan_links(page)
    context.errors.extend(errors)
    for link in links:
        _, rule, message = context.resolver.resolve(link.target, page.path)
        if rule and message:
            context.report(page, rule, message, line=link.line)
