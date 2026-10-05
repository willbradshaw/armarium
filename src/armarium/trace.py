"""List the records that link to a file, and where each link sits."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from armarium.add import select_vault
from armarium.extensions import is_template
from armarium.index import VaultIndex, link_key
from armarium.lib import check_vault, find_files, find_vault, record_files
from armarium.parse import Body, Frontmatter


@dataclass(frozen=True)
class Reference:
    """One place where a record links to the traced record.

    Attributes:
        relative: Vault-relative path of the linking record, with forward
            slashes.
        where: The frontmatter field holding the link, dotted for a nested
            field such as ``campaign_1.held_by``; or the headings the link
            sits beneath, outermost first and joined by `` > ``, which is
            empty for body text before the first heading.
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


def _spellings(path: Path) -> set[str]:
    """List the final target segments with which a link can name a file.

    Args:
        path: A file in the vault.

    Returns:
        set[str]: Its filename as link_key returns it and, for Markdown, the
            filename without .md: the last path segments under which a
            VaultIndex files it.
    """
    spellings = {link_key(path.name)}
    if path.suffix.lower() == ".md":
        spellings.add(link_key(path.stem))
    return spellings


def _sharing(files: Iterable[Path], spellings: set[str]) -> list[Path]:
    """List the files that a link's final target segment can name.

    A link resolves among the files sharing its target's final segment, so
    indexing these files resolves such links exactly as the whole vault would.

    Args:
        files: Files in the vault.
        spellings: Final target segments, as _spellings returns them.

    Returns:
        list[Path]: The files with any of the spellings, in the given order.
    """
    return [path for path in files if not spellings.isdisjoint(_spellings(path))]


def _final_segment(target: str) -> str:
    """Give the last path segment of a link target, as link_key returns it."""
    return link_key(target).rsplit("/", 1)[-1]


def _locate(path: Path, vault: Path | None) -> tuple[Path, Path]:
    """Find the file to trace and the vault it belongs to.

    Args:
        path: File path. With a vault, a relative path is taken from the vault
            root; without one, from the working directory.
        vault: Vault root, or None to discover the vault from the file's
            location, as validating the file would.

    Returns:
        tuple[Path, Path]: The resolved vault root and the resolved file.

    Raises:
        ValueError: The path is a symlink, does not exist or is a directory;
            no vault encloses it; or it lies outside the given vault.
    """
    if vault is not None:
        path = select_vault(vault) / path
    if path.is_symlink():
        raise ValueError(f"{path} is a symlink")
    if not path.exists():
        raise ValueError(
            f"{path} does not exist; give a file path, which armarium find lists "
            "for a name"
        )
    if path.is_dir():
        raise ValueError(f"{path} is a directory, not a file")
    # Resolve the directory first, so that .. and symlinked directories do not
    # select a vault the file is not in.
    path = path.parent.resolve() / path.name
    return (find_vault(path) if vault is None else check_vault(path, vault)), path


@lru_cache(maxsize=8)
def _spelling(needle: str) -> tuple[re.Pattern[str], re.Pattern[bytes] | None]:
    """Build the patterns that find a filename where a link would end with it.

    A link's target ends with the linked file's name, optionally followed by
    ``.md``, and then the closing brackets, a display alias or an anchor.
    Starting with the literal name lets the search skip to its occurrences.

    Args:
        needle: The target's filename as link_key returns it, without .md.

    Returns:
        tuple[re.Pattern[str], re.Pattern[bytes] | None]: The pattern for
            text passed through link_key, and its counterpart for lowercased
            ASCII bytes, or None when the name is not ASCII.
    """
    source = re.escape(needle) + r"(?:\.md)?\s*(?:\]\]|\\?\||#)"
    return re.compile(source), (
        re.compile(source.encode()) if needle.isascii() else None
    )


def _frontmatter_text(data: bytes) -> str:
    """Give a file's frontmatter as YAML reads its text, for a cheap search.

    YAML may write a link other than as it reads it: a single-quoted string
    doubles an apostrophe, and a long string folds onto further lines.

    Args:
        data: Contents of a Markdown file.

    Returns:
        str: The source of the frontmatter as link_key returns it, with
            doubled apostrophes halved and each run of whitespace, line
            breaks included, made one space. Empty without frontmatter.

    Raises:
        UnicodeError: The frontmatter cannot be decoded.
    """
    text = data[: max(data.find(b"\n---", 3), 0)].decode("utf-8-sig")
    if not text.startswith("---"):
        return ""
    return " ".join(link_key(text).replace("''", "'").split())


def _mentions(data: bytes, needle: str) -> bool:
    """Tell cheaply whether a file's text could hold a link to a target.

    Every link to a file ends its target with the file's name, so a file
    whose text never spells the name that way cannot link to it and need not
    be parsed. The text is searched as written, then its frontmatter as YAML
    reads it.

    Args:
        data: Contents of a Markdown file.
        needle: The target's filename as link_key returns it, without .md.

    Returns:
        bool: Whether the text spells the name as a link target would,
            ignoring case and Unicode spelling, or its frontmatter holds a
            backslash, whose escapes only parsing can read. False for text
            that cannot be decoded.
    """
    text, ascii_bytes = _spelling(needle)
    try:
        if data.isascii():
            if ascii_bytes is not None and ascii_bytes.search(data.lower()):
                return True
        elif text.search(link_key(data.decode("utf-8-sig"))):
            return True
        frontmatter = _frontmatter_text(data)
    except UnicodeError:
        return False
    return "\\" in frontmatter or bool(text.search(frontmatter))


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
        spellings = _spellings(target)
        relative = path.relative_to(index.root).as_posix()
        references: list[Reference] = []
        body: Body | None = None
        for link in links:
            if link.error or _final_segment(link.target) not in spellings:
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
    root, located = _locate(path, vault)
    sharing = _sharing(find_files(root), _spellings(located))
    # The scan's own path for the file, however the given path spelled it.
    target = next((file for file in sharing if file.samefile(located)), None)
    if target is None:
        raise ValueError(
            f"{located} is not part of the vault: hidden entries, symlinks and "
            "cache directories are skipped"
        )
    index = VaultIndex(root, sharing)
    needle = link_key(target.stem if target.suffix.lower() == ".md" else target.name)
    references: set[Reference] = set()
    for record in record_files(root, root):
        # Validation scans templates too; they are not records that link.
        if record == target or (
            "templates" in record.parts and is_template(record, root)
        ):
            continue
        try:
            data = record.read_bytes()
        except OSError:
            continue
        if _mentions(data, needle):
            references.update(_references(record, data, index, target))
    return target.relative_to(root).as_posix(), sorted(
        references, key=lambda r: (r.relative, r.line, r.where)
    )
