"""Index vault files and lazily parse referenced Markdown notes."""

import unicodedata
from pathlib import Path

from armarium.lib import Diagnostic, find_files
from armarium.parse import Note


class VaultIndex:
    """Hold one validation run's file targets and parsed notes for a vault."""

    def __init__(self, root: Path) -> None:
        """Index visible files, including assets, by full and suffix paths.

        Args:
            root: Vault directory; hidden files and symlinks are excluded.
        """
        self.root = root.resolve()
        self.targets: dict[str, set[Path]] = {}
        self.notes: dict[Path, tuple[Note | None, list[Diagnostic]]] = {}
        for path in find_files(self.root):
            relative = path.relative_to(self.root)
            names = [relative.as_posix()]
            if path.suffix.lower() == ".md":
                names.append(relative.with_suffix("").as_posix())
            for name in names:
                parts = name.split("/")
                for offset in range(len(parts)):
                    key = unicodedata.normalize("NFC", "/".join(parts[offset:]))
                    self.targets.setdefault(key, set()).add(path)

    def resolve(self, target: str, source: Path) -> tuple[Path | None, str | None]:
        """Resolve a parsed link without using display names or YAML aliases.

        Args:
            target: File target from parse_wikilink; empty for a self-anchor.
            source: Absolute source-note path inside this vault.

        Returns:
            tuple[Path | None, str | None]: A resolved path and no error, or no
                path and the rule link.missing or link.ambiguous. Matching is
                case-sensitive and Unicode-normalized. Anchors are not checked.

        Raises:
            ValueError: The source lies outside this vault.
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
