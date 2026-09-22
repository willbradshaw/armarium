"""Reusable whole-vault file index and lazy parsed-note cache."""

import unicodedata
from pathlib import Path

from armarium.discovery import files
from armarium.lib import Diagnostic
from armarium.parse import Note, parse


class VaultIndex:
    """Resolve canonical full or unique suffix paths, never YAML display aliases."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.targets: dict[str, set[Path]] = {}
        self.notes: dict[Path, tuple[Note | None, list[Diagnostic]]] = {}
        for path in files(root):
            relative = path.relative_to(root)
            names = [relative.as_posix()]
            if path.suffix.lower() == ".md":
                names.append(relative.with_suffix("").as_posix())
            for name in names:
                parts = name.split("/")
                for offset in range(len(parts)):
                    key = unicodedata.normalize(
                        "NFC", "/".join(parts[offset:])
                    ).casefold()
                    self.targets.setdefault(key, set()).add(path)

    def resolve(self, target: str, source: Path) -> tuple[Path | None, str | None]:
        """Return a single file or a stable missing/ambiguous rule identifier."""
        if not target:
            return source, None
        key = unicodedata.normalize("NFC", target.removeprefix("/")).casefold()
        candidates = self.targets.get(key, set())
        if len(candidates) == 1:
            return next(iter(candidates)), None
        return None, "link.ambiguous" if candidates else "link.missing"

    def note(self, path: Path) -> tuple[Note | None, list[Diagnostic]]:
        """Parse referenced Markdown only when needed, retaining parse failures."""
        if path not in self.notes:
            self.notes[path] = parse(path, self.root)
        return self.notes[path]
