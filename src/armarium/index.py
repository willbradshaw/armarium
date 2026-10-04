"""Index vault files and lazily parse referenced Markdown records."""

import unicodedata
from pathlib import Path

from jsonschema.exceptions import SchemaError

from armarium.extensions import ExtensionSet, load_extension_set
from armarium.lib import (
    Diagnostic,
    find_campaign,
    find_files,
    parse_directories,
    parse_subtype_directories,
)
from armarium.parse import Record
from armarium.schemas import Schema

# Failures loading a schema or the extension set, kept to raise again for each record.
LOAD_ERRORS = (OSError, ValueError, SchemaError, RecursionError)


class VaultIndex:
    """Hold one validation run's file targets and parsed records for a vault."""

    def __init__(self, root: Path) -> None:
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
        """
        self.root = root.resolve()
        self.targets: dict[str, set[Path]] = {}
        self.records: dict[Path, tuple[Record | None, list[Diagnostic]]] = {}
        self._extensions: ExtensionSet | Exception | None = None
        self._schemas: dict[Path, Schema | Exception] = {}
        self._declarations: dict[str, dict[str, str]] | None = None
        self._subtype_directories: dict[str, str] | None = None
        for path in find_files(self.root):
            relative = path.relative_to(self.root)
            # Markdown links may include or omit .md; asset extensions matter.
            names = [relative.as_posix()]
            if path.suffix.lower() == ".md":
                names.append(relative.with_suffix("").as_posix())
            for name in names:
                parts = name.split("/")
                # Index each trailing path, from the full path to the filename.
                for offset in range(len(parts)):
                    key = link_key("/".join(parts[offset:]))
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
        if not source.is_relative_to(self.root):
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
        if not path.is_relative_to(self.root) or path.suffix.lower() != ".md":
            raise ValueError("target must be Markdown inside the indexed vault")
        if path not in self.records:
            self.records[path] = Record.parse(path, self.root)
        return self.records[path]

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

    def subtype_directories(self) -> dict[str, str]:
        """Read the subfolder the Content Type record declares for each subtype.

        Returns:
            dict[str, str]: Content subtype to its declared subfolder below
                each Content directory. Empty when reference/types/Content.md
                declares none, cannot be read, or holds an unusable
                declaration, which validate_vault reports. Read once per
                validation run; callers must not modify the mapping.
        """
        if self._subtype_directories is None:
            self._subtype_directories = self._read_subtype_directories()
        return self._subtype_directories

    def _read_subtype_directories(self) -> dict[str, str]:
        """Parse the Content Type record for subtype_directories."""
        path = self.root / "reference/types/Content.md"
        if path.is_symlink() or not path.is_file():
            return {}
        record, _ = self.parse(path)
        if record is None:
            return {}
        try:
            return parse_subtype_directories(
                record.frontmatter.get("subtype_directories"),
                self.extension_set().subtypes,
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
        parts = path.relative_to(self.root).parts
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
