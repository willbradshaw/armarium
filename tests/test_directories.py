"""Directory scans retain per-file semantics and deterministic failure handling."""

from pathlib import Path

import pytest
from test_intrafile import VALID, write

from armarium.discovery import files
from armarium.validation import validate


def test_directory_equivalence_and_continuation(vault: Path) -> None:
    write(vault, VALID)
    (vault / "content/Bad.md").write_text("---\nx: [\n---\n")
    (vault / "content/Unknown.md").write_text('---\ntype: "[[Unknown]]"\n---\n')
    (vault / "content/Page.md").write_text("untyped page")
    directory = validate(vault / "content")
    individual = [validate(p) for p in files(vault / "content")]
    assert directory.diagnostics == sorted(d for r in individual for d in r.diagnostics)
    assert (directory.checked, directory.skipped, directory.unsupported) == (3, 1, 1)
    assert directory.failed
    assert directory == validate(vault / "content")


def test_empty_exclusions_assets_and_context(vault: Path, tmp_path: Path) -> None:
    empty = vault / "extra"
    empty.mkdir()
    assert validate(empty).checked == 0
    for excluded in [".git", ".obsidian", ".scratch", "__pycache__", "node_modules"]:
        directory = empty / excluded
        directory.mkdir()
        (directory / "Bad.md").write_text("---\nx: [\n---\n")
    (empty / "view.base").write_text("not Markdown")
    (empty / "outside").symlink_to(tmp_path, target_is_directory=True)
    path = empty / "Page.md"
    path.write_text("[[types/Content]] [[templates/Content]]")
    assert not validate(empty).failed
    assert validate(empty).skipped == 1
    with pytest.raises(ValueError, match="symlink"):
        validate(empty / "outside", vault)


def test_templates_are_not_completed_records(vault: Path) -> None:
    result = validate(vault / "reference/templates")
    assert result.skipped == 5 and not result.failed
