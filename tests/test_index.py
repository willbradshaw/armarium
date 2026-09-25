"""File resolution and lazy parsing are independent of record validation."""

from pathlib import Path
from unittest.mock import patch

import pytest

from armarium.index import VaultIndex, _key
from armarium.parse import Body, Frontmatter, Record

# A case-only pair cannot coexist on case-insensitive filesystems such as
# macOS, so tests patch find_files to index one without creating it.
CASE_PAIR = ("Quay Nine.md", "quay nine.md")


class TestVaultIndex:
    def test_construction(self, tmp_path: Path) -> None:
        (tmp_path / "records").mkdir()
        (tmp_path / "records/Café.MD").write_text("---\nx: [\n")
        (tmp_path / "image.png").write_bytes(b"image")
        (tmp_path / ".hidden.md").write_text("hidden")
        (tmp_path / "link.md").symlink_to(tmp_path / "records/Café.MD")
        with patch.object(Record, "parse") as parse:
            index = VaultIndex(tmp_path)
        assert not parse.called
        assert index.records == {}
        assert set(index.targets) == {
            "records/café.md",
            "café.md",
            "records/café",
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
            ("records/Café", "records/Café.md", None),
            ("Café.md", "records/Café.md", None),
            ("Cafe\u0301", "records/Café.md", None),
            ("/records/Café.md", "records/Café.md", None),
            ("café", "records/Café.md", None),
            ("CAFÉ", "records/Café.md", None),
            ("RECORDS/CAFÉ.MD", "records/Café.md", None),
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
        names = ("records/Café.md", "Straße.md", "a/same.md", "b/same.md", "image.png")
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
        record = Record(
            tmp_path / "selected.md", Frontmatter({"field": value}), Body("", 1)
        )
        assert VaultIndex(tmp_path).resolve_field(record, "field") == (
            tmp_path / resolved if resolved else None,
            error,
        )


class TestVaultIndexParse:
    @pytest.mark.parametrize(
        "text, failed", [("plain record", False), ("---\nx: [\n---\n", True)]
    )
    def test_cache(self, tmp_path: Path, text: str, failed: bool) -> None:
        path = tmp_path / "record.md"
        path.write_text(text)
        index = VaultIndex(tmp_path)
        with patch.object(Record, "parse", wraps=Record.parse) as parse:
            first = index.parse(path)
            assert index.parse(path) is first
            parse.assert_called_once_with(path, tmp_path)
        assert (first[0] is None) == failed
        assert bool(first[1]) == failed
        assert path.read_text() == text

    @pytest.mark.parametrize("outside, suffix", [(True, ".md"), (False, ".png")])
    def test_invalid_target(self, tmp_path: Path, outside: bool, suffix: str) -> None:
        path = (tmp_path.parent if outside else tmp_path) / f"record{suffix}"
        with pytest.raises(ValueError, match="Markdown inside"):
            VaultIndex(tmp_path).parse(path)


class TestVaultIndexDeclaredDirectories:
    def test_reads_usable_declarations(self, tmp_path: Path) -> None:
        for name, text in {
            "Content.md": "directories: {shared: content, campaign: content}",
            "nested/Widget.md": "directories: {campaign: widgets}",
            "Bare.md": 'type: "[[Type]]"',
            "Bad.md": "directories: {shared: /x}",
            "Broken.md": "x: [",
            "notes.txt": "directories: {shared: content}",
        }.items():
            path = tmp_path / "reference/types" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"---\n{text}\n---\n")
        index = VaultIndex(tmp_path)
        assert index.declared_directories() == {
            "Content": {"shared": "content", "campaign": "content"},
            "Widget": {"campaign": "widgets"},
        }
        # Every definition is parsed through the cache, once for the run.
        assert set(index.records) == {
            tmp_path / "reference/types" / name
            for name in (
                "Content.md",
                "nested/Widget.md",
                "Bare.md",
                "Bad.md",
                "Broken.md",
            )
        }
        with patch.object(Record, "parse", wraps=Record.parse) as parse:
            assert index.declared_directories() == index.declared_directories()
        assert parse.call_count == 0

    @pytest.mark.parametrize("kind", ["missing", "file", "symlink"])
    def test_unusable_types_directory(self, tmp_path: Path, kind: str) -> None:
        types = tmp_path / "reference/types"
        if kind == "file":
            types.parent.mkdir()
            types.write_text("")
        elif kind == "symlink":
            (tmp_path / "elsewhere").mkdir()
            types.parent.mkdir()
            types.symlink_to(tmp_path / "elsewhere", target_is_directory=True)
        assert VaultIndex(tmp_path).declared_directories() == {}


class TestVaultIndexContainingDirectories:
    DECLARATIONS = {
        "Content": "{shared: content, campaign: content}",
        "Session": "{campaign: sessions}",
        "Transcript": "{campaign: sessions/transcripts}",
        "Widget": "{shared: content}",
    }

    @pytest.mark.parametrize(
        "relative, expected",
        [
            ("content/A.md", [("shared", "content", {"Content", "Widget"})]),
            ("content/nested/A.md", [("shared", "content", {"Content", "Widget"})]),
            (
                "campaigns/campaign_1/content/A.md",
                [("campaign", "content", {"Content"})],
            ),
            (
                "campaigns/campaign_1/sessions/S.md",
                [("campaign", "sessions", {"Session"})],
            ),
            (
                "campaigns/campaign_1/sessions/transcripts/S.md",
                [
                    ("campaign", "sessions", {"Session"}),
                    ("campaign", "sessions/transcripts", {"Transcript"}),
                ],
            ),
            ("campaigns/other/content/A.md", []),
            ("sessions/S.md", []),
            ("elsewhere.md", []),
        ],
    )
    def test_containing(
        self, tmp_path: Path, relative: str, expected: list[tuple[str, str, set[str]]]
    ) -> None:
        for name, declared in self.DECLARATIONS.items():
            path = tmp_path / "reference/types" / f"{name}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"---\ndirectories: {declared}\n---\n")
        index = VaultIndex(tmp_path)
        assert index.containing_directories(tmp_path / relative) == expected

    def test_outside_vault(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            VaultIndex(tmp_path).containing_directories(tmp_path.parent / "a.md")


class TestKey:
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("Cafe\u0301", "café"),
            ("CAFÉ", "café"),
            ("Straße", "strasse"),
            ("records/Quay Nine.MD", "records/quay nine.md"),
            ("image.png", "image.png"),
        ],
    )
    def test_key(self, name: str, expected: str) -> None:
        assert _key(name) == expected
