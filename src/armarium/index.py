"""Index vault files and lazily parse referenced Markdown notes."""

import unicodedata
from pathlib import Path

from armarium.lib import Diagnostic, find_files
from armarium.parse import Note


class VaultIndex:
    """Hold one validation run's file targets and parsed notes for a vault."""

    def __init__(self, root: Path) -> None:
        """Map possible link targets to files without reading their contents.

        Each file contributes its vault-relative path and every trailing path.
        For example, reference/types/Content.md contributes that full path,
        types/Content.md and Content.md, plus all three without .md. These keys
        support links such as [[types/Content]] and [[Content]]. Assets keep
        their extensions. Each key maps to a set because multiple files can
        share a name; resolve() reports such matches as ambiguous.

        Parsed notes are stored separately in self.notes, initially empty.
        parse() fills that cache only when a note's contents are needed.

        Args:
            root: Vault directory; hidden files and symlinks are excluded.
        """
        self.root = root.resolve()
        self.targets: dict[str, set[Path]] = {}
        self.notes: dict[Path, tuple[Note | None, list[Diagnostic]]] = {}
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
                    # Equivalent Unicode spellings should share the same key.
                    key = unicodedata.normalize("NFC", "/".join(parts[offset:]))
                    self.targets.setdefault(key, set()).add(path)

    def resolve(self, target: str, source: Path) -> tuple[Path | None, str | None]:
        """Find the single file named by a wikilink's target text.

        For example, target="types/Content" can return the full filesystem path
        /vault/reference/types/Content.md. Here "resolve" means looking up which
        file the link names; this method does not read the file or check whether
        a linked heading or block exists.

        Args:
            target: Target text returned by parse_wikilink, without brackets,
                display alias or heading/block suffix. For [[#Heading]], this
                is an empty string because the link points within its own note.
            source: Full filesystem path of the note containing the link, such
                as /vault/content/Harbour.md, rather than content/Harbour.md.
                An empty target returns this path. Other targets are looked up
                across the vault, not relative to the source note's directory.

        Returns:
            tuple[Path | None, str | None]: (file_path, None) for exactly one
                matching file, (None, "link.missing") for no matches, or
                (None, "link.ambiguous") for multiple matches. Matching is
                case-sensitive, but equivalent Unicode spellings match.
                Display aliases and YAML aliases are not lookup keys.

        Raises:
            ValueError: source is not a full path inside this vault.
        """
        if not source.is_relative_to(self.root):
            raise ValueError("source must be inside the indexed vault")
        if not target:
            return source, None
        key = unicodedata.normalize("NFC", target.removeprefix("/"))
        candidates = self.targets.get(key, set())
        if len(candidates) == 1:
            return next(iter(candidates)), None
        return None, "link.ambiguous" if candidates else "link.missing"

    def resolve_field(self, note: Note, field: str) -> tuple[Path | None, str | None]:
        """Resolve the single wikilink held by one top-level frontmatter field.

        Args:
            note: Parsed note inside this vault.
            field: Top-level frontmatter field name, such as "type".

        Returns:
            tuple[Path | None, str | None]: (file_path, None) when the field
                holds exactly one well-formed link naming exactly one file.
                Otherwise (None, message) saying why not: the field holds no
                link or several, the link text is malformed, or the target is
                missing or ambiguous.
        """
        links = [link for link in note.links if link.location == field]
        if len(links) != 1:
            return None, f"{field} must hold exactly one wikilink"
        (link,) = links
        if link.error is not None:
            return None, link.error
        resolved, rule = self.resolve(link.target, note.path)
        if rule:
            return None, f"cannot uniquely resolve [[{link.target}]]"
        return resolved, None

    def parse(self, path: Path) -> tuple[Note | None, list[Diagnostic]]:
        """Parse a Markdown target once, retaining failures as well as notes.

        Args:
            path: Absolute Markdown path inside the indexed vault.

        Returns:
            tuple[Note | None, list[Diagnostic]]: Cached Note.parse result.

        Raises:
            ValueError: The path is outside this vault or is not Markdown.
        """
        if not path.is_relative_to(self.root) or path.suffix.lower() != ".md":
            raise ValueError("target must be Markdown inside the indexed vault")
        if path not in self.notes:
            self.notes[path] = Note.parse(path, self.root)
        return self.notes[path]
