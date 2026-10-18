"""List the links to a file or from a record, and where each one sits."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from armarium.index import (
    VaultIndex,
    link_key,
    mentioning,
    read_record,
    sharing,
    spellings,
)
from armarium.lib import find_files, locate
from armarium.parse import Body, Frontmatter


@dataclass(frozen=True)
class Reference:
    """One link between the traced file and another file.

    Attributes:
        relative: Vault-relative path of the other file, with forward
            slashes: the linking record for a link to the traced file, the
            linked file for a link from it.
        where: The frontmatter field holding the link, dotted for a nested
            field such as ``campaign_1.held_by``; or the headings the link
            sits beneath, outermost first and joined by `` > ``, which is
            empty for body text before the first heading. It is a place in
            the record that holds the link.
        line: One-based source line of a body link, or 0 for frontmatter.
    """

    relative: str
    where: str
    line: int

    @property
    def text(self) -> str:
        """Return the reference as one tab-separated line of output.

        Returns:
            str: Linking record, location and line number; the line number is
                empty for a frontmatter link.
        """
        return "\t".join((self.relative, self.where, str(self.line or "")))


def _final_segment(target: str) -> str:
    """Give the last path segment of a link target, as link_key returns it."""
    return link_key(target).rsplit("/", 1)[-1]


def _references(
    path: Path, data: bytes, index: VaultIndex, target: Path
) -> list[Reference]:
    """List one record's links to the traced file.

    The frontmatter is parsed and the body's lines are scanned for links; the
    body's structure is parsed only when a body link needs its headings.

    Args:
        path: The linking record, inside the index's vault.
        data: Its contents.
        index: Index holding at least every file that shares a spelling with
            the target.
        target: The traced file.

    Returns:
        list[Reference]: Each link that resolves to the target, in source
            order. Empty when the record cannot be decoded or parsed.
    """
    try:
        text = data.decode("utf-8-sig")
        frontmatter, length = Frontmatter.parse(text)
        body_text = "".join(text.splitlines(keepends=True)[length:])
        links = frontmatter.links + Body.scan_links(body_text, length + 1)
        names = spellings(target)
        relative = path.relative_to(index.root).as_posix()
        references: list[Reference] = []
        body: Body | None = None
        for link in links:
            if link.error or _final_segment(link.target) not in names:
                continue
            if index.resolve(link.target, path)[0] != target:
                continue
            if link.line:
                body = body or Body(body_text, length + 1)
                where = " > ".join(body.headings_at(link.line))
            else:
                where = link.field
            references.append(Reference(relative, where, link.line))
    except UnicodeError, yaml.YAMLError, ValueError, RecursionError:
        return []
    return references


def trace_record(path: Path, vault: Path | None = None) -> tuple[str, list[Reference]]:
    """List every link to one file from the vault's records.

    Links resolve as validation resolves them, so a link counts however it
    spells the target; embeds count as links. Only the files that share a
    name with the target are indexed, and only records whose text could hold
    a link to it are parsed.

    Args:
        path: The record or asset to trace. With a vault, a relative path is
            taken from the vault root; without one, from the working directory.
        vault: Vault root, or None to discover the vault from the file's
            location.

    Returns:
        tuple[str, list[Reference]]: The traced file's vault-relative path,
            with forward slashes, and its references in order of linking
            record, line and location. Links repeated at one
            location are listed once. The file's links to itself are left out,
            as are links from templates, hidden entries, the docs/ and
            scripts/ directories, AGENTS.md and files that cannot be read or
            parsed.

    Raises:
        ValueError: The path is not a file, lies in no vault or outside the
            given one, or is an entry that vault scans skip.
        OSError: A directory cannot be read.
    """
    root, located = locate(path, vault)
    candidates = sharing(find_files(root), spellings(located))
    # The scan's own path for the file, however the given path spelled it.
    target = next((file for file in candidates if file.samefile(located)), None)
    if target is None:
        raise ValueError(
            f"{located} is not part of the vault: hidden entries, symlinks and "
            "cache directories are skipped"
        )
    index = VaultIndex(root, candidates)
    references: set[Reference] = set()
    for record, data in mentioning(root, [target]):
        if record != target:
            references.update(_references(record, data, index, target))
    return target.relative_to(root).as_posix(), sorted(
        references, key=lambda r: (r.relative, r.line, r.where)
    )


def trace_outbound(
    path: Path, vault: Path | None = None
) -> tuple[str, list[Reference], list[str]]:
    """List every link from one record to the vault's other files.

    Links resolve as validation resolves them; embeds count as links. Only
    the files that a link's target could name are indexed.

    Args:
        path: The record to trace. With a vault, a relative path is taken
            from the vault root; without one, from the working directory.
        vault: Vault root, or None to discover the vault from the file's
            location.

    Returns:
        tuple[str, list[Reference], list[str]]: The traced record's
            vault-relative path, with forward slashes; the files it links to,
            in the order the links appear, a link repeated at one location
            listed once and the record's links to itself left out; and a
            message for each link that is malformed or names no file or
            several, which validation reports in full.

    Raises:
        ValueError: The path lies in no vault or outside the given one, is
            not one of its records or is a template, or cannot be parsed.
        OSError: A directory or the record cannot be read.
    """
    root, source, record = read_record(path, vault)
    relative = source.relative_to(root).as_posix()
    files = find_files(root)
    body = record.body
    links = record.frontmatter.links + body.links
    index = VaultIndex(
        root,
        sharing(files, {_final_segment(link.target) for link in links if link.target}),
    )
    references: dict[Reference, None] = {}
    unresolved: list[str] = []
    for link in sorted(links, key=lambda link: link.line):
        where = " > ".join(body.headings_at(link.line)) if link.line else link.field
        place = f"line {link.line}" if link.line else where
        if link.error:
            unresolved.append(f"{place}: {link.error}")
            continue
        if not link.target:
            continue
        resolved, rule = index.resolve(link.target, source)
        if resolved is None:
            problem = (
                "names several files" if rule == "link.ambiguous" else "names no file"
            )
            unresolved.append(f"{place}: [[{link.target}]] {problem}")
        elif resolved != source:
            reference = Reference(
                resolved.relative_to(root).as_posix(), where, link.line
            )
            references[reference] = None
    return relative, list(references), unresolved
