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
