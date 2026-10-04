"""List the records that link to a record, and where each link sits."""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from armarium.add import select_vault
from armarium.extensions import is_template
from armarium.find import find_records
from armarium.index import VaultIndex, link_key
from armarium.lib import record_files


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


def _target(index: VaultIndex, name: str) -> Path:
    """Find the one file a name refers to, as a link target or else as find does.

    Args:
        index: Index of the vault to search.
        name: Record name or trailing path, as written in a link, or an alias.

    Returns:
        Path: The file a link with this target resolves to. When no link
            would resolve, the single record armarium find lists for the
            name: one declaring it as an alias, or one whose filename differs
            from it only in whitespace.

    Raises:
        ValueError: The name is blank or names no file, or it names several,
            which the message lists.
        OSError: A directory cannot be read.
    """
    target = name.strip()
    if not target:
        raise ValueError("name must not be blank")
    path, rule = index.resolve(target, index.root)
    if path is not None:
        return path
    if rule == "link.ambiguous":
        candidates = [
            file.relative_to(index.root).as_posix()
            for file in sorted(index.targets[link_key(target.removeprefix("/"))])
        ]
        raise ValueError(
            f"several files are named {target}: {', '.join(candidates)}; "
            "use a vault-relative path"
        )
    matches = find_records(target, index.root)
    if not matches:
        raise ValueError(f"no record is named {target}")
    if len(matches) > 1:
        candidates = [match.relative for match in matches]
        raise ValueError(
            f"several records have the name or alias {target}: {', '.join(candidates)}"
        )
    return matches[0].path


@lru_cache(maxsize=8)
def _spelling(needle: str) -> tuple[re.Pattern[str], re.Pattern[bytes] | None]:
    """Build the patterns that find a filename where a link would end with it.

    A link's target ends with the linked file's name: after ``[[`` or a path
    separator, optionally followed by ``.md``, and before the closing
    brackets, a display alias or an anchor.

    Args:
        needle: The target's filename as link_key returns it, without .md.

    Returns:
        tuple[re.Pattern[str], re.Pattern[bytes] | None]: The pattern for
            text passed through link_key, and its counterpart for lowercased
            ASCII bytes, or None when the name is not ASCII.
    """
    source = r"(?:\[\[\s*|/)" + re.escape(needle) + r"(?:\.md)?\s*(?:\]\]|\\?\||#)"
    return re.compile(source), (
        re.compile(source.encode()) if needle.isascii() else None
    )


def _mentions(data: bytes, needle: str) -> bool:
    """Tell cheaply whether a file's text could hold a link to a target.

    Every link to a file ends its target with the file's name, so a file
    whose text never spells the name that way cannot link to it and need not
    be parsed.

    Args:
        data: Contents of a Markdown file.
        needle: The target's filename as link_key returns it, without .md.

    Returns:
        bool: Whether the text spells the name as a link target would,
            ignoring case and Unicode spelling. False for text that cannot be
            decoded.
    """
    text, ascii_bytes = _spelling(needle)
    if data.isascii():
        return ascii_bytes is not None and bool(ascii_bytes.search(data.lower()))
    try:
        return bool(text.search(link_key(data.decode("utf-8-sig"))))
    except UnicodeError:
        return False


def trace_record(name: str, vault: Path | None = None) -> tuple[Path, list[Reference]]:
    """List every link to one record from the vault's other records.

    Links resolve as validation resolves them, so a link counts however it
    spells the target; embeds count as links. Only records whose text could
    hold such a link are parsed.

    Args:
        name: Name, trailing path or alias of the record to trace.
        vault: Vault root, or None to discover it from the working directory.

    Returns:
        tuple[Path, list[Reference]]: The traced file and its references, in
            order of linking record, line and location. Links repeated at one
            location are listed once. The file's links to itself are left out,
            as are links from templates, hidden entries, the scripts/
            directory and files that cannot be read or parsed.

    Raises:
        ValueError: The vault cannot be identified, or the name is blank or
            names no file or several.
        OSError: A directory cannot be read.
    """
    root = select_vault(vault)
    index = VaultIndex(root)
    target = _target(index, name)
    needle = link_key(target.stem if target.suffix.lower() == ".md" else target.name)
    references: set[Reference] = set()
    for path in record_files(root, root):
        # Validation scans templates too; they are not records that link.
        if path == target or ("templates" in path.parts and is_template(path, root)):
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if not _mentions(data, needle):
            continue
        record, _ = index.parse(path)
        if record is None:
            continue
        relative = path.relative_to(root).as_posix()
        for link in record.links:
            if link.error or not link.target:
                continue
            if index.resolve(link.target, path)[0] != target:
                continue
            where = (
                " > ".join(record.body.headings_at(link.line))
                if link.line
                else link.field
            )
            references.add(Reference(relative, where, link.line))
    return target, sorted(references, key=lambda r: (r.relative, r.line, r.where))
