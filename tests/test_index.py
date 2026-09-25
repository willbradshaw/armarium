"""File resolution and lazy parsing are independent of record validation."""

from pathlib import Path
from unittest.mock import patch

import pytest

from armarium.index import VaultIndex, _key
from armarium.parse import Body, Frontmatter, Note

# A case-only pair cannot coexist on case-insensitive filesystems such as
# macOS, so tests patch find_files to index one without creating it.
CASE_PAIR = ("Quay Nine.md", "quay nine.md")


class TestVaultIndex:
    def test_construction(self, tmp_path: Path) -> None:
        (tmp_path / "notes").mkdir()
        (tmp_path / "notes/Café.MD").write_text("---\nx: [\n")
        (tmp_path / "image.png").write_bytes(b"image")
        (tmp_path / ".hidden.md").write_text("hidden")
        (tmp_path / "link.md").symlink_to(tmp_path / "notes/Café.MD")
        with patch.object(Note, "parse") as parse:
            index = VaultIndex(tmp_path)
        assert not parse.called
        assert index.notes == {}
        assert set(index.targets) == {
            "notes/café.md",
            "café.md",
            "notes/café",
            "café",
            "image.png",
        }
        assert index.root == tmp_path.resolve()

    def test_case_only_pair(self, tmp_path: Path) -> None:
        paths = [tmp_path / name for name in CASE_PAIR]
        with patch("armarium.index.find_files", return_value=paths):
            index = VaultIndex(tmp_path)
        assert index.targets == {"quay nine.md": set(paths), "quay nine": set(paths)}


class TestVaultIndexResolve:
    @pytest.mark.parametrize(
        "target, expected, rule",
        [
            ("notes/Café", "notes/Café.md", None),
            ("Café.md", "notes/Café.md", None),
            ("Cafe\u0301", "notes/Café.md", None),
            ("/notes/Café.md", "notes/Café.md", None),
            ("café", "notes/Café.md", None),
            ("CAFÉ", "notes/Café.md", None),
            ("NOTES/CAFÉ.MD", "notes/Café.md", None),
            ("Straße", "Straße.md", None),
            ("STRASSE", "Straße.md", None),
            ("strasse", "Straße.md", None),
            ("Nickname", None, "link.missing"),
            ("same", None, "link.ambiguous"),
            ("a/same", "a/same.md", None),
            ("image.png", "image.png", None),
            ("missing", None, "link.missing"),
            ("", "source.md", None),
        ],
    )
    def test_resolution(
        self, tmp_path: Path, target: str, expected: str | None, rule: str | None
    ) -> None:
        names = ("notes/Café.md", "Straße.md", "a/same.md", "b/same.md", "image.png")
        for name in names:
            path = tmp_path / name
            path.parent.mkdir(exist_ok=True)
            path.write_text("---\naliases: [Nickname]\n---\n")
        assert VaultIndex(tmp_path).resolve(target, tmp_path / "source.md") == (
            tmp_path / expected if expected else None,
            rule,
        )

    @pytest.mark.parametrize("target", ["Quay Nine", "quay nine", "QUAY NINE.md"])
    def test_case_only_pair(self, tmp_path: Path, target: str) -> None:
        paths = [tmp_path / name for name in CASE_PAIR]
        with patch("armarium.index.find_files", return_value=paths):
            index = VaultIndex(tmp_path)
        assert index.resolve(target, tmp_path / "source.md") == (
            None,
            "link.ambiguous",
        )

    def test_outside_source(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="inside"):
            VaultIndex(tmp_path).resolve("", tmp_path.parent / "outside.md")


class TestVaultIndexResolveField:
    @pytest.mark.parametrize(
        ("value", "resolved", "error"),
        [
            ("[[Target]]", "Target.md", None),
            ("[[Target|Alias]]", "Target.md", None),
            ("[[Target.md#Heading]]", "Target.md", None),
            ("[[Target]] [[Target]]", None, "field must hold exactly one wikilink"),
            (["[[Target]]"], None, "field must hold exactly one wikilink"),
            ("plain", None, "field must hold exactly one wikilink"),
            (None, None, "field must hold exactly one wikilink"),
            (
                "[[broken",
                None,
                "use [[target]] with balanced double brackets on one line",
            ),
            ("[[missing]]", None, "cannot uniquely resolve [[missing]]"),
            ("[[same]]", None, "cannot uniquely resolve [[same]]"),
        ],
    )
    def test_field(
        self, tmp_path: Path, value: object, resolved: str | None, error: str | None
    ) -> None:
        for name in ("Target.md", "a/same.md", "b/same.md"):
            path = tmp_path / name
            path.parent.mkdir(exist_ok=True)
            path.write_text("")
        note = Note(
            tmp_path / "selected.md", Frontmatter({"field": value}), Body("", 1)
        )
        assert VaultIndex(tmp_path).resolve_field(note, "field") == (
            tmp_path / resolved if resolved else None,
            error,
        )


class TestVaultIndexParse:
    @pytest.mark.parametrize(
        "text, failed", [("plain note", False), ("---\nx: [\n---\n", True)]
    )
    def test_cache(self, tmp_path: Path, text: str, failed: bool) -> None:
        path = tmp_path / "note.md"
        path.write_text(text)
        index = VaultIndex(tmp_path)
        with patch.object(Note, "parse", wraps=Note.parse) as parse:
            first = index.parse(path)
            assert index.parse(path) is first
            parse.assert_called_once_with(path, tmp_path)
        assert (first[0] is None) == failed
        assert bool(first[1]) == failed
        assert path.read_text() == text

    @pytest.mark.parametrize("outside, suffix", [(True, ".md"), (False, ".png")])
    def test_invalid_target(self, tmp_path: Path, outside: bool, suffix: str) -> None:
        path = (tmp_path.parent if outside else tmp_path) / f"note{suffix}"
        with pytest.raises(ValueError, match="Markdown inside"):
            VaultIndex(tmp_path).parse(path)


class TestKey:
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("Cafe\u0301", "café"),
            ("CAFÉ", "café"),
            ("Straße", "strasse"),
            ("notes/Quay Nine.MD", "notes/quay nine.md"),
            ("image.png", "image.png"),
        ],
    )
    def test_key(self, name: str, expected: str) -> None:
        assert _key(name) == expected
