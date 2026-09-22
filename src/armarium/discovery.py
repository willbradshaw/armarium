"""Vault inference uses product structure, never a repository marker alone."""

from pathlib import Path


def find_vault(path: Path, explicit: Path | None = None) -> Path:
    """Locate the closest vault, or enforce an explicitly supplied boundary."""
    if explicit is not None:
        root = explicit.resolve()
        if not root.is_dir() or not path.resolve().is_relative_to(root):
            raise ValueError("target must be inside the selected vault directory")
        return root
    for candidate in (path.resolve(), *path.resolve().parents):
        if (candidate / "reference/types").is_dir() and (
            candidate / "campaigns"
        ).is_dir():
            return candidate
    raise ValueError("cannot infer vault; supply --vault PATH")


def files(root: Path) -> list[Path]:
    """List visible files deterministically, without following any symlinks."""
    import os

    found: list[Path] = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        base = Path(directory)
        dirs[:] = sorted(
            name
            for name in dirs
            if not name.startswith(".")
            and name not in {"__pycache__", "node_modules"}
            and not (base / name).is_symlink()
        )
        found.extend(
            base / name
            for name in sorted(names)
            if not name.startswith(".") and not (base / name).is_symlink()
        )
    return sorted(found)
