"""Read visible vault files without requiring the starter's empty directories."""

from dataclasses import dataclass, field
from pathlib import Path

from .parsing import Diagnostic, Page, parse_page


@dataclass(slots=True)
class VaultFiles:
    files: set[str] = field(default_factory=set)
    directories: set[str] = field(default_factory=set)
    pages: dict[str, Page] = field(default_factory=dict)
    errors: list[Diagnostic] = field(default_factory=list)


def read_vault(root: Path) -> VaultFiles:
    """Skip hidden paths and all symlinks; retain errors and continue reading."""
    vault = VaultFiles()

    def on_error(error: OSError) -> None:
        path = Path(error.filename).relative_to(root) if error.filename else Path(".")
        vault.errors.append(Diagnostic(path.as_posix(), "io.read", str(error)))

    for base, directories, files in root.walk(on_error=on_error, follow_symlinks=False):
        directories[:] = sorted(
            name for name in directories
            if not name.startswith(".") and not (base / name).is_symlink()
        )
        vault.directories.update((base / name).relative_to(root).as_posix() for name in directories)
        for name in sorted(files):
            path = base / name
            if name.startswith(".") or path.is_symlink():
                continue
            relative = path.relative_to(root).as_posix()
            vault.files.add(relative)
            if path.suffix != ".md":
                continue
            try:
                page, errors = parse_page(relative, path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError) as error:
                vault.errors.append(Diagnostic(relative, "io.read", str(error)))
                continue
            vault.pages[relative] = page
            vault.errors.extend(errors)
    return vault
