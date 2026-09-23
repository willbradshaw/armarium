"""Selected-note contextual checks use only relevant vault dependencies."""

from pathlib import Path

import pytest

from armarium.check import check_links
from armarium.index import VaultIndex
from armarium.parse import Note


class TestCheckLinks:
    @pytest.mark.parametrize(
        "text, rule",
        [
            ("[[target|Alias]] [[target.md#Heading]] [[#^block]] ![[image.png]]", None),
            ("[[missing]]", "link.missing"),
            ("[[same]]", "link.ambiguous"),
            ("[[bad]]", "link.malformed"),
            ("[[broken", "link.syntax"),
            ("```markdown\n[[missing]]\n```", None),
            ("```dataview\n[[missing]]\n```", "link.missing"),
            ("`[[missing]]`", None),
            ("`= [[missing]].text`", "link.missing"),
        ],
    )
    def test_body(self, tmp_path: Path, text: str, rule: str | None) -> None:
        for name, body in {
            "selected.md": text,
            "target.md": "plain",
            "image.png": "asset",
            "bad.md": "---\nx: [\n---\n",
            "a/same.md": "",
            "b/same.md": "",
        }.items():
            path = tmp_path / name
            path.parent.mkdir(exist_ok=True)
            path.write_text(body)
        note = Note(tmp_path / "selected.md", {}, text, 5)
        index = VaultIndex(tmp_path)
        result = check_links(note, index)
        assert [d.rule for d in result] == ([rule] if rule else [])
        if result:
            assert result[0].path == "selected.md"
            assert result[0].line == (6 if text.startswith("```") else 5)
        if "[[bad]]" not in text:
            assert tmp_path / "bad.md" not in index.notes

    def test_metadata_and_recovery(self, tmp_path: Path) -> None:
        note = Note(
            tmp_path / "selected.md",
            {"nested": ["[[missing]]"]},
            "[[broken [[other]]",
            8,
        )
        result = check_links(note, VaultIndex(tmp_path))
        assert [(d.rule, d.field, d.line) for d in result] == [
            ("link.missing", "nested.0", 0),
            ("link.syntax", "", 8),
            ("link.missing", "", 8),
        ]
