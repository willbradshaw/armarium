"""Shared syntax utilities independent of note parsing and vault validation."""

import re
from collections.abc import Iterator

_WIKILINK = re.compile(r"\[\[([^\[\]\r\n]+)\]\]")


def parse_wikilink(value: object, *, canonical: bool = False) -> str:
    """Extract the file target from one complete wikilink.

    Args:
        value: Candidate wikilink, including its double brackets. Non-strings
            and text surrounding a wikilink are not accepted.
        canonical: Require a file target without a display alias or anchor.
            Use this for identity fields such as a note's declared type.

    Returns:
        str: The file target, with surrounding whitespace, display alias and
            anchor removed. A self-anchor such as ``[[#Heading]]`` returns an
            empty string when canonical is False. Paths and optional .md
            extensions are preserved; target existence is not checked.

    Raises:
        ValueError: The input is not one complete wikilink, its target is empty,
            or canonical is True and the link contains an alias or anchor.
    """
    if not isinstance(value, str):
        raise ValueError("wikilink must be a string")
    match = _WIKILINK.fullmatch(value)
    if match is None:
        raise ValueError("use [[target]] with balanced double brackets on one line")
    contents = match[1].replace("\\|", "|")
    if canonical and ("|" in contents or "#" in contents):
        raise ValueError(
            "canonical wikilinks cannot contain display aliases or anchors"
        )
    target = contents.split("|", 1)[0].split("#", 1)[0].strip()
    if not target and (canonical or not contents.startswith("#")):
        raise ValueError("wikilink target must not be empty")
    return target


def _find_wikilink_candidates(text: str) -> Iterator[str]:
    """Find wikilink candidates, retaining malformed delimiters for validation.

    Args:
        text: Text to scan. The caller decides which Markdown regions are prose
            or executable queries and which are illustrative code.

    Yields:
        str: Candidate text, including unmatched delimiters, nested openers and empty
            links. A new opener recovers scanning after an unclosed link,
            preserving later links.
    """
    start: int | None = None
    for match in re.finditer(r"\[\[|\]\]", text):
        if match[0] == "[[":
            if start is not None:
                yield text[start : match.start()]
            start = match.start()
        elif start is None:
            yield match[0]
        else:
            yield text[start : match.end()]
            start = None
    if start is not None:
        yield text[start:]


def iter_wikilinks(text: str) -> Iterator[str | ValueError]:
    """Parse links in text, returning syntax errors without stopping the scan.

    Args:
        text: Text to scan. The caller excludes illustrative code or other
            regions where wikilink syntax should not be interpreted.

    Yields:
        str | ValueError: The parsed file target or the ValueError explaining
            invalid syntax.
            A valid self-anchor has an empty-string target. Errors are yielded
            as data, not raised, so later links are still parsed.
    """
    for candidate in _find_wikilink_candidates(text):
        try:
            target = parse_wikilink(candidate)
        except ValueError as exc:
            yield exc
        else:
            yield target
