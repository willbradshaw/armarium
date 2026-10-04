"""Find a vault's records by name or alias without validating them."""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from armarium.add import select_vault
from armarium.extensions import is_template
from armarium.index import link_key
from armarium.lib import record_files
from armarium.parse import Frontmatter

# From the start of a line, an aliases field that may hold a value: text
# after the colon, or a block list on the lines below.
ALIASES = re.compile(rb"[\"']?aliases[\"']?[ \t]*:[ \t]*(?:\S|(?:\s|#[^\n]*)*-\s)")

# Match kinds in the order they are listed.
KINDS = ("name", "alias")


@dataclass(frozen=True)
class Match:
    """One record whose name or alias matches a query.

    Attributes:
        path: Absolute path of the record.
        relative: Its vault-relative path, with forward slashes.
        kind: The record's type, followed by ``/`` and its subtype when it has
            one, such as ``Content/NPC``. Empty for an untyped record.
        match: ``name`` when the filename is the query, ``alias`` when one
            of the record's aliases is.
        summary: The record's summary on one line, or empty.
    """

    path: Path
    relative: str
    kind: str
    match: str
    summary: str

    @property
    def line(self) -> str:
        """Return the match as one tab-separated line of output.

        Returns:
            str: Vault-relative path, type, match kind and summary.
        """
        return "\t".join((self.relative, self.kind, self.match, self.summary))


def _name_key(name: str) -> str:
    """Normalise a query, filename or alias so that equal names compare equal.

    Args:
        name: Name as written.

    Returns:
        str: The name as link_key returns it, with surrounding whitespace
            removed and inner runs of whitespace collapsed. Empty for a blank
            name.
    """
    return link_key(" ".join(name.split()))


def _may_declare_aliases(data: bytes) -> bool:
    """Tell cheaply whether a record's aliases field could hold a value.

    Empty fields are told apart without parsing YAML, so most records are
    never parsed. Only lines containing the field's name are examined.

    Args:
        data: Contents of a Markdown file.

    Returns:
        bool: Whether some line opens with an aliases field followed by a
            value or a block list. A record whose field is absent or empty
            gives False; text that merely resembles a filled field gives
            True, and parsing then decides.
    """
    found = data.find(b"aliases")
    while found >= 0:
        if ALIASES.match(data, data.rfind(b"\n", 0, found) + 1):
            return True
        found = data.find(b"aliases", found + 1)
    return False


def _read_frontmatter(data: bytes) -> Frontmatter | None:
    """Parse the frontmatter of a record's bytes, leaving its body unread.

    Args:
        data: Contents of a Markdown file.

    Returns:
        Frontmatter | None: The parsed metadata, empty when the record has
            none, or None when the file cannot be decoded or parsed.
    """
    try:
        return Frontmatter.parse(data.decode("utf-8-sig"))[0]
    except UnicodeError, yaml.YAMLError, ValueError, RecursionError:
        return None


def _aliases(frontmatter: Frontmatter) -> list[str]:
    """List the alternate names a record declares.

    Args:
        frontmatter: Parsed metadata of the record.

    Returns:
        list[str]: The strings in its ``aliases`` list; a single string counts
            as one alias, and any other value as none.
    """
    value = frontmatter.get("aliases")
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [alias for alias in value if isinstance(alias, str)]
    return []


def find_records(name: str, vault: Path | None = None) -> list[Match]:
    """List the records whose filename or one of whose aliases is a name.

    Names compare as link targets do: ignoring case and Unicode spelling.
    Every record is read, but only those whose filename matches or whose
    aliases field may hold a value are parsed, and then only their
    frontmatter.

    Args:
        name: Name to look for, without a path or .md.
        vault: Vault root, or None to discover it from the working directory.

    Returns:
        list[Match]: Records with that name, then records with that alias,
            each group in path order. Templates, hidden entries and the
            scripts/ directory are not searched; files that cannot be read or
            parsed are left out.

    Raises:
        ValueError: The name is blank or the vault cannot be identified.
        OSError: A directory cannot be read.
    """
    query = _name_key(name)
    if not query:
        raise ValueError("name must not be blank")
    root = select_vault(vault)
    matches: list[Match] = []
    for path in record_files(root, root):
        # Validation scans templates too; they are not records to find.
        if "templates" in path.parts and is_template(path, root):
            continue
        named = _name_key(path.stem) == query
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if not named and not _may_declare_aliases(data):
            continue
        frontmatter = _read_frontmatter(data)
        if frontmatter is None:
            continue
        if named:
            match = "name"
        elif query in {_name_key(alias) for alias in _aliases(frontmatter)}:
            match = "alias"
        else:
            continue
        label = frontmatter.type or ""
        subtype = frontmatter.get("subtype")
        if label and isinstance(subtype, str):
            label += f"/{subtype}"
        summary = frontmatter.get("summary")
        matches.append(
            Match(
                path,
                path.relative_to(root).as_posix(),
                label,
                match,
                " ".join(summary.split()) if isinstance(summary, str) else "",
            )
        )
    return sorted(matches, key=lambda m: (KINDS.index(m.match), m.relative))
