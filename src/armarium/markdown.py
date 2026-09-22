"""Small Markdown readers for real links and structural headings."""

import re
from collections.abc import Iterator
from typing import Any

from armarium.lib import iter_wikilinks


def visible_lines(body: str, queries: bool = True) -> Iterator[tuple[int, str]]:
    """Ignore illustrative fences; optionally retain executable view contents."""
    fence = ""
    length = 0
    active = False
    for number, line in enumerate(body.splitlines(), 1):
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", line)
        if match:
            marker, info = match.groups()
            if not fence:
                fence, length = marker[0], len(marker)
                active = queries and info.strip().lower() in {"dataview", "dataviewjs"}
            elif marker[0] == fence and len(marker) >= length and not info.strip():
                fence, active = "", False
            continue
        if not fence or active:
            yield number, line


def links(text: str) -> list[str]:
    """Extract file targets from wikilinks in text.

    Args:
        text: Text containing zero or more wikilinks.

    Returns:
        list[str]: Targets in occurrence order, retaining duplicates. The shared
            wikilink parser removes display aliases and anchors; a self-anchor
            yields an empty target. Malformed candidates are excluded here;
            contextual validation reports them separately as link.syntax errors.
    """
    return [result for result in iter_wikilinks(text) if isinstance(result, str)]


def values(value: Any, field: str = "") -> Iterator[tuple[str, str]]:
    """Visit textual YAML values, retaining their field paths."""
    if isinstance(value, str):
        yield field, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from values(item, f"{field}.{key}".strip("."))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from values(item, f"{field}.{index}")
