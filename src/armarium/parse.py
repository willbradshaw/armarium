"""Safe frontmatter parsing with duplicate detection and JSON normalization."""

import math
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, replace
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
        anchor: Heading path or ``^block-id`` after ``#``, or empty.
    """

    target: str
    location: str
    line: int
    error: str | None = None
    anchor: str = ""

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
                for parsed in iter_wikilinks(value):
                    if isinstance(parsed, ValueError):
                        links.append(Link("", location, 0, str(parsed)))
                    else:
                        links.append(Link(parsed[0], location, 0, anchor=parsed[1]))
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

    def walk(self) -> Iterator["Block"]:
        """Yield this block and every block nested inside it, in order.

        Yields:
            Block: This block, then each child's walk in turn.
        """
        yield self
        for child in self.children:
            yield from child.walk()

    _BLOCK_ID = re.compile(r"^(.*?)\s*\^([A-Za-z0-9-]+)$", re.S)
    _LEAF_KINDS = {
        "fence": "code",
        "code_block": "code",
        "hr": "rule",
        "html_block": "html",
    }

    @classmethod
    def from_tokens(
        cls, tokens: list[Token], start: int, start_line: int
    ) -> tuple["Block", int]:
        """Build the block that opens at a token, with everything it contains.

        Args:
            tokens: A markdown-it token stream.
            start: Index of the block's opening or self-closing token.
            start_line: Source line of the stream's first line.

        Returns:
            tuple[Block, int]: The block, and the index just after its last
                token.
        """
        token = tokens[start]
        end = cls._close(tokens, start)
        line = start_line + (token.map[0] if token.map else 0)
        kind = token.type.removesuffix("_open")
        if kind == "paragraph":
            text, block_id = cls._split_block_id(tokens[start + 1].content)
            return cls("paragraph", line, text, block_id=block_id), end + 1
        if kind == "heading":
            return cls("heading", line, tokens[start + 1].content), end + 1
        if kind in {"bullet_list", "ordered_list", "blockquote"}:
            name = {"bullet_list": "list", "blockquote": "quote"}.get(kind, kind)
            children = cls._sequence(tokens, start + 1, end, start_line)
            return cls(name, line, children=children), end + 1
        if kind == "list_item":
            children = cls._sequence(tokens, start + 1, end, start_line)
            if children and children[0].kind == "paragraph":
                first, children = children[0], children[1:]
                return cls("item", line, first.text, children, first.block_id), end + 1
            return cls("item", line, children=children), end + 1
        if kind == "table":
            return cls("table", line), end + 1
        if kind in {"fence", "code_block"}:
            return cls("code", line, token.content), end + 1
        return cls(cls._LEAF_KINDS.get(kind, "other"), line), end + 1

    @classmethod
    def _sequence(
        cls, tokens: list[Token], start: int, end: int, start_line: int
    ) -> tuple["Block", ...]:
        """Build every block in the tokens [start, end)."""
        blocks: list[Block] = []
        position = start
        while position < end:
            block, position = cls.from_tokens(tokens, position, start_line)
            blocks.append(block)
        return tuple(blocks)

    @staticmethod
    def _close(tokens: list[Token], position: int) -> int:
        """Return the index closing the token at position; itself when self-closing."""
        depth = 0
        for index in range(position, len(tokens)):
            depth += tokens[index].nesting
            if depth == 0:
                return index
        raise ValueError("unbalanced Markdown token stream")

    @classmethod
    def _split_block_id(cls, text: str) -> tuple[str, str | None]:
        """Separate a trailing Obsidian ^block-id from paragraph text."""
        text = text.replace("\n", " ")
        match = cls._BLOCK_ID.fullmatch(text)
        if match is None:
            return text, None
        return match[1], match[2]


@dataclass(frozen=True)
class Section:
    """A heading, the blocks beneath it and its subsections.

    A Body is the level-0 Section of a note: its blocks precede the first
    heading and its children are the top-level headed sections.

    Attributes:
        title: Heading text as written; empty for a body.
        level: Heading level, 1 to 6, or 0 for a body.
        line: One-based source line of the heading, or where a body starts.
        blocks: Blocks between this heading and the next.
        children: Subsections, nested by heading level.
    """

    title: str
    level: int
    line: int
    blocks: tuple[Block, ...] = ()
    children: tuple["Section", ...] = ()

    def walk(self) -> Iterator["Section"]:
        """Yield this section and every descendant in document order.

        Yields:
            Section: This section, then each child's walk in turn.
        """
        yield self
        for child in self.children:
            yield from child.walk()

    @classmethod
    def nest(cls, entries: list["Section | Block"]) -> tuple["Section", ...]:
        """Arrange a flat run of headings and blocks into a tree by level.

        Args:
            entries: Headings as childless Sections, each followed by the
                blocks beneath it, in document order. The first entry must be
                a heading.

        Returns:
            tuple[Section, ...]: The top-level sections, each holding its
                blocks and, nested beneath it, every following heading that is
                deeper until one of its own level or shallower.
        """
        sections, _ = cls._nest(entries, 0, 0)
        return sections

    @classmethod
    def _nest(
        cls, entries: list["Section | Block"], position: int, level: int
    ) -> tuple[tuple["Section", ...], int]:
        """Build the sections deeper than level from entries at position."""
        sections: list[Section] = []
        while position < len(entries):
            entry = entries[position]
            assert isinstance(entry, Section)  # blocks are consumed below
            if entry.level <= level:
                break
            position += 1
            blocks: list[Block] = []
            while position < len(entries):
                following = entries[position]
                if not isinstance(following, Block):
                    break
                blocks.append(following)
                position += 1
            children, position = cls._nest(entries, position, entry.level)
            sections.append(replace(entry, blocks=tuple(blocks), children=children))
        return tuple(sections), position


@dataclass(frozen=True, init=False)
class Body(Section):
    """A note's Markdown after the frontmatter: its text, links and structure.

    The body is the level-0 Section of the note, parsed as CommonMark plus
    tables when constructed. Headings inside fenced code do not count; setext
    headings do. Its ``line`` is the source line at which the text begins.

    Attributes:
        text: Markdown after the closing frontmatter delimiter, or the entire
            file when frontmatter is absent.
    """

    # Set in __init__; a dataclass field after Section's defaulted fields
    # must itself declare a default.
    text: str = ""

    _PARSER = MarkdownIt("commonmark").enable("table")

    def __init__(self, text: str, start_line: int = 1) -> None:
        """Parse the body's structure.

        Args:
            text: Markdown after the frontmatter.
            start_line: One-based source-file line at which text begins; 1
                without frontmatter, otherwise the line after the closing
                delimiter.
        """
        object.__setattr__(self, "text", text)
        tokens = self._PARSER.parse(text)
        # Blocks before the first heading belong to the body itself; from the
        # first heading on, headings and blocks are nested by level.
        blocks: list[Block] = []
        entries: list[Section | Block] = []
        position = 0
        while position < len(tokens):
            token = tokens[position]
            if token.type == "heading_open":
                line = start_line + (token.map[0] if token.map else 0)
                title = tokens[position + 1].content
                entries.append(Section(title, int(token.tag[1]), line))
                position += 3  # heading_open, inline, heading_close
                continue
            block, position = Block.from_tokens(tokens, position, start_line)
            (entries if entries else blocks).append(block)
        super().__init__("", 0, start_line, tuple(blocks), Section.nest(entries))

    @cached_property
    def links(self) -> tuple[Link, ...]:
        """Find every wikilink in the body, line by line.

        Lines are scanned as written, including inline and fenced code.

        Returns:
            tuple[Link, ...]: Links in source order with source line numbers;
                malformed link text is included with its error.
        """
        links: list[Link] = []
        for line, text in enumerate(self.text.splitlines(), self.line):
            for parsed in iter_wikilinks(text):
                if isinstance(parsed, ValueError):
                    links.append(Link("", "", line, str(parsed)))
                else:
                    links.append(Link(parsed[0], "", line, anchor=parsed[1]))
        return tuple(links)


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
