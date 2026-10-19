"""Plan the link changes that renaming or removing a record needs."""

import re
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from armarium.changes import FileChange, FileChanges, report_changes
from armarium.edit import open_quote, requote, rewrite_frontmatter
from armarium.index import (
    VaultIndex,
    find_records,
    link_key,
    mentioning,
    sharing,
    spellings,
)
from armarium.lib import (
    CAMPAIGN_NAME,
    WIKILINK,
    find_files,
    line_ending,
    relative_posix,
    wikilink_text,
)
from armarium.logging import logger
from armarium.parse import PARSE_ERRORS, Block, Body, Frontmatter
from armarium.validate import is_campaign_file

# One link, embedded or not: the embed mark, then the link's contents.
LINK = re.compile(r"(!?)" + WIKILINK.pattern)

# A link's contents: space, the target, space, then its anchor or display alias.
CONTENTS = re.compile(r"(\s*)(.*?)(\s*)((?:\\?\||#).*)?", re.DOTALL)

# Files other than records in which Obsidian follows links.
LINKING_SUFFIXES = (".md", ".base", ".canvas")

# A Markdown link's destination, with or without angle brackets.
MARKDOWN_LINK = re.compile(r"\]\(<?([^()<>]+?)>?\)")

# A list item dropped from frontmatter.
_DROP = object()

# Types whose records have names the vault gives them, or that define the vault.
FIXED_TYPES = ("Clue", "Session", "Status", "Transcript", "Type")


class Refused(ValueError):
    """A relinking command refused, with lines that say what stands in its way.

    Attributes:
        details: Lines to print, one each, such as the links that remain.
    """

    def __init__(self, message: str, details: list[str]) -> None:
        """Hold the refusal and its details.

        Args:
            message: Why the command refused.
            details: Lines to print, one each.
        """
        super().__init__(message)
        self.details = details


@dataclass(frozen=True)
class RelinkChange:
    """One change to a file, as a line of a relinking command's output.

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
class RelinkPlan:
    """Every change one relinking command makes, worked out before any is made.

    Attributes:
        files: The files to write, move and delete.
        changes: What changes, in path and line order, for the output.
        notes: Links to the changed files that are left as they are, each
            with why, for the user to check.
    """

    files: FileChanges
    changes: list[RelinkChange] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def report(self, applied: list[FileChange], *, dry_run: bool) -> None:
        """Print the changes, warn of the links left as written, and log the files.

        Args:
            applied: Each file's change, as applying files returns them.
            dry_run: Whether the changes were only planned.
        """
        for change in self.changes:
            print(change.output)
        for note in self.notes:
            logger.warning(note)
        report_changes(applied, dry_run=dry_run)


def check_movable(
    relative: str, frontmatter: Frontmatter, refused: Collection[str] = FIXED_TYPES
) -> None:
    """Refuse a record that the relinking commands must leave in place.

    Args:
        relative: The record's vault-relative path, with forward slashes.
        frontmatter: Its frontmatter.
        refused: Types whose records the command leaves alone.

    Raises:
        ValueError: The record is of a refused type, or is a file every
            campaign requires.
    """
    if frontmatter.type in refused:
        raise ValueError(f"{relative} is a {frontmatter.type} record")
    if is_campaign_file(relative):
        raise ValueError(f"{relative} is a file every campaign requires")


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
        self.arrivals = set(arrivals)
        self._index: VaultIndex | None = None

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
        found = self.before.resolve_link(contents, source)
        if found is None or found not in self.targets:
            return None
        return found, self.moves.get(found, found)

    def landing(self, contents: str, source: Path) -> Path | None:
        """Tell which arriving file a link names after the change.

        Args:
            contents: What lies between the link's brackets, after the change.
            source: The record holding the link.

        Returns:
            Path | None: The file a moved file goes to, when the link names
                it; otherwise None.
        """
        found = self.after.resolve_link(contents, source)
        return found if found in self.arrivals else None

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

    def relink(self, path: Path, text: str) -> tuple[str, list[RelinkChange]] | None:
        """Rewrite the links in one record that the change touches.

        Args:
            path: The record.
            text: Its contents.

        Returns:
            tuple[str, list[RelinkChange]] | None: Its new text and each change,
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
        changes: list[RelinkChange] = []
        data = dict(frontmatter)
        expected = self._value(data, "", path, relative, changes, listed=False)
        fields = len(changes)
        body: Body | None = None
        rows: set[int] = set()
        items: dict[int, Block] = {}
        removed: list[int] = []
        for number in range(length, len(lines)):
            line = lines[number]
            if "[[" not in line or not any(
                self.destination(m[2], path) for m in LINK.finditer(line)
            ):
                continue
            if body is None:
                body = Body("".join(lines[length:]), length + 1)
                rows = {b.line for b in body.iter_blocks() if b.kind == "row"}
                items = {item.line: item for item in body.list_items("Appearances")}
            where = " > ".join(body.headings_at(number + 1))
            item = items.get(number + 1)
            entry = None if item is None else WIKILINK.match(item.text)
            if (
                entry is not None
                and (found := self.destination(entry[1], path)) is not None
                and found[1] is None
            ):
                lines[number] = ""
                removed.append(number)
                changes.append(
                    RelinkChange(relative, where, number + 1, f"{line.strip()} removed")
                )
                continue
            new, changed = self.substitute(
                line, path, body=True, table=number + 1 in rows
            )
            lines[number] = new
            changes += [
                RelinkChange(relative, where, number + 1, f"{old} → {to}")
                for old, to in changed
            ]
        if removed and frontmatter.type == "Content":
            for where, link in self._appearances(
                lines, removed, list(items.values()), expected, path
            ).items():
                # A field whose Session goes was nulled; say what it became.
                prior = next(
                    (i for i, c in enumerate(changes[:fields]) if c.where == where),
                    None,
                )
                text = f"{link[0] or 'null'} → {link[1] or 'null'}"
                if prior is None:
                    changes.insert(fields, RelinkChange(relative, where, 0, text))
                    fields += 1
                else:
                    old = changes[prior].text.removesuffix(" removed")
                    changes[prior] = RelinkChange(
                        relative, where, 0, f"{old} → {link[1] or 'null'}"
                    )
        # The body is rewritten first: a rewritten field may change how many
        # lines the frontmatter spans.
        if expected != data:
            lines[:length] = rewrite_frontmatter(
                lines[:length], expected, lambda line: self._raw(line, path)
            )
        return ("".join(lines), changes) if changes else None

    def _appearances(
        self,
        lines: list[str],
        removed: list[int],
        items: list[Block],
        expected: dict[str, Any],
        path: Path,
    ) -> dict[str, tuple[str | None, str | None]]:
        """Bring a Content record's history up to date after removing appearances.

        An Appearances list left empty gets its ``- N/A`` item, and each
        campaign block's ``first_session`` and ``last_session`` are set to the
        earliest and latest Sessions of that campaign that remain, or null.

        Args:
            lines: The record's lines, the removed items already emptied;
                changed in place.
            removed: Indices of the removed items' lines.
            items: The Appearances list's items, as parsed before removal.
            expected: The frontmatter the record will read as; changed in
                place.
            path: The record.

        Returns:
            dict[str, tuple[str | None, str | None]]: Each campaign block
                field set to another value, dotted, to its old and new
                values; the old value is the one read, before links to
                Sessions that go were nulled.
        """
        remaining = [
            match[1]
            for item in items
            if item.line - 1 not in removed
            and (match := WIKILINK.match(item.text)) is not None
        ]
        if not remaining:
            lines[removed[0]] = "- N/A" + line_ending(lines[removed[0] - 1])
        changed: dict[str, tuple[str | None, str | None]] = {}
        found = self.bounds(remaining, path)
        for campaign, block in expected.items():
            if not CAMPAIGN_NAME.fullmatch(campaign) or not isinstance(block, dict):
                continue
            for name, value in zip(
                ("first_session", "last_session"), found.get(campaign, (None, None))
            ):
                link = None if value is None else f"[[{value}]]"
                if name in block and block[name] != link:
                    changed[f"{campaign}.{name}"] = (block[name], link)
                    block[name] = link
        return changed

    def bounds(
        self, targets: Iterable[str], source: Path
    ) -> dict[str, tuple[str, str]]:
        """Find each campaign's earliest and latest Session among some links.

        Args:
            targets: Link contents, such as an Appearances list's links.
            source: The record holding them.

        Returns:
            dict[str, tuple[str, str]]: Each campaign directory name to the
                names of its earliest and latest Session, by session_number,
                among the links that name a Session that stays. Links to
                anything else are left out.
        """
        if self._index is None:
            self._index = VaultIndex(self.root)
        found: dict[str, list[tuple[int, str]]] = {}
        for contents in targets:
            session = self._index.resolve_link(contents, source)
            if session is None or self.moves.get(session, session) is None:
                continue
            order = self._index.session_order(session)
            if order is not None:
                found.setdefault(order[0], []).append((order[1], session.stem))
        return {
            campaign: (min(sessions)[1], max(sessions)[1])
            for campaign, sessions in found.items()
        }

    def _value(
        self,
        value: Any,
        location: str,
        source: Path,
        relative: str,
        changes: list[RelinkChange],
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
            kept: list[Any] = []
            named: dict[Path, str] = {}
            for item, before in zip(items, value):
                if item is _DROP:
                    continue
                # A merge can leave two items naming one file; keep the first.
                whole = WIKILINK.fullmatch(item) if isinstance(item, str) else None
                landed = None if whole is None else self.landing(whole[1], source)
                if landed is not None and landed in named:
                    changes.append(
                        RelinkChange(
                            relative,
                            location,
                            0,
                            f"{before} removed: repeats {named[landed]}",
                        )
                    )
                    continue
                if landed is not None:
                    named[landed] = item
                kept.append(item)
            return kept
        if not isinstance(value, str):
            return value
        whole = WIKILINK.fullmatch(value)
        if whole is not None:
            found = self.destination(whole[1], source)
            if found is not None and found[1] is None:
                changes.append(RelinkChange(relative, location, 0, f"{value} removed"))
                return _DROP if listed else None
        new, changed = self.substitute(value, source, body=False)
        changes += [
            RelinkChange(relative, location, 0, f"{old} → {to}") for old, to in changed
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
            new = requote(new, open_quote(line, match.start()))
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
        records = set(find_records(self.root))
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

    def plan(self) -> RelinkPlan:
        """Work out every link change, writing nothing.

        Returns:
            RelinkPlan: The new texts of the records whose links change, with the
                changes and the links left unchanged.

        Raises:
            ValueError: A record that may link to a touched file cannot be
                parsed, or its frontmatter cannot be rewritten; each is named.
        """
        plan = RelinkPlan(FileChanges(self.root))
        problems: list[str] = []
        for path, data in mentioning(self.root, self.targets):
            relative = relative_posix(path, self.root)
            try:
                relinked = self.relink(path, data.decode("utf-8-sig"))
            except PARSE_ERRORS as exc:
                problems.append(f"{relative}: {exc}")
                continue
            if relinked is not None:
                text, changes = relinked
                plan.files.write_text(path, text)
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
    name = wikilink_text(target)
    return name[:-3] if link_key(name).endswith(".md") else name
