"""Edit a record's frontmatter in place, keeping its formatting."""

import json
import re
from collections.abc import Callable
from typing import Any

import yaml

from armarium.lib import line_ending
from armarium.parse import PARSE_ERRORS, Frontmatter

# A top-level key opening a line of frontmatter, quoted or plain.
TOP_KEY = re.compile(r"""("[^"]*"|'[^']*'|(?!- |#)[^\s'"][^:#]*?)[ \t]*:(?:\s|$)""")

# Keys that YAML reads as written without quotes.
PLAIN_KEY = re.compile(r"[A-Za-z_][\w-]*")


def rewrite_frontmatter(
    lines: list[str],
    expected: dict[str, Any],
    edit: Callable[[str], str] | None = None,
) -> list[str]:
    """Rewrite frontmatter source so that it reads as an expected mapping.

    The source is first edited line by line, which keeps its formatting.
    When that does not give the expected mapping, each top-level field whose
    value changes is written afresh, and each new field is added at the end.

    Args:
        lines: The frontmatter's lines, delimiters included, with endings.
        expected: The mapping the frontmatter must read as.
        edit: A function from one source line to its edited text, tried
            first; None to write changed fields afresh at once.

    Returns:
        list[str]: The new lines, delimiters included.

    Raises:
        ValueError: Neither way gives the expected mapping.
    """
    newline = line_ending(lines[0] if lines else "")
    if edit is not None:
        edited = [lines[0], *(edit(line) for line in lines[1:-1]), lines[-1]]
        if _reads_as(edited, expected):
            return edited
    current = dict(Frontmatter.parse("".join(lines))[0])
    inner = lines[1:-1]
    spans = _fields(inner)
    for key in reversed(list(spans)):
        if key in expected and expected[key] != current.get(key):
            start, end = spans[key]
            inner[start:end] = [line + newline for line in emit(key, expected[key])]
    for key, value in expected.items():
        if key not in spans:
            inner += [line + newline for line in emit(key, value)]
    rewritten = [lines[0], *inner, lines[-1]]
    if not _reads_as(rewritten, expected):
        raise ValueError("its frontmatter cannot be rewritten; edit it by hand")
    return rewritten


def set_field(text: str, key: str, value: Any) -> str:
    """Set one top-level frontmatter field of a record, keeping its other lines.

    Args:
        text: Whole text of a record.
        key: Top-level field name.
        value: The value the field should hold, as JSON can represent it.

    Returns:
        str: The record's text with the field set, written as emit writes
            it; an absent field is added at the end of the frontmatter.

    Raises:
        ValueError: The record has no frontmatter, or the field cannot be set
            without changing another field.
        yaml.YAMLError: The frontmatter is invalid YAML.
    """
    frontmatter, length = Frontmatter.parse(text)
    if not length:
        raise ValueError("record has no frontmatter")
    lines = text.splitlines(keepends=True)
    head = rewrite_frontmatter(lines[:length], {**frontmatter, key: value})
    return "".join(head + lines[length:])


def _reads_as(lines: list[str], expected: dict[str, Any]) -> bool:
    """Tell whether frontmatter source reads as a mapping."""
    try:
        return dict(Frontmatter.parse("".join(lines))[0]) == expected
    except PARSE_ERRORS:
        return False


def _fields(lines: list[str]) -> dict[str, tuple[int, int]]:
    """Find the lines each top-level field of frontmatter source spans.

    Args:
        lines: The frontmatter's lines, without delimiters.

    Returns:
        dict[str, tuple[int, int]]: Each key to the start and end of its
            lines; blank lines and comments ending a span are left out of it.
    """
    starts: list[tuple[int, str]] = []
    for number, line in enumerate(lines):
        match = TOP_KEY.match(line)
        if match is not None:
            token = match[1]
            key = yaml.safe_load(token) if token[0] in "\"'" else token.strip()
            starts.append((number, str(key)))
    spans: dict[str, tuple[int, int]] = {}
    for position, (start, key) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        while end > start + 1 and (
            not lines[end - 1].strip() or lines[end - 1].startswith("#")
        ):
            end -= 1
        spans[key] = (start, end)
    return spans


def emit(key: str, value: Any, indent: int = 0) -> list[str]:
    """Write one frontmatter field as YAML, in the style of the vault's records.

    Strings are double-quoted, lists of scalars written inline, mappings as
    indented blocks and null as an empty value.

    Args:
        key: The field's name.
        value: Its value, as JSON can represent it.
        indent: Nesting depth, two spaces per level.

    Returns:
        list[str]: The field's lines, without line endings.
    """
    pad = "  " * indent
    name = key if PLAIN_KEY.fullmatch(key) else json.dumps(key, ensure_ascii=False)
    if isinstance(value, dict) and value:
        lines = [f"{pad}{name}:"]
        for item_key, item in value.items():
            lines += emit(str(item_key), item, indent + 1)
        return lines
    return [f"{pad}{name}: {_scalar(value)}".rstrip()]


def _scalar(value: Any) -> str:
    """Write a value on one line: null as nothing, the rest as JSON."""
    if value is None:
        return ""
    if isinstance(value, list):
        return "[" + ", ".join(_scalar(item) or "null" for item in value) + "]"
    return json.dumps(value, ensure_ascii=False)


def open_quote(line: str, position: int) -> str:
    """Tell which YAML quote, if any, is open at a position in a line.

    Args:
        line: One line of YAML.
        position: An index into it.

    Returns:
        str: ``"`` or ``'`` for the open quote, or empty outside quotes.
    """
    quote = ""
    index = 0
    while index < position:
        character = line[index]
        if quote == '"' and character == "\\":
            index += 2
            continue
        if character == quote:
            quote = ""
        elif not quote and character in "\"'":
            quote = character
        index += 1
    return quote


def requote(text: str, quote: str) -> str:
    """Escape text to sit inside a YAML string opened by a quote.

    Args:
        text: The text.
        quote: ``"`` or ``'`` for the string's quote, or empty outside one.

    Returns:
        str: The text as the string must hold it to read as the text.
    """
    if quote == '"':
        return text.replace("\\", "\\\\").replace('"', '\\"')
    if quote == "'":
        return text.replace("'", "''")
    return text
