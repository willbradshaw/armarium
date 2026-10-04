"""Name and alias lookup reads frontmatter only and never validates."""

from pathlib import Path
from unittest.mock import patch

import pytest

from armarium.find import (
    ALIASES,
    Match,
    _aliases,
    _name_key,
    _read_frontmatter,
    find_records,
)
from armarium.parse import Body, Frontmatter


def write(root: Path, relative: str, frontmatter: str = "", body: str = "") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}---\n{body}" if frontmatter else body)
    return path


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault with spaces"
    for directory in ("reference/types", "campaigns", "content"):
        (root / directory).mkdir(parents=True)
    content = 'type: "[[types/Content]]"\n'
    write(
        root,
        "content/Mara.md",
        content + "subtype: NPC\nsummary: Harbour pilot.\naliases: [The Pilot]\n",
    )
    write(
        root,
        "content/Captain Mara Vey.md",
        content + "subtype: NPC\nsummary: |\n  A captain\twho\n  settles arguments.\n",
    )
    write(
        root,
        "campaigns/campaign_1/content/Quay Nine.md",
        content + "subtype: Location\nsummary:\naliases:\n  - Mara\n  - The Ninth\n",
    )
    write(
        root,
        "content/Port Briselle.md",
        content + "subtype: Location\naliases:\n- Mara's Harbour\n",
    )
    write(root, "notes/Mara.md", 'type: "[[Note]]"\naliases:\n')
    write(root, "content/Wake-lark.md", content + "subtype: Object\naliases: []\n")
    return root


class TestAliases:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("aliases: [Mara]\n", True),
            ("aliases: Mara\n", True),
            ("aliases:\n  - Mara\n", True),
            ("aliases:\n- Mara\n", True),
            ("aliases:\r\n  - Mara\r\n", True),
            ("aliases:\n\n  # known names\n  - Mara\n", True),
            ('"aliases": [Mara]\n', True),
            ("'aliases' : [Mara]\n", True),
            ("type: x\naliases: []\n", True),
            ("aliases:\n", False),
            ("aliases:\n---\n## Notes\n", False),
            ("aliases:\nsummary: A - B\n", False),
            ("aliases:   \ncontent_tags:\n  - Healing\n", False),
            ("old_aliases: [Mara]\n", False),
            ("summary: no aliases: here\n", False),
            ("", False),
        ],
    )
    def test_detects_possible_values(self, text: str, expected: bool) -> None:
        assert bool(ALIASES.search(text.encode())) is expected


class TestMatchLine:
    def test_tab_separated(self, tmp_path: Path) -> None:
        match = Match(tmp_path / "content/Mara.md", "content/Mara.md", "", "name", "")
        assert match.line == "content/Mara.md\t\tname\t"


class TestNameKey:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Mara", "mara"),
            ("MARA", "mara"),
            ("  Mara ", "mara"),
            ("Mara \t  Vey", "mara vey"),
            ("Cafe\u0301", "café"),
            ("Straße", "strasse"),
            ("", ""),
            ("   ", ""),
        ],
    )
    def test_key(self, name: str, expected: str) -> None:
        assert _name_key(name) == expected


class TestReadFrontmatter:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b"---\nsummary: Pilot.\n---\n## Notes\n", {"summary": "Pilot."}),
            (b"\xef\xbb\xbf---\nsummary: Pilot.\n---\n", {"summary": "Pilot."}),
            (b"## Notes\n", {}),
            (b"", {}),
            (b"---\nsummary: [\n---\n", None),
            (b"---\nsummary: Pilot.\n", None),
            (b"---\n- item\n---\n", None),
            (b"---\nsummary: \xff\n---\n", None),
        ],
    )
    def test_reads_or_rejects(
        self, data: bytes, expected: dict[str, object] | None
    ) -> None:
        assert _read_frontmatter(data) == expected

    def test_leaves_the_body_unparsed(self) -> None:
        with patch.object(Body, "__init__") as body:
            assert _read_frontmatter(b"---\nsummary: Pilot.\n---\n## Notes\n")
        assert not body.called


class TestAliasList:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (["Mara", "The Pilot"], ["Mara", "The Pilot"]),
            ("Mara", ["Mara"]),
            (["Mara", 3, None, ["nested"]], ["Mara"]),
            ([], []),
            (None, []),
            (7, []),
            ({"name": "Mara"}, []),
        ],
    )
    def test_strings_only(self, value: object, expected: list[str]) -> None:
        assert _aliases(Frontmatter({"aliases": value})) == expected

    def test_absent(self) -> None:
        assert _aliases(Frontmatter()) == []


class TestFindRecords:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            (
                "mara",
                [
                    ("content/Mara.md", "Content/NPC", "name", "Harbour pilot."),
                    ("notes/Mara.md", "Note", "name", ""),
                    (
                        "campaigns/campaign_1/content/Quay Nine.md",
                        "Content/Location",
                        "alias",
                        "",
                    ),
                ],
            ),
            (
                "captain  MARA vey",
                [
                    (
                        "content/Captain Mara Vey.md",
                        "Content/NPC",
                        "name",
                        "A captain who settles arguments.",
                    )
                ],
            ),
            (
                " THE   pilot ",
                [("content/Mara.md", "Content/NPC", "alias", "Harbour pilot.")],
            ),
            ("the ninth quay", []),
            ("captain", []),
            ("mar", []),
            ("mara's", []),
            ("wake-lark", [("content/Wake-lark.md", "Content/Object", "name", "")]),
            ("gull", []),
        ],
    )
    def test_matches(
        self,
        vault: Path,
        name: str,
        expected: list[tuple[str, str, str, str]],
    ) -> None:
        matches = find_records(name, vault)
        assert [(m.relative, m.kind, m.match, m.summary) for m in matches] == expected
        assert all(m.path == vault.resolve() / m.relative for m in matches)

    def test_discovers_the_vault(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(vault / "content")
        assert [m.relative for m in find_records("wake-lark")] == [
            "content/Wake-lark.md"
        ]

    def test_skips_non_records(self, vault: Path) -> None:
        for relative in (
            "reference/templates/Gull.md",
            "reference/extensions/birds/templates/Gull.md",
            "scripts/Gull.md",
            ".hidden/Gull.md",
            "content/.Gull.md",
        ):
            write(vault, relative, "aliases: [Gull]\n")
        (vault / "content/Gull.txt").write_text("---\naliases: [Gull]\n---\n")
        (vault / "content/Linked Gull.md").symlink_to(vault / "content/Mara.md")
        assert find_records("gull", vault) == []

    @pytest.mark.parametrize(
        "text",
        ["---\naliases: [Gull\n---\n", "---\naliases: [Gull]\n", "---\n- Gull\n---\n"],
    )
    def test_skips_unparseable_records(self, vault: Path, text: str) -> None:
        (vault / "content/Gull.md").write_text(text)
        (vault / "content/Bad.md").write_bytes(b"---\naliases: [Gull, \xff]\n---\n")
        assert find_records("gull", vault) == []

    def test_skips_unreadable_records(self, vault: Path) -> None:
        mara = (vault / "content/Mara.md").resolve()
        read = Path.read_bytes

        def read_bytes(path: Path) -> bytes:
            if path == mara:
                raise OSError("unreadable")
            return read(path)

        with patch.object(Path, "read_bytes", read_bytes):
            matches = find_records("mara", vault)
        assert "content/Mara.md" not in [m.relative for m in matches]
        assert matches

    def test_untyped_record(self, vault: Path) -> None:
        write(vault, "content/Gull.md", body="No frontmatter.\n")
        write(vault, "content/Tern.md", "type: Content\nsubtype: 3\naliases: Gull\n")
        assert [(m.relative, m.kind, m.match) for m in find_records("gull", vault)] == [
            ("content/Gull.md", "", "name"),
            ("content/Tern.md", "", "alias"),
        ]

    def test_parses_only_possible_matches(self, vault: Path) -> None:
        with patch("armarium.find._read_frontmatter", wraps=_read_frontmatter) as read:
            find_records("briselle", vault)
        # The two records with empty aliases and unrelated names stay unparsed.
        assert read.call_count == 4

    @pytest.mark.parametrize("name", ["", "   ", "\t"])
    def test_rejects_blank_name(self, vault: Path, name: str) -> None:
        with pytest.raises(ValueError, match="blank"):
            find_records(name, vault)

    def test_rejects_missing_vault(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            find_records("mara", tmp_path)
