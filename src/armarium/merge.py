"""Merge one record into another and repoint every link to it."""

from pathlib import Path
from typing import Any

from armarium.edit import place_aliases, rewrite_frontmatter
from armarium.index import VaultIndex, name_key, read_aliases, read_record
from armarium.lib import (
    CAMPAIGN_NAME,
    WIKILINK,
    find_campaign,
    line_ending,
    relative_posix,
    split_wikilink,
)
from armarium.parse import PARSE_ERRORS, Body, Frontmatter, Record
from armarium.relink import (
    LINK,
    Refused,
    RelinkChange,
    Relinker,
    RelinkPlan,
    check_movable,
)

# Types whose records can be merged: things in the setting, and notes.
MERGEABLE = ("Content", "Note")

# Campaign block fields worked out from the merged Appearances.
HISTORY = ("first_session", "last_session")

# Types whose records merge refuses besides those relinking leaves alone.
UNMERGEABLE = ("Clue", "Player", "Reference", "Session", "Status", "Transcript", "Type")


class Conflicts(Refused):
    """The two records disagree where only the user can say which is right.

    Attributes:
        conflicts: One line per disagreement.
    """

    def __init__(self, conflicts: list[str]) -> None:
        """Describe the disagreements.

        Args:
            conflicts: One line per disagreement.
        """
        count = len(conflicts)
        super().__init__(
            f"{count} {'conflict' if count == 1 else 'conflicts'}; edit the "
            "records so that they agree, then merge again",
            conflicts,
        )


class Merger:
    """Combine two records' frontmatter and bodies, noting where they disagree."""

    def __init__(
        self, root: Path, source: Path, target: Path, relinker: Relinker
    ) -> None:
        """Prepare to merge.

        Args:
            root: Resolved vault directory.
            source: The record merged in, which goes.
            target: The record it is merged into, which stays.
            relinker: The relinker repointing links from source to target.
        """
        self.root = root
        self.source = source
        self.target = target
        self.relinker = relinker
        self.index = VaultIndex(root)
        self.conflicts: list[str] = []
        self.names = (
            relative_posix(source, root),
            relative_posix(target, root),
        )

    def conflict(self, where: str, message: str) -> None:
        """Note one disagreement.

        Args:
            where: The field or section where the records disagree.
            message: What disagrees.
        """
        self.conflicts.append(f"{where}: {message}")

    def key(self, value: Any) -> Any:
        """Give a value in a form that compares equal for equal meanings.

        A link compares by the file it names, however it is spelled.

        Args:
            value: A frontmatter value.

        Returns:
            Any: The file a link names, or the value itself.
        """
        whole = WIKILINK.fullmatch(value) if isinstance(value, str) else None
        found = (
            None if whole is None else self.index.resolve_link(whole[1], self.target)
        )
        return value if found is None else found

    def value(self, where: str, kept: Any, merged: Any) -> Any:
        """Combine one field's value in the target with its value in the source.

        Args:
            where: The field, dotted for a nested one.
            kept: The target's value.
            merged: The source's value.

        Returns:
            Any: The combined value. Lists are united, target's items first;
                mappings are combined field by field; an empty value gives way
                to the other; other values that differ are a conflict, and the
                target's is kept.
        """
        if merged in (None, "", [], {}):
            return kept
        if kept in (None, "", [], {}):
            return merged
        if isinstance(kept, list) and isinstance(merged, list):
            united = list(kept)
            keys = [self.key(item) for item in kept]
            for item in merged:
                if self.key(item) not in keys:
                    united.append(item)
                    keys.append(self.key(item))
            return united
        if isinstance(kept, dict) and isinstance(merged, dict):
            return self.mapping(where, kept, merged)
        if self.key(kept) != self.key(merged):
            self.conflict(
                where,
                f"{_show(kept)} in {self.names[1]}, {_show(merged)} in {self.names[0]}",
            )
        return kept

    def mapping(
        self, where: str, kept: dict[str, Any], merged: dict[str, Any]
    ) -> dict[str, Any]:
        """Combine two mappings field by field, in the target's order.

        A field only the source has follows the nearest field before it in
        the source that the combined mapping has, or comes first.

        Args:
            where: The mapping's field, dotted, or empty for the frontmatter.
            kept: The target's mapping.
            merged: The source's mapping.

        Returns:
            dict[str, Any]: The combined mapping.
        """
        items = list(kept.items())
        for key, value in merged.items():
            location = f"{where}.{key}" if where else key
            if key in kept:
                position = next(i for i, (k, _) in enumerate(items) if k == key)
                if not (CAMPAIGN_NAME.fullmatch(where) and key in HISTORY):
                    items[position] = (key, self.value(location, kept[key], value))
                continue
            present = [k for k, _ in items]
            before = list(merged)[: list(merged).index(key)]
            after = next((k for k in reversed(before) if k in present), None)
            items.insert(0 if after is None else present.index(after) + 1, (key, value))
        return dict(items)

    def frontmatter(self, kept: Frontmatter, merged: Frontmatter) -> dict[str, Any]:
        """Combine the two records' frontmatter.

        Args:
            kept: The target's frontmatter, its links repointed.
            merged: The source's frontmatter, its links repointed.

        Returns:
            dict[str, Any]: The merged frontmatter. Its aliases gain the
                source's aliases and filename; the type and subtype are the
                records' own.
        """
        data = self.mapping(
            "",
            dict(kept),
            {
                k: v
                for k, v in merged.items()
                if k not in ("type", "subtype", "aliases")
            },
        )
        names = {name_key(self.target.stem)}
        aliases: list[str] = []
        for alias in [
            *read_aliases(kept),
            *read_aliases(merged),
            self.source.stem,
        ]:
            if name_key(alias) not in names:
                names.add(name_key(alias))
                aliases.append(alias)
        if aliases != read_aliases(kept):
            data = place_aliases(data, aliases)
            for alias in aliases:
                others = self.index.sharing_name(self.target, alias)
                taken = [
                    path
                    for path in dict.fromkeys(
                        relative_posix(o.path, self.root) for o in others
                    )
                    if path != self.names[0]
                ]
                if taken:
                    self.conflict(
                        "aliases", f"{alias} is already a name of {', '.join(taken)}"
                    )
        for link in Frontmatter(data).links:
            if link.error or not link.target:
                continue
            if self.relinker.after.resolve(link.target, self.target)[0] == self.target:
                self.conflict(
                    link.field, f"[[{link.target}]] would link the record to itself"
                )
        return data

    def body(self, kept: str, merged: str, kind: str | None) -> str:
        """Combine the two records' bodies.

        A Note's body is the target's followed by the source's. A Content
        record's text before its first section must agree; its Notes are the
        target's followed by the source's; its Appearances are both lists in
        session order; its Active Clues are the target's.

        Args:
            kept: The target's body, its links repointed.
            merged: The source's body, its links repointed.
            kind: The records' type.

        Returns:
            str: The merged body.
        """
        for block in sorted(_block_ids(kept) & _block_ids(merged)):
            self.conflict("body", f"both records have the block ^{block}")
        if kind != "Content":
            return _join(kept, merged)
        kept_start, kept_sections = Body(kept).divide()
        merged_start, merged_sections = Body(merged).divide()
        start = kept_start
        if _empty(kept_start):
            start = merged_start
        elif not _empty(merged_start) and kept_start.strip() != merged_start.strip():
            self.conflict(
                "body", "the text before Notes differs, such as a callout or image"
            )
        others = dict(merged_sections)
        titles = [title for title, _ in kept_sections]
        # Sections only the source has follow Notes, or end the body.
        extras = [section for name, section in merged_sections if name not in titles]
        parts = [start]
        for title, text in kept_sections:
            other = others.get(title, "")
            if title == "Notes":
                parts.append(_heading(text) + _join(_content(text), _content(other)))
                parts += extras
                extras = []
            elif title == "Appearances":
                parts.append(self.appearances(text, other))
            elif title == "Active Clues" or _empty(_content(other)):
                parts.append(text)
            elif _empty(_content(text)):
                parts.append(other)
            else:
                if _content(text).strip() != _content(other).strip():
                    self.conflict(title, "the section differs between the records")
                parts.append(text)
        return "".join(parts + extras)

    def appearances(self, kept: str, merged: str) -> str:
        """Combine two Appearances sections in campaign and session order.

        Args:
            kept: The target's section, heading included.
            merged: The source's section, heading included, or empty.

        Returns:
            str: The merged section; an item each Session, ``- N/A`` for none.
        """
        found: dict[Path, tuple[tuple[int, int], str]] = {}
        newline = line_ending(kept)
        for text in (kept, merged):
            listed = {item.line: item for item in Body(text).list_items("Appearances")}
            for number, line in enumerate(text.splitlines()[1:], 2):
                if not line.strip() or line.strip() == "- N/A":
                    continue
                item = listed.get(number)
                entry = None if item is None else WIKILINK.match(item.text)
                session = None if entry is None else self.session(entry[1])
                if session is None:
                    self.conflict("Appearances", f"cannot read the item {line.strip()}")
                    continue
                path, order = session
                if path in found and found[path][1].strip() != line.strip():
                    self.conflict(
                        "Appearances",
                        f"both records have an item for {path.stem}; keep one",
                    )
                    continue
                found.setdefault(path, (order, line.rstrip("\r\n") + newline))
        items = [line for _, line in sorted(found.values())]
        trail = newline if kept.endswith(newline * 2) else ""
        return (
            _heading(kept)
            + newline
            + ("".join(items) if items else f"- N/A{newline}")
            + trail
        )

    def session(self, contents: str) -> tuple[Path, tuple[int, int]] | None:
        """Find the Session an Appearances link names, and where it falls.

        Args:
            contents: What lies between the link's brackets.

        Returns:
            tuple[Path, tuple[int, int]] | None: The Session's path, with its
                campaign number and session number to order it by; or None
                when the link names no Session with both.
        """
        path = self.index.resolve_link(contents, self.target)
        order = None if path is None else self.index.session_order(path)
        if path is None or order is None:
            return None
        return path, (int(order[0].removeprefix("campaign_")), order[1])


def _show(value: Any) -> str:
    """Write a frontmatter value briefly, for a conflict."""
    text = value if isinstance(value, str) else repr(value)
    return text if len(text) <= 60 else text[:57] + "..."


def _block_ids(text: str) -> set[str]:
    """List the block ids that end a body's paragraphs and items, ignoring case."""
    return {
        block.block_id.casefold()
        for block in Body(text).iter_blocks()
        if block.block_id is not None
    }


def _heading(section: str) -> str:
    """Give a section's heading line."""
    return section.splitlines(keepends=True)[0]


def _content(section: str) -> str:
    """Give a section's text below its heading."""
    return "".join(section.splitlines(keepends=True)[1:])


def _empty(text: str) -> bool:
    """Tell whether text holds nothing, or only the ``- N/A`` placeholder."""
    return text.strip() in ("", "- N/A")


def _join(kept: str, merged: str) -> str:
    """Put one text after another, a blank line between, keeping line ends.

    Args:
        kept: The first text.
        merged: The text after it.

    Returns:
        str: Both texts; either alone when the other is empty.
    """
    if _empty(merged):
        return kept
    newline = line_ending(kept + merged)
    if _empty(kept):
        return newline + merged.strip("\r\n") + newline + newline
    trail = kept[len(kept.rstrip("\r\n")) :]
    return (
        kept.rstrip("\r\n")
        + newline * 2
        + merged.strip("\r\n")
        + (trail if trail else newline)
    )


def merge(source: Path, target: Path, vault: Path | None = None) -> RelinkPlan:
    """Plan merging one record into another and repointing every link to it.

    Args:
        source: The record merged in, which goes. With a vault, a relative
            path is taken from the vault root; without one, from the working
            directory.
        target: The record it is merged into, which stays; as for source.
        vault: Vault root, or None to discover the vault from the records'
            location.

    Returns:
        RelinkPlan: The merged record, the deletion and the link changes, not yet
            made.

    Raises:
        Conflicts: The records disagree where only the user can say which
            is right.
        ValueError: The records cannot be merged, or a record that may link
            to the source cannot be rewritten.
        OSError: A file or directory cannot be read.
    """
    root, merged_path, merged_record = read_record(source, vault)
    target_root, kept_path, kept_record = read_record(target, vault or root)
    if target_root != root:
        raise ValueError("the two records must be in one vault")
    if kept_path == merged_path:
        raise ValueError("a record cannot be merged into itself")
    names = tuple(relative_posix(path, root) for path in (merged_path, kept_path))
    merged_front, kept_front = merged_record.frontmatter, kept_record.frontmatter
    for relative, frontmatter in zip(names, (merged_front, kept_front)):
        check_movable(relative, frontmatter, UNMERGEABLE)
    kind = kept_front.type
    if kind not in MERGEABLE or merged_front.type != kind:
        raise ValueError(
            f"only two Content records or two Notes can be merged, not "
            f"{merged_front.type} into {kind}"
        )
    if merged_front.get("subtype") != kept_front.get("subtype"):
        raise ValueError(
            f"{names[0]} is a {merged_front.get('subtype')} and {names[1]} a "
            f"{kept_front.get('subtype')}; give them one subtype first"
        )
    scope = find_campaign(kept_path, root)
    if scope is not None and scope != find_campaign(merged_path, root):
        raise ValueError(
            f"{names[1]} belongs to {scope}, so records that link to {names[0]} "
            "could not link to it; merge into a shared record"
        )
    relinker = Relinker(root, {merged_path: kept_path}, keep_text=True)
    plan = relinker.plan()
    merger = Merger(root, merged_path, kept_path, relinker)
    texts = [plan.files.read_text(path) for path in (kept_path, merged_path)]
    try:
        (kept, kept_length), (merged, merged_length) = (
            Frontmatter.parse(text) for text in texts
        )
    except PARSE_ERRORS as exc:
        raise ValueError(f"cannot parse the records: {exc}") from exc
    kept_lines, merged_lines = (text.splitlines(keepends=True) for text in texts)
    data = merger.frontmatter(kept, merged)
    merged_body = "".join(merged_lines[merged_length:])
    body = merger.body("".join(kept_lines[kept_length:]), merged_body, kind)
    if kind == "Content":
        bounds = relinker.bounds(
            [
                match[1]
                for item in Body(body).list_items("Appearances")
                if (match := WIKILINK.match(item.text)) is not None
            ],
            kept_path,
        )
        for campaign, block in data.items():
            if CAMPAIGN_NAME.fullmatch(campaign) and isinstance(block, dict):
                first, last = bounds.get(campaign, (None, None))
                block["first_session"] = None if first is None else f"[[{first}]]"
                block["last_session"] = None if last is None else f"[[{last}]]"
        for campaign in bounds.keys() - data.keys():
            merger.conflict(campaign, "neither record has this campaign's block")
    try:
        lines = rewrite_frontmatter(kept_lines[:kept_length], data)
    except ValueError as exc:
        raise ValueError(f"cannot write {names[1]}: {exc}") from exc
    plan.files.write_text(kept_path, "".join(lines) + body)
    plan.files.writes.pop(merged_path, None)
    record = Record(kept_path, Frontmatter(data), Body(body, len(lines) + 1))
    for path in plan.files.writes:
        text = plan.files.read_text(path)
        for number, line in enumerate(text.splitlines(), 1):
            for match in LINK.finditer(line):
                try:
                    target_text, anchor = split_wikilink(f"[[{match[2]}]]")
                except ValueError:
                    continue
                if not anchor or not target_text:
                    continue
                if relinker.after.resolve(target_text, path)[0] != kept_path:
                    continue
                if record.body.missing_anchor(anchor) is not None:
                    relative = relative_posix(path, root)
                    merger.conflict(
                        f"{relative}:{number}",
                        f"{match[0]} names no heading or block of the merged record",
                    )
    if merger.conflicts:
        raise Conflicts(merger.conflicts)
    plan.files.deletes.add(merged_path)
    plan.changes = [
        RelinkChange(names[0], "", 0, f"merged into {names[1]}"),
        *(
            RelinkChange(names[1], key, 0, f"merged from {names[0]}")
            for key in data
            if data[key] != kept.get(key)
        ),
        *(change for change in plan.changes if change.relative != names[0]),
    ]
    if kind == "Content":
        merged_body = _content(dict(Body(merged_body).divide()[1]).get("Notes", ""))
    if not _empty(merged_body):
        plan.notes.append(f"{names[1]}: review the text merged from {names[0]}")
    return plan
