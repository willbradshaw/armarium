"""Parser contracts for source locations, YAML aliases and declared record types."""

from pathlib import Path

import pytest

from armarium.parse import Note, normalize, parse


def test_kind_uses_canonical_link_syntax() -> None:
    note = Note(Path("example.md"), {"type": "[[types/Content.md]]"}, "", 1)
    assert note.kind == "Content"
    aliased = Note(note.path, {"type": "[[types/Content|Alias]]"}, "", 1)
    assert aliased.kind is None


def test_normalize_allows_shared_aliases_but_rejects_cycles() -> None:
    shared = ["value"]
    source = {"first": shared, "second": shared}
    normalized = normalize(source)
    assert normalized == source
    assert normalized["first"] is not normalized["second"]
    cycle: list[object] = []
    cycle.append(cycle)
    with pytest.raises(ValueError, match="recursive YAML aliases"):
        normalize(cycle)


@pytest.mark.parametrize(
    ("text", "body", "start"),
    [
        ("## Notes\n", "## Notes\n", 1),
        ("---\ntitle: Example\n---\n## Notes\n", "## Notes\n", 4),
        ("---\n---\n", "", 3),
    ],
)
def test_body_start_line(tmp_path: Path, text: str, body: str, start: int) -> None:
    path = tmp_path / "example.md"
    path.write_text(text)
    note, diagnostics = parse(path, tmp_path)
    assert diagnostics == [] and note is not None
    assert note.body == body
    assert note.body_start_line == start


def test_parse_failure_is_a_located_report(tmp_path: Path) -> None:
    path = tmp_path / "broken.md"
    path.write_text("---\nname: first\nname: second\n---\n")
    note, diagnostics = parse(path, tmp_path)
    assert note is None and len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.path == "broken.md"
    assert diagnostic.rule == "parse.invalid"
    assert diagnostic.line == 3
    assert diagnostic.severity == "error"
    assert "duplicate key" in diagnostic.message
