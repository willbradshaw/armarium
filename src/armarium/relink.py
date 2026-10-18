"""Plan and make the link changes that renaming or removing a record needs."""

import codecs
import json
import os
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml

from armarium.extensions import is_template
from armarium.index import VaultIndex, link_key
from armarium.lib import (
    WIKILINK,
    Result,
    find_files,
    record_files,
    relative_posix,
    split_wikilink,
    wikilink_text,
)
from armarium.parse import Body, Frontmatter
from armarium.trace import mentioning, sharing, spellings
from armarium.validate import validate_markdown

# Failures decoding or parsing a record's text.
PARSE_ERRORS = (UnicodeError, yaml.YAMLError, ValueError, RecursionError)

# One link, embedded or not: the embed mark, then the link's contents.
LINK = re.compile(r"(!?)" + WIKILINK.pattern)

# A link's contents: space, the target, space, then its anchor or display alias.
CONTENTS = re.compile(r"(\s*)(.*?)(\s*)((?:\\?\||#).*)?", re.DOTALL)

# Files other than records in which Obsidian follows links.
LINKING_SUFFIXES = (".md", ".base", ".canvas")

# A Markdown link's destination, with or without angle brackets.
MARKDOWN_LINK = re.compile(r"\]\(<?([^()<>]+?)>?\)")

# A top-level key opening a line of frontmatter, quoted or plain.
TOP_KEY = re.compile(r"""("[^"]*"|'[^']*'|(?!- |#)[^\s'"][^:#]*?)[ \t]*:(?:\s|$)""")

# Keys that YAML reads as written without quotes.
PLAIN_KEY = re.compile(r"[A-Za-z_][\w-]*")

# A list item dropped from frontmatter.
_DROP = object()


@dataclass(frozen=True)
class Change:
    """One change to the vault's files.

    Attributes:
        relative: Vault-relative path of the changed file, with forward
            slashes, as it is before the change.
        where: The frontmatter field or body headings where a changed link
            sits, as armarium trace gives them; empty for a whole file.
        line: One-based line of a changed body link, or 0.
        text: What changes, such as ``[[Old]] → [[New]]``.
    """

    relative: str
    where: str
    line: int
    text: str

    @property
    def output(self) -> str:
        """Return the change as one tab-separated line of output.

        Returns:
            str: Path, location, line number and change; the line number is
                empty for a frontmatter link or a whole file.
        """
        return "\t".join((self.relative, self.where, str(self.line or ""), self.text))


@dataclass
class Plan:
    """Every file change one command makes, worked out before any is made.

    Attributes:
        root: Resolved vault directory.
        texts: New contents of each file whose text changes, by its path
            before any rename.
        renamed: Each renamed file's path to its new path.
        deleted: Files to delete.
        changes: What changes, in path and line order, for the output.
        notes: Links to the changed files that are left as they are, each
            with why, for the user to check.
    """

    root: Path
    texts: dict[Path, str] = field(default_factory=dict)
    renamed: dict[Path, Path] = field(default_factory=dict)
    deleted: set[Path] = field(default_factory=set)
    changes: list[Change] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def touched(self) -> list[Path]:
        """List the records that remain after the change and were changed.

        Returns:
            list[Path]: Their paths after any rename, in path order.
        """
        paths = {self.renamed.get(path, path) for path in [*self.texts, *self.renamed]}
        return sorted(paths - self.deleted)

    def apply(self) -> None:
        """Write the new texts, then rename and delete files.

        Each file is replaced whole, so a reader never sees half of it.

        Raises:
            OSError: A file cannot be written, renamed or deleted; the
                changes made until then are kept.
        """
        for path, text in self.texts.items():
            if path not in self.deleted:
                _write(path, text)
        for old, new in self.renamed.items():
            old.rename(new)
        for path in sorted(self.deleted):
            path.unlink()


def _write(path: Path, text: str) -> None:
    """Replace a file's text, keeping a byte order mark it opens with."""
    with path.open("rb") as file:
        bom = file.read(len(codecs.BOM_UTF8)) == codecs.BOM_UTF8
    temporary = path.with_name(f".{path.name}.armarium")
    with temporary.open(
        "w", encoding="utf-8-sig" if bom else "utf-8", newline=""
    ) as file:
        file.write(text)
    os.replace(temporary, path)


class Relinker:
    """Rewrite the vault's links for files that move or go.

    A link to a file that moves is spelled for its new path, keeping its
    form: its folders, ``.md``, anchor and display alias. Where that spelling
    names several files, the link gets the shortest trailing path that names
    one. A link to a file that goes becomes its display text. Links to files
    that come to share a name with a moved file are lengthened in the same
    way, so that they keep naming one file.
    """

    def __init__(
        self,
        root: Path,
        moves: Mapping[Path, Path | None],
        *,
        keep_text: bool = False,
    ) -> None:
        """Index the files whose names the change touches.

        Args:
            root: Resolved vault directory.
            moves: Each file that moves to its new path, or to None when it
                goes and its links become text. A new path may be another
                existing file, into which the file is merged.
            keep_text: Write a body link that has no display alias of its own
                with the old name as its display alias, so prose keeps its
                wording.
        """
        self.root = root
        self.moves = dict(moves)
        self.keep_text = keep_text
        files = find_files(root)
        arrivals = [path for path in self.moves.values() if path is not None]
        arriving = set[str]().union(*(spellings(path) for path in arrivals))
        before = sharing(files, arriving.union(*(spellings(p) for p in self.moves)))
        after = [self.moves.get(path, path) for path in before]
        self.before = VaultIndex(root, before)
        self.after = VaultIndex(
            root,
            dict.fromkeys([p for p in after if p is not None] + arrivals),
        )
        self.targets = set(self.moves) | set(sharing(files, arriving))

    def destination(
        self, contents: str, source: Path
    ) -> tuple[Path, Path | None] | None:
        """Tell where a link's file goes, when the change touches it.

        Args:
            contents: What lies between the link's brackets.
            source: The record holding the link.

        Returns:
            tuple[Path, Path | None] | None: The file the link names now and
                its path after the change, None when it goes; or None when
                the link is malformed or names a file the change leaves be.
        """
        try:
            target, _ = split_wikilink(f"[[{contents}]]")
        except ValueError:
            return None
        found = self.before.resolve(target, source)[0] if target else None
        if found is None or found not in self.targets:
            return None
        return found, self.moves.get(found, found)

    def spell(self, target: str, old: Path, new: Path, source: Path) -> str:
        """Spell a link to a file's new path in the form of its old spelling.

        Args:
            target: The link's target as written.
            old: The file it names now.
            new: The file's path after the change.
            source: The record holding the link.

        Returns:
            str: The target unchanged when it still names the file alone; else
                its folders with the new name when that names the file alone;
                else the shortest trailing path of the new path that does.

        Raises:
            ValueError: Even the new path names other files too.
        """
        markdown = new.suffix.lower() == ".md"
        extension = ".md" if link_key(target).endswith(".md") else ""
        name = new.stem + extension if markdown else new.name
        relative = relative_posix(new, self.root)
        if markdown:
            relative = relative.removesuffix(new.suffix) + extension
        parts = relative.split("/")
        candidates = [target] if old == new else []
        candidates.append(target[: target.rfind("/") + 1] + name)
        candidates += ["/".join(parts[-depth:]) for depth in range(1, len(parts) + 1)]
        for candidate in candidates:
            if self.after.resolve(candidate, source)[0] == new:
                return candidate
        raise ValueError(f"no link can name {relative_posix(new, self.root)} alone")

    def replacement(
        self, contents: str, source: Path, *, body: bool, table: bool = False
    ) -> str | None:
        """Give the text that replaces one link, when the change touches it.

        Args:
            contents: What lies between the link's brackets.
            source: The record holding the link.
            body: Whether the link is in the body, where it may gain a display
                alias; frontmatter links stay canonical.
            table: Whether the link sits in a table row, where a display
                alias's bar is escaped.

        Returns:
            str | None: The rewritten link with its brackets; the link's
                display text when its file goes; or None to leave it.
        """
        found = self.destination(contents, source)
        if found is None:
            return None
        old, new = found
        if new is None:
            return wikilink_text(contents)
        match = CONTENTS.fullmatch(contents)
        assert match is not None
        lead, target, trail, rest = match[1], match[2], match[3], match[4] or ""
        spelled = self.spell(target, old, new, source)
        if spelled == target:
            return None
        if body and self.keep_text and old != new and "|" not in rest:
            rest += ("\\|" if table else "|") + _display(target)
        return f"[[{lead}{spelled}{trail}{rest}]]"

    def substitute(
        self, text: str, source: Path, *, body: bool, table: bool = False
    ) -> tuple[str, list[tuple[str, str]]]:
        """Rewrite every link in a text that the change touches.

        Args:
            text: Text holding links, such as one body line.
            source: The record holding it.
            body: As for replacement.
            table: As for replacement.

        Returns:
            tuple[str, list[tuple[str, str]]]: The new text, and each changed
                link as written before and after. An embed whose file goes
                loses its ``!`` with its brackets.
        """
        changed: list[tuple[str, str]] = []

        def replace(match: re.Match[str]) -> str:
            new = self.replacement(match[2], source, body=body, table=table)
            if new is None:
                return match[0]
            if new.startswith("[["):
                new = match[1] + new
            changed.append((match[0], new))
            return new

        return LINK.sub(replace, text), changed

    def relink(self, path: Path, text: str) -> tuple[str, list[Change]] | None:
        """Rewrite the links in one record that the change touches.

        Args:
            path: The record.
            text: Its contents.

        Returns:
            tuple[str, list[Change]] | None: Its new text and each change,
                frontmatter first, then body lines in order; or None when no
                link changes.

        Raises:
            UnicodeError, yaml.YAMLError, ValueError, RecursionError: The
                record cannot be parsed, or its frontmatter cannot be
                rewritten to hold the new links.
        """
        relative = relative_posix(path, self.root)
        frontmatter, length = Frontmatter.parse(text)
        lines = text.splitlines(keepends=True)
        changes: list[Change] = []
        data = dict(frontmatter)
        expected = self._value(data, "", path, relative, changes, listed=False)
        body: Body | None = None
        rows: set[int] = set()
        for number in range(length, len(lines)):
            line = lines[number]
            if "[[" not in line or not any(
                self.destination(m[2], path) for m in LINK.finditer(line)
            ):
                continue
            if body is None:
                body = Body("".join(lines[length:]), length + 1)
                rows = {b.line for b in body.iter_blocks() if b.kind == "row"}
            new, changed = self.substitute(
                line, path, body=True, table=number + 1 in rows
            )
            lines[number] = new
            where = " > ".join(body.headings_at(number + 1))
            changes += [
                Change(relative, where, number + 1, f"{old} → {to}")
                for old, to in changed
            ]
        # The body is rewritten first: a rewritten field may change how many
        # lines the frontmatter spans.
        if expected != data:
            lines[:length] = rewrite_frontmatter(
                lines[:length], expected, lambda line: self._raw(line, path)
            )
        return ("".join(lines), changes) if changes else None

    def _value(
        self,
        value: Any,
        location: str,
        source: Path,
        relative: str,
        changes: list[Change],
        *,
        listed: bool,
    ) -> Any:
        """Rewrite the links in one frontmatter value, as YAML reads it.

        Args:
            value: The value.
            location: Its field, dotted for a nested one, without list indices.
            source: The record holding it.
            relative: The record's vault-relative path, for the changes.
            changes: Changes made, extended in place.
            listed: Whether the value is a list item, which a link whose file
                goes removes; outside a list, such a link becomes null.

        Returns:
            Any: The new value, or _DROP for a list item to remove.
        """
        if isinstance(value, dict):
            return {
                key: self._value(
                    item,
                    f"{location}.{key}" if location else key,
                    source,
                    relative,
                    changes,
                    listed=False,
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            items = [
                self._value(item, location, source, relative, changes, listed=True)
                for item in value
            ]
            return [item for item in items if item is not _DROP]
        if not isinstance(value, str):
            return value
        whole = WIKILINK.fullmatch(value)
        if whole is not None:
            found = self.destination(whole[1], source)
            if found is not None and found[1] is None:
                changes.append(Change(relative, location, 0, f"{value} removed"))
                return _DROP if listed else None
        new, changed = self.substitute(value, source, body=False)
        changes += [
            Change(relative, location, 0, f"{old} → {to}") for old, to in changed
        ]
        return new

    def _raw(self, line: str, source: Path) -> str:
        """Rewrite the links in one line of frontmatter source, as written.

        A link inside a quoted YAML string gets the quoting that string
        needs; whether the line still reads as intended is checked after.
        """
        result: list[str] = []
        last = 0
        for match in LINK.finditer(line):
            new = self.replacement(match[2], source, body=False)
            if new is None or not new.startswith("[["):
                continue
            quote = _quote(line, match.start())
            if quote == '"':
                new = new.replace("\\", "\\\\").replace('"', '\\"')
            elif quote == "'":
                new = new.replace("'", "''")
            result += [line[last : match.start()], match[1], new]
            last = match.end()
        return "".join(result) + line[last:]

    def unchanged(self) -> list[str]:
        """Describe the links to touched files that the change leaves as written.

        Wikilinks outside records, in templates and the vault's optional root
        entries, ``.base`` and ``.canvas`` files, are not rewritten; nor are
        Markdown links to a moved or deleted file anywhere.

        Returns:
            list[str]: One line per link, giving its file, line and link.
        """
        records = {
            path
            for path in record_files(self.root, self.root)
            if not ("templates" in path.parts and is_template(path, self.root))
        }
        needles = {link_key(path.stem) for path in self.targets}
        names = {link_key(path.name) for path in self.moves}
        notes: list[str] = []
        for path in find_files(self.root):
            if not path.name.lower().endswith(LINKING_SUFFIXES):
                continue
            try:
                text = path.read_text(encoding="utf-8-sig")
            except OSError, UnicodeError:
                continue
            folded = link_key(text)
            if "](" not in text and not any(needle in folded for needle in needles):
                continue
            relative = relative_posix(path, self.root)
            for number, line in enumerate(text.splitlines(), 1):
                if path not in records:
                    notes += [
                        f"{relative}:{number}: {match[0]} not changed: not a record"
                        for match in LINK.finditer(line)
                        if self.destination(match[2], path) is not None
                    ]
                for match in MARKDOWN_LINK.finditer(line):
                    final = unquote(match[1]).partition("#")[0].rsplit("/", 1)[-1]
                    if link_key(final.strip()) in names:
                        notes.append(
                            f"{relative}:{number}: Markdown link ({match[1]}) not "
                            "changed: only wikilinks are rewritten"
                        )
        return notes

    def plan(self) -> Plan:
        """Work out every link change, writing nothing.

        Returns:
            Plan: The new texts of the records whose links change, with the
                changes and the links left unchanged.

        Raises:
            ValueError: A record that may link to a touched file cannot be
                parsed, or its frontmatter cannot be rewritten; each is named.
        """
        plan = Plan(self.root)
        problems: list[str] = []
        for path, data in mentioning(self.root, self.targets):
            relative = relative_posix(path, self.root)
            try:
                relinked = self.relink(path, data.decode("utf-8-sig"))
            except PARSE_ERRORS as exc:
                problems.append(f"{relative}: {exc}")
                continue
            if relinked is not None:
                plan.texts[path], changes = relinked
                plan.changes += changes
        if problems:
            raise ValueError(
                "cannot rewrite the links in these records; fix them and try "
                "again: " + "; ".join(problems)
            )
        plan.notes = self.unchanged()
        return plan


def _display(target: str) -> str:
    """Give the name a reader sees for a link target with no display alias."""
    name = target.rsplit("/", 1)[-1]
    return name[:-3] if link_key(name).endswith(".md") else name


def _quote(line: str, position: int) -> str:
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
    newline = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
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


def validate_changed(root: Path, paths: Iterable[Path]) -> Result:
    """Validate the records a change touched, sharing one index.

    Args:
        root: Resolved vault directory.
        paths: The records, as Plan.touched gives them.

    Returns:
        Result: Their findings and counts.
    """
    index = VaultIndex(root)
    return Result.combine(validate_markdown(path, root, index=index) for path in paths)
