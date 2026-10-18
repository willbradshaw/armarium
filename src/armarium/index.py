"""Index vault files and lazily parse referenced Markdown records."""

import re
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from jsonschema.exceptions import SchemaError

from armarium.extensions import ExtensionSet, is_template, load_extension_set
from armarium.lib import (
    Diagnostic,
    find_campaign,
    find_files,
    is_inside,
    locate,
    parse_directories,
    parse_subtype_directories,
    record_files,
    relative_parts,
    relative_posix,
)
from armarium.parse import Frontmatter, Record
from armarium.schemas import Schema

# Types whose records are structure, not things looked up by name: indexes,
# overviews and the type system itself. Their names may repeat.
STRUCTURAL_TYPES = frozenset({"Reference", "Status", "Type"})

# Failures loading a schema or the extension set, kept to raise again for each record.
LOAD_ERRORS = (OSError, ValueError, SchemaError, RecursionError)


class VaultIndex:
    """Hold one validation run's file targets and parsed records for a vault."""

    def __init__(self, root: Path, files: Iterable[Path] | None = None) -> None:
        """Map possible link targets to files without reading their contents.

        Each file contributes its vault-relative path and every trailing path.
        For example, reference/types/Content.md contributes that full path,
        types/Content.md and Content.md, plus all three without .md. These keys
        support links such as [[types/Content]] and [[Content]]. Assets keep
        their extensions. Each key maps to a set because multiple files can
        share a name; resolve() reports such matches as ambiguous. Keys are
        casefolded, as Obsidian resolves links case-insensitively, so files
        whose paths differ only by case collide in the same way.

        Parsed records are stored separately in self.records, initially empty.
        parse() fills that cache only when a record's contents are needed.
        Schemas and the extension set are likewise loaded once, on first use.

        Args:
            root: Vault directory; hidden files and symlinks are excluded.
            files: Files below the resolved root to index in place of every
                visible file. A target then resolves as in the whole vault
                only if every file that could match it is among them.
        """
        self.root = root.resolve()
        self.targets: dict[str, set[Path]] = {}
        self.records: dict[Path, tuple[Record | None, list[Diagnostic]]] = {}
        self._extensions: ExtensionSet | Exception | None = None
        self._schemas: dict[Path, Schema | Exception] = {}
        self._declarations: dict[str, dict[str, str]] | None = None
        self._names: dict[str, list[Name]] | None = None
        self._subtype_directories: dict[str, dict[str, str]] = {}
        for path in find_files(self.root) if files is None else files:
            relative = "/".join(relative_parts(path, self.root))
            # Markdown links may include or omit .md; asset extensions matter.
            names = [relative]
            if path.suffix.lower() == ".md":
                names.append(relative[:-3])
            for name in names:
                # link_key never joins or splits across a slash, so the key of
                # a trailing path is the same trailing path of the full key.
                parts = link_key(name).split("/")
                # Index each trailing path, from the full path to the filename.
                for offset in range(len(parts)):
                    key = "/".join(parts[offset:])
                    self.targets.setdefault(key, set()).add(path)

    def extension_set(self) -> ExtensionSet:
        """Load the vault's enabled extensions once for this validation run.

        Returns:
            ExtensionSet: The rules and permitted Content subtypes.

        Raises:
            OSError, ValueError, SchemaError, RecursionError: The extension set
                is invalid. The same error is raised again on every later call,
                so each record reports it as it would without the cache.
        """
        if self._extensions is None:
            try:
                self._extensions = load_extension_set(self.root)
            except LOAD_ERRORS as exc:
                self._extensions = exc
        if isinstance(self._extensions, Exception):
            raise self._extensions
        return self._extensions

    def load_schema(self, path: Path, root: Path) -> Schema:
        """Load one schema once for this validation run; see Schema.load.

        Args:
            path: Schema file path.
            root: Vault path, as Schema.load takes it.

        Returns:
            Schema: The loaded schema, shared by every later call for this path.

        Raises:
            OSError, ValueError, SchemaError, RecursionError: The schema is
                invalid; the same error is raised again on every later call.
        """
        key = path.absolute()
        if key not in self._schemas:
            try:
                self._schemas[key] = Schema.load(path, root)
            except LOAD_ERRORS as exc:
                self._schemas[key] = exc
        cached = self._schemas[key]
        if isinstance(cached, Exception):
            raise cached
        return cached

    def resolve(self, target: str, source: Path) -> tuple[Path | None, str | None]:
        """Find the single file named by a wikilink's target text.

        For example, target="types/Content" can return the full filesystem path
        /vault/reference/types/Content.md. Here "resolve" means looking up which
        file the link names; this method does not read the file or check whether
        a linked heading or block exists.

        Args:
            target: Target text returned by parse_wikilink, without brackets,
                display alias or heading/block suffix. For [[#Heading]], this
                is an empty string because the link points within its own record.
            source: Full filesystem path of the record containing the link, such
                as /vault/content/Harbour.md, rather than content/Harbour.md.
                An empty target returns this path. Other targets are looked up
                across the vault, not relative to the source record's directory.

        Returns:
            tuple[Path | None, str | None]: (file_path, None) for exactly one
                matching file, (None, "link.missing") for no matches, or
                (None, "link.ambiguous") for multiple matches. Matching is
                case-insensitive, as in Obsidian, and equivalent Unicode
                spellings match. Display aliases and YAML aliases are not
                lookup keys.

        Raises:
            ValueError: source is not a full path inside this vault.
        """
        if not is_inside(source, self.root):
            raise ValueError("source must be inside the indexed vault")
        if not target:
            return source, None
        candidates = self.targets.get(link_key(target.removeprefix("/")), set())
        if len(candidates) == 1:
            return next(iter(candidates)), None
        return None, "link.ambiguous" if candidates else "link.missing"

    def resolve_field(
        self, record: Record, field: str
    ) -> tuple[Path | None, str | None]:
        """Resolve the single wikilink held by one top-level frontmatter field.

        Args:
            record: Parsed record inside this vault.
            field: Top-level frontmatter field name, such as "type".

        Returns:
            tuple[Path | None, str | None]: (file_path, None) when the field
                holds exactly one well-formed link naming exactly one file.
                Otherwise (None, message) saying why not: the field holds no
                link or several, the link text is malformed, or the target is
                missing or ambiguous.
        """
        links = [link for link in record.links if link.location == field]
        if len(links) != 1:
            return None, f"{field} must hold exactly one wikilink"
        (link,) = links
        if link.error is not None:
            return None, link.error
        resolved, rule = self.resolve(link.target, record.path)
        if rule:
            return None, f"cannot uniquely resolve [[{link.target}]]"
        return resolved, None

    def parse(self, path: Path) -> tuple[Record | None, list[Diagnostic]]:
        """Parse a Markdown target once, retaining failures as well as records.

        Args:
            path: Absolute Markdown path inside the indexed vault.

        Returns:
            tuple[Record | None, list[Diagnostic]]: Cached Record.parse result.

        Raises:
            ValueError: The path is outside this vault or is not Markdown.
        """
        if not is_inside(path, self.root) or path.suffix.lower() != ".md":
            raise ValueError("target must be Markdown inside the indexed vault")
        if path not in self.records:
            self.records[path] = Record.parse(path, self.root)
        return self.records[path]

    def names(self) -> dict[str, list["Name"]]:
        """Read the names the vault's records go by, once for this run.

        Returns:
            dict[str, list[Name]]: The mapping read_names returns for this
                vault. Every call returns the same mapping, which callers
                must not modify.

        Raises:
            OSError: A directory cannot be read.
        """
        if self._names is None:
            self._names = read_names(self.root)
        return self._names

    def sharing_name(self, path: Path, name: str) -> list["Name"]:
        """List the other records that go by a name where a record is visible.

        A record is visible among the shared records and those of its own
        campaign, or of every campaign for a shared record. Records of two
        different campaigns may share a name.

        Args:
            path: The record.
            name: A name, as a filename or an alias writes it.

        Returns:
            list[Name]: Each filename or alias of another record that equals
                the name, unless that record belongs to a different campaign
                or is a structural record. A record that cannot be parsed
                counts, since its type is unknown.
        """
        scope = find_campaign(path, self.root)
        found: list[Name] = []
        for other in self.names().get(name_key(name), []):
            if other.path == path:
                continue
            visible = find_campaign(other.path, self.root)
            if scope is not None and visible is not None and scope != visible:
                continue
            parsed, _ = self.parse(other.path)
            if parsed is not None and parsed.frontmatter.type in STRUCTURAL_TYPES:
                continue
            found.append(other)
        return found

    def declared_directories(self) -> dict[str, dict[str, str]]:
        """Read where each Type record declares that its records live.

        Returns:
            dict[str, dict[str, str]]: Type name (the record's filename stem)
                to its declared directory per scope, for every reference/types
                record with a usable declaration; the others are left out.
                Read once per validation run; every call returns the same
                mapping, which callers must not modify.
        """
        if self._declarations is None:
            self._declarations = self._read_declarations()
        return self._declarations

    def _read_declarations(self) -> dict[str, dict[str, str]]:
        """List and parse the Type records for declared_directories."""
        types = self.root / "reference/types"
        if types.is_symlink() or not types.is_dir():
            return {}
        declarations: dict[str, dict[str, str]] = {}
        for path in find_files(types):
            if path.suffix.lower() != ".md":
                continue
            record, _ = self.parse(path)
            if record is None:
                continue
            try:
                value = record.frontmatter.get("directories")
                declarations[path.stem] = parse_directories(value)
            except ValueError:
                continue
        return declarations

    def subtype_directories(self, kind: str) -> dict[str, str]:
        """Read the subfolder a Type record declares for each subtype.

        Args:
            kind: The type, such as Content.

        Returns:
            dict[str, str]: Subtype to its declared subfolder below each of
                the type's directories. Empty when its Type record declares
                none, cannot be read, or holds an unusable declaration, which
                validate_vault reports. Read once per type per validation run;
                callers must not modify the mapping.
        """
        if kind not in self._subtype_directories:
            self._subtype_directories[kind] = self._read_subtype_directories(kind)
        return self._subtype_directories[kind]

    def _read_subtype_directories(self, kind: str) -> dict[str, str]:
        """Parse a type's Type record for subtype_directories."""
        path = self.root / "reference/types" / f"{kind}.md"
        if path.is_symlink() or not path.is_file():
            return {}
        record, _ = self.parse(path)
        if record is None:
            return {}
        try:
            return parse_subtype_directories(
                record.frontmatter.get("subtype_directories"),
                kind,
                self.extension_set().subtypes_of(kind),
            )
        except LOAD_ERRORS:
            return {}

    def containing_directories(self, path: Path) -> list[tuple[str, str, set[str]]]:
        """Find the declared directories a path lies under, shallowest first.

        Args:
            path: Absolute path inside the indexed vault.

        Returns:
            list[tuple[str, str, set[str]]]: Scope, declared path and the
                names of the types declaring it, for each declared directory
                containing the path: shared directories under the vault root
                and, for a path inside campaigns/campaign_N, that campaign's
                directories. The last entry is the deepest.

        Raises:
            ValueError: The path is outside this vault.
        """
        # Compare path components rather than building a Path per declaration:
        # this runs for every record and every type-bound link target.
        parts = relative_parts(path, self.root)
        scope = find_campaign(path, self.root)
        bases: dict[str, tuple[str, ...] | None] = {
            "shared": (),
            "campaign": ("campaigns", scope) if scope else None,
        }
        found: dict[tuple[str, ...], tuple[str, str, set[str]]] = {}
        for name, directories in self.declared_directories().items():
            for area, declared in directories.items():
                base = bases[area]
                if base is None:
                    continue
                directory = (*base, *declared.split("/"))
                if parts[: len(directory)] != directory:
                    continue
                found.setdefault(directory, (area, declared, set()))[2].add(name)
        return [found[key] for key in sorted(found, key=len)]


def link_key(name: str) -> str:
    """Normalise a link target or file path into a case-insensitive index key.

    Args:
        name: Vault-relative path or link target text.

    Returns:
        str: NFC-normalised, casefolded key so that equivalent Unicode
            spellings and case variants share one entry.
    """
    return unicodedata.normalize("NFC", name).casefold()


def name_key(name: str) -> str:
    """Normalise a record name or alias so that equal names compare equal.

    Args:
        name: Name as written.

    Returns:
        str: The name as link_key returns it, with surrounding whitespace
            removed and inner runs of whitespace collapsed. Empty for a blank
            name.
    """
    return link_key(" ".join(name.split()))


# From the start of a line, an aliases field that may hold a value: text
# after the colon, or a block list on the lines below.
ALIASES = re.compile(rb"[\"']?aliases[\"']?[ \t]*:[ \t]*(?:\S|(?:\s|#[^\n]*)*-\s)")


def may_declare_aliases(data: bytes) -> bool:
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


def read_aliases(frontmatter: Frontmatter) -> list[str]:
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


@dataclass(frozen=True)
class Name:
    """One name a record goes by.

    Attributes:
        path: Absolute path of the record.
        alias: Whether the name is one of the record's aliases; otherwise it
            is the record's filename without .md.
        text: The name as the filename or the alias writes it.
    """

    path: Path
    alias: bool
    text: str


def read_names(root: Path) -> dict[str, list[Name]]:
    """Read every name the vault's records go by: filenames and aliases.

    Every record is read, but only those whose aliases field may hold a
    value are parsed, and then only their frontmatter.

    Args:
        root: Resolved vault directory.

    Returns:
        dict[str, list[Name]]: Each name, as name_key returns it, to the
            records that go by it, in path order with a record's filename
            before its aliases. Templates and whatever record_files leaves
            out are not read. A record that cannot be read or parsed
            contributes its filename only, since its aliases are unknown.

    Raises:
        ValueError: The root is a symlink or is not a directory.
        OSError: A directory cannot be read.
    """
    names: dict[str, list[Name]] = {}
    for path in record_files(root, root):
        # Validation scans templates too; they are not records with names.
        if "templates" in path.parts and is_template(path, root):
            continue
        names.setdefault(name_key(path.stem), []).append(Name(path, False, path.stem))
        try:
            data = path.read_bytes()
            if not may_declare_aliases(data):
                continue
            frontmatter = Frontmatter.parse(data.decode("utf-8-sig"))[0]
        except OSError, UnicodeError, yaml.YAMLError, ValueError, RecursionError:
            continue
        for alias in read_aliases(frontmatter):
            if key := name_key(alias):
                names.setdefault(key, []).append(Name(path, True, alias))
    return names


def read_record(path: Path, vault: Path | None) -> tuple[Path, Path, Record]:
    """Find and parse the record a command names.

    Args:
        path: The record. With a vault, a relative path is taken from the
            vault root; without one, from the working directory.
        vault: Vault root, or None to discover the vault from the record's
            location.

    Returns:
        tuple[Path, Path, Record]: The resolved vault root, the record's path
            as a scan of the vault spells it, whatever case the given path
            used, and the parsed record.

    Raises:
        ValueError: The file cannot be found in a vault, is not one of its
            records (hidden entries, symlinks, cache directories, docs/,
            scripts/ and AGENTS.md are not) or is a template, or cannot be
            parsed.
    """
    root, located = locate(path, vault)
    key = link_key(located.name)
    source = next(
        (
            file
            for file in record_files(located.parent, root)
            if file.parent == located.parent
            and link_key(file.name) == key
            and file.samefile(located)
        ),
        None,
    )
    relative = relative_posix(located, root)
    if source is None or is_template(source, root):
        raise ValueError(f"{relative} is not a record")
    record, diagnostics = Record.parse(source, root)
    if record is None:
        raise ValueError(f"cannot parse {relative}: {diagnostics[0].message}")
    return root, source, record


def spellings(path: Path) -> set[str]:
    """List the final target segments with which a link can name a file.

    Args:
        path: A file in the vault.

    Returns:
        set[str]: Its filename as link_key returns it and, for Markdown, the
            filename without .md: the last path segments under which a
            VaultIndex files it.
    """
    names = {link_key(path.name)}
    if path.suffix.lower() == ".md":
        names.add(link_key(path.stem))
    return names


def sharing(files: Iterable[Path], names: set[str]) -> list[Path]:
    """List the files that a link's final target segment can name.

    A link resolves among the files sharing its target's final segment, so
    indexing these files resolves such links exactly as the whole vault would.

    Args:
        files: Files in the vault.
        names: Final target segments, as spellings returns them.

    Returns:
        list[Path]: The files with any of the spellings, in the given order.
    """
    return [path for path in files if not names.isdisjoint(spellings(path))]


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


def mentioning(root: Path, targets: Iterable[Path]) -> Iterator[tuple[Path, bytes]]:
    """Find the records whose text could hold a link to one of some files.

    Args:
        root: Resolved vault directory.
        targets: Files in the vault.

    Yields:
        tuple[Path, bytes]: Each record that spells one of the files' names as
            a link target would, with its contents, in path order. Templates,
            whatever record_files leaves out and files that cannot be read
            are not yielded; the targets themselves may be.
    """
    needles = {
        link_key(path.stem if path.suffix.lower() == ".md" else path.name)
        for path in targets
    }
    for record in record_files(root, root):
        # Validation scans templates too; they are not records that link.
        if "templates" in record.parts and is_template(record, root):
            continue
        try:
            data = record.read_bytes()
        except OSError:
            continue
        if any(_mentions(data, needle) for needle in needles):
            yield record, data
