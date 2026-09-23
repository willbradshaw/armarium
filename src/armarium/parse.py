"""Safe frontmatter parsing with duplicate detection and JSON normalization."""

import math
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml
from markdown_it import MarkdownIt
from markdown_it.token import Token
from yaml.nodes import MappingNode

from armarium.lib import CAMPAIGN_NAME, Diagnostic, iter_wikilinks, parse_wikilink


class FrontmatterLoader(yaml.SafeLoader):
    """Load safe YAML frontmatter with unique keys and JSON-compatible values."""

    def construct_mapping(self, node: MappingNode, deep: bool = False) -> Any:
        """Construct a YAML mapping after checking its keys for duplicates.

        Args:
            node: YAML mapping node supplied by PyYAML.
            deep: Whether PyYAML should recursively construct nested values now.

        Returns:
            dict[Any, Any]: The mapping constructed by SafeLoader.

        Raises:
            ValueError: A key is not a scalar string representation.
            yaml.constructor.ConstructorError: A mapping contains duplicate keys.
        """
        seen: set[str] = set()
        for key, _ in node.value:
            if not isinstance(key.value, str):
                raise ValueError("frontmatter mapping keys must be strings")
            if key.value in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key: {key.value}", key.start_mark
                )
            seen.add(key.value)
        return super().construct_mapping(node, deep=deep)

    def get_single_data(self) -> Any:
        """Load and normalize one YAML document after constructing all aliases.

        Returns:
            Any: JSON-compatible metadata with ISO date/timestamp strings, or
                None for an empty document. The note parser checks that the
                top-level value is a mapping.

        Raises:
            yaml.YAMLError: The document is invalid or contains duplicate keys.
            ValueError: A constructed value cannot be represented in JSON.
        """
        return self._normalize(super().get_single_data())

    def _normalize(self, value: Any, ancestors: frozenset[int] = frozenset()) -> Any:
        """Convert parsed YAML values into JSON-compatible schema input.

        Args:
            value: A value produced by the safe YAML loader.
            ancestors: Container identities on the current recursion path. Callers
                should leave this empty; recursive calls use it to detect cycles.

        Returns:
            Any: A JSON-compatible value with dates/timestamps converted to ISO
                strings and dictionaries/lists copied recursively. The input is
                not modified.

        Raises:
            ValueError: A cycle, non-string mapping key, nonfinite float or other
                value that JSON cannot represent is encountered.
        """
        # YAML recognizes date scalars automatically; JSON schemas expect strings.
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, (dict, list)):
            # Track only the active path: two siblings may legitimately share a YAML
            # alias. A reference back to an ancestor is a cycle JSON cannot encode.
            if id(value) in ancestors:
                raise ValueError("recursive YAML aliases are not JSON-compatible")
            ancestors = ancestors | {id(value)}
            if isinstance(value, list):
                return [self._normalize(item, ancestors) for item in value]
            # JSON object keys must be strings; coercing keys would hide bad input
            # and could collapse distinct YAML keys into the same JSON key.
            if any(not isinstance(key, str) for key in value):
                raise ValueError("frontmatter mapping keys must be strings")
            return {
                key: self._normalize(item, ancestors) for key, item in value.items()
            }
        if value is None or isinstance(value, (str, bool, int)):
            return value
        # YAML accepts NaN and infinities, but they are not standard JSON numbers.
        if isinstance(value, float) and math.isfinite(value):
            return value
        raise ValueError("frontmatter contains a non-JSON YAML value")


@dataclass(frozen=True)
class Link:
    """One wikilink found in a note, and where it was found.

    Attributes:
        target: File target inside the brackets, without alias or anchor. Empty
            for a self-anchor such as ``[[#Heading]]`` or for malformed text.
        location: Dotted frontmatter location such as ``subjects.0`` or
            ``campaign_1.first_session``, or an empty string for a body link.
        line: One-based source line of a body link, or 0 for frontmatter.
        error: Parser message when the link text is malformed, otherwise None.
    """

    target: str
    location: str
    line: int
    error: str | None = None

    @property
    def field(self) -> str:
        """Return the frontmatter field containing the link, ignoring list indices.

        Returns:
            str: The location without numeric segments, so links in a field's
                list share its name: ``subjects.0`` gives ``subjects`` and
                ``campaign_1.held_by.2`` gives ``campaign_1.held_by``. Empty
                for body links.
        """
        return ".".join(part for part in self.location.split(".") if not part.isdigit())


class Frontmatter(Mapping[str, Any]):
    """A note's parsed YAML metadata and what checks derive from it.

    Behaves as a read-only mapping of the JSON-compatible values produced by
    FrontmatterLoader; an absent frontmatter is an empty mapping.
    """

    def __init__(self, data: Mapping[str, Any] | None = None) -> None:
        """Wrap parsed metadata.

        Args:
            data: Top-level mapping of the note's frontmatter, if any.
        """
        self._data: dict[str, Any] = dict(data or {})

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"Frontmatter({self._data!r})"

    @cached_property
    def type(self) -> str | None:
        """Return the declared record type name without resolving its target.

        Returns:
            str | None: The final path component of the canonical ``type``
                wikilink, without an optional .md extension, or None if the
                field is absent or malformed. ``[[types/Content.md]]`` declares
                Content. Whether the target is the correct definition is a
                contextual check.
        """
        # Missing/invalid type is classified by record validation; other callers
        # of the shared parser receive its ValueError directly.
        try:
            target = parse_wikilink(self._data.get("type"), canonical=True)
        except ValueError:
            return None
        return target.removesuffix(".md").rsplit("/", 1)[-1] if target else None

    @cached_property
    def campaigns(self) -> dict[str, dict[str, Any]]:
        """Return the campaign_N fields that hold mappings.

        Returns:
            dict[str, dict[str, Any]]: Campaign directory name to its block, in
                frontmatter order. A campaign_N field holding anything else is
                left for checks to report.
        """
        return {
            key: value
            for key, value in self._data.items()
            if CAMPAIGN_NAME.fullmatch(key) and isinstance(value, dict)
        }

    @cached_property
    def links(self) -> tuple[Link, ...]:
        """Find every wikilink in the frontmatter's strings.

        Nested mappings and lists are walked so each link keeps its location.

        Returns:
            tuple[Link, ...]: Links in metadata order, with malformed link text
                included with its error. No target is resolved here.
        """
        # Reverse children when adding them to the stack so nested values
        # retain their order.
        pending: list[tuple[str, object]] = [("", self._data)]
        links: list[Link] = []
        while pending:
            location, value = pending.pop()
            if isinstance(value, dict):
                pending.extend(
                    (f"{location}.{key}" if location else key, item)
                    for key, item in reversed(value.items())
                )
            elif isinstance(value, list):
                pending.extend(
                    (f"{location}.{number}", value[number])
                    for number in reversed(range(len(value)))
                )
            elif isinstance(value, str):
                for target in iter_wikilinks(value):
                    if isinstance(target, ValueError):
                        links.append(Link("", location, 0, str(target)))
                    else:
                        links.append(Link(target, location, 0))
        return tuple(links)


@dataclass(frozen=True)
class Block:
    """One block of Markdown inside a section or another block.

    Attributes:
        kind: paragraph, item, list, ordered_list, quote, code, table, rule,
            html, heading or other.
        line: One-based source line on which the block starts.
        text: A paragraph's text with wrapped lines joined; an item's first
            paragraph; code contents; heading text. Empty otherwise.
        children: A list's items, an item's further blocks, a quote's blocks.
        block_id: An Obsidian ``^id`` ending a paragraph or item, if any.
    """

    kind: str
    line: int
    text: str = ""
    children: tuple["Block", ...] = ()
    block_id: str | None = None


@dataclass(frozen=True)
class Section:
    """A heading, the blocks beneath it and its subsections.

    Attributes:
        title: Heading text as written.
        level: Heading level, 1 to 6.
        line: One-based source line of the heading.
        blocks: Top-level blocks between this heading and the next.
        children: Subsections, nested by heading level.
    """

    title: str
    level: int
    line: int
    blocks: tuple[Block, ...] = ()
    children: tuple["Section", ...] = ()


_BLOCK_ID = re.compile(r"^(.*?)\s*\^([A-Za-z0-9-]+)$", re.S)


@dataclass(frozen=True)
class Body:
    """A note's Markdown after the frontmatter, with its links and structure.

    Attributes:
        text: Markdown after the closing frontmatter delimiter, or the entire
            file when frontmatter is absent.
        start_line: One-based source-file line at which text begins; 1 without
            frontmatter, otherwise the line after the closing delimiter.
    """

    text: str
    start_line: int

    @cached_property
    def links(self) -> tuple[Link, ...]:
        """Find every wikilink in the body, line by line.

        Lines are scanned as written, including inline and fenced code.

        Returns:
            tuple[Link, ...]: Links in source order with source line numbers;
                malformed link text is included with its error.
        """
        links: list[Link] = []
        for line, text in enumerate(self.text.splitlines(), self.start_line):
            for target in iter_wikilinks(text):
                if isinstance(target, ValueError):
                    links.append(Link("", "", line, str(target)))
                else:
                    links.append(Link(target, "", line))
        return tuple(links)

    @cached_property
    def sections(self) -> tuple[Section, ...]:
        """Return the body's heading tree, parsed as CommonMark plus tables.

        Returns:
            tuple[Section, ...]: Top-level sections in document order, each
                holding its blocks and nested subsections. Headings inside
                fenced code do not count; setext headings do.
        """
        return self._structure[1]

    @cached_property
    def preamble(self) -> tuple[Block, ...]:
        """Return the blocks before the first heading.

        Returns:
            tuple[Block, ...]: Top-level blocks preceding any heading.
        """
        return self._structure[0]

    @cached_property
    def _structure(self) -> tuple[tuple[Block, ...], tuple[Section, ...]]:
        tokens = MarkdownIt("commonmark").enable("table").parse(self.text)
        preamble: list[Block] = []
        roots: list[dict[str, Any]] = []  # mutable section builders
        stack: list[dict[str, Any]] = []
        position = 0
        while position < len(tokens):
            token = tokens[position]
            end = _matching_close(tokens, position)
            if token.type == "heading_open":
                level = int(token.tag[1])
                section = {
                    "title": tokens[position + 1].content,
                    "level": level,
                    "line": self._line(token),
                    "blocks": [],
                    "children": [],
                }
                while stack and stack[-1]["level"] >= level:
                    stack.pop()
                (stack[-1]["children"] if stack else roots).append(section)
                stack.append(section)
            else:
                block = self._block(tokens, position, end)
                (stack[-1]["blocks"] if stack else preamble).append(block)
            position = end + 1
        return tuple(preamble), tuple(_freeze(section) for section in roots)

    def _line(self, token: Token) -> int:
        return (token.map[0] if token.map else 0) + self.start_line

    def _blocks(self, tokens: list[Token], start: int, end: int) -> tuple[Block, ...]:
        """Build the blocks for the tokens in [start, end)."""
        blocks: list[Block] = []
        position = start
        while position < end:
            close = _matching_close(tokens, position)
            blocks.append(self._block(tokens, position, close))
            position = close + 1
        return tuple(blocks)

    def _block(self, tokens: list[Token], start: int, end: int) -> Block:
        """Build one block from its opening token at start and closing at end."""
        token = tokens[start]
        line = self._line(token)
        kind = token.type.removesuffix("_open")
        if kind == "paragraph":
            text, block_id = _split_block_id(tokens[start + 1].content)
            return Block("paragraph", line, text, block_id=block_id)
        if kind == "heading":
            return Block("heading", line, tokens[start + 1].content)
        if kind in {"bullet_list", "ordered_list"}:
            name = "list" if kind == "bullet_list" else "ordered_list"
            return Block(name, line, children=self._blocks(tokens, start + 1, end))
        if kind == "list_item":
            children = self._blocks(tokens, start + 1, end)
            if children and children[0].kind == "paragraph":
                first, children = children[0], children[1:]
                return Block("item", line, first.text, children, first.block_id)
            return Block("item", line, children=children)
        if kind == "blockquote":
            return Block("quote", line, children=self._blocks(tokens, start + 1, end))
        if kind == "table":
            return Block("table", line)
        if kind in {"fence", "code_block"}:
            return Block("code", line, token.content)
        return Block({"hr": "rule", "html_block": "html"}.get(kind, "other"), line)


def _matching_close(tokens: list[Token], position: int) -> int:
    """Return the index closing the token at position; itself when self-closing."""
    depth = 0
    for index in range(position, len(tokens)):
        depth += tokens[index].nesting
        if depth == 0:
            return index
    raise ValueError("unbalanced Markdown token stream")


def _split_block_id(text: str) -> tuple[str, str | None]:
    """Separate a trailing Obsidian ^block-id from paragraph text."""
    text = text.replace("\n", " ")
    match = _BLOCK_ID.fullmatch(text)
    if match is None:
        return text, None
    return match[1], match[2]


def _freeze(section: dict[str, Any]) -> Section:
    """Convert a section builder and its children into frozen Sections."""
    return Section(
        section["title"],
        section["level"],
        section["line"],
        tuple(section["blocks"]),
        tuple(_freeze(child) for child in section["children"]),
    )


@dataclass(frozen=True)
class Note:
    """A note's parsed frontmatter and body.

    Attributes:
        path: Source Markdown file path.
        frontmatter: Parsed metadata, empty when the note has none.
        body: Markdown after the frontmatter, with its source position.
    """

    path: Path
    frontmatter: Frontmatter
    body: Body

    @property
    def links(self) -> tuple[Link, ...]:
        """Return every wikilink in the note.

        Returns:
            tuple[Link, ...]: Frontmatter links in metadata order, then body
                links in source order. No target is resolved here.
        """
        return self.frontmatter.links + self.body.links

    @classmethod
    def parse(cls, path: Path, root: Path) -> tuple["Note | None", list[Diagnostic]]:
        """Read a Markdown note, returning either its contents or an error report.

        Args:
            path: Markdown file inside root. Both paths must use the same absolute
                or relative form so a vault-relative diagnostic path can be formed.
            root: Vault directory used to label errors with relative file paths.

        Returns:
            tuple[Note | None, list[Diagnostic]]: A pair of (note, diagnostics).
                Success returns a Note and an empty list. Read, YAML and normalization
                failures return None and a Diagnostic with rule ``parse.invalid``.
                A Diagnostic is data describing the failure, not an exception: the
                caller can report it and keep checking other files. This function
                neither prints nor changes the source file.

        Raises:
            ValueError: path is not lexically inside root (a caller contract error).
        """
        relative = path.relative_to(root).as_posix()
        try:
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError("note escapes the vault boundary")
            text = path.read_text(encoding="utf-8-sig")
            lines = text.splitlines(keepends=True)
            if not lines or lines[0].strip() != "---":
                return cls(path, Frontmatter(), Body(text, 1)), []
            end = next(
                (i for i in range(1, len(lines)) if lines[i].strip() == "---"), None
            )
            if end is None:
                raise ValueError("frontmatter has no closing --- delimiter")
            data = yaml.load("".join(lines[1:end]), Loader=FrontmatterLoader)
            if data is None:
                data = {}
            if not isinstance(data, dict):
                raise ValueError("frontmatter must be a mapping")
            body = Body("".join(lines[end + 1 :]), end + 2)
            return cls(path, Frontmatter(data), body), []
        except (
            OSError,
            UnicodeError,
            yaml.YAMLError,
            ValueError,
            RecursionError,
        ) as exc:
            # PyYAML counts from zero within the frontmatter slice. Add two for
            # one-based file lines and the opening --- delimiter omitted above.
            mark = getattr(exc, "problem_mark", None)
            return None, [
                Diagnostic(
                    relative,
                    "parse.invalid",
                    str(exc),
                    line=mark.line + 2 if mark else 0,
                )
            ]
