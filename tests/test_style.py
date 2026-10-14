"""Style records declare how a kind of art is made and stored."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from armarium.parse import Record
from armarium.style import (
    STYLE_DIRECTORY,
    Style,
    _count,
    art_directory,
    choose_style,
    parse_style,
    read_styles,
)


def write_style(root: Path, name: str, fields: dict[str, Any], body: str = "") -> Path:
    path = root / STYLE_DIRECTORY / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"type": "[[Reference]]", **fields}
    path.write_text(f"---\n{yaml.safe_dump(metadata)}---\n{body}")
    return path


def record(root: Path, text: str, name: str = "content/A.md") -> Record:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    parsed, _ = Record.parse(path, root)
    assert parsed is not None
    return parsed


class TestStyleAppliesTo:
    @pytest.mark.parametrize(
        ("illustrates", "kind", "subtype", "expected"),
        [
            (("Content/Gear",), "Content", "Gear", True),
            (("Content/Gear",), "Content", "NPC", False),
            (("Content/Gear",), "Content", None, False),
            (("Content",), "Content", "NPC", True),
            (("Content",), "Note", None, False),
            (("Note", "Content/Gear"), "Note", None, True),
            (("Content/Gear",), None, "Gear", False),
            (("Content/3",), "Content", 3, False),
            ((), "Content", "Gear", False),
        ],
    )
    def test_matches_type_or_type_and_subtype(
        self,
        illustrates: tuple[str, ...],
        kind: str | None,
        subtype: object,
        expected: bool,
    ) -> None:
        assert Style("S", "", illustrates).applies_to(kind, subtype) is expected


class TestArtDirectory:
    @pytest.mark.parametrize("value", ["assets/art", "assets/art/gear"])
    def test_accepts_a_folder_inside_assets(self, value: str) -> None:
        assert art_directory(value) == value

    @pytest.mark.parametrize(
        "value", ["content", "assets", "assets/../content", "assets/art/", 3, None]
    )
    def test_refuses_anything_else(self, value: object) -> None:
        with pytest.raises(
            ValueError, match="directory must be a folder inside assets/"
        ):
            art_directory(value)


class TestCount:
    @pytest.mark.parametrize(
        ("data", "expected"), [({}, None), ({"n": None}, None), ({"n": 3}, 3)]
    )
    def test_reads_a_positive_number(
        self, data: dict[str, Any], expected: int | None
    ) -> None:
        assert _count(data, "n") == expected

    @pytest.mark.parametrize("value", [0, -1, 2.5, "3", True])
    def test_refuses_anything_else(self, value: object) -> None:
        with pytest.raises(ValueError, match="n must be a whole number of at least 1"):
            _count({"n": value}, "n")


class TestParseStyle:
    def test_takes_defaults(self, tmp_path: Path) -> None:
        parsed = record(
            tmp_path, '---\ntype: "[[Reference]]"\n---\n', "reference/styles/Plain.md"
        )
        assert parse_style(parsed) == Style("Plain", "")

    def test_reads_every_field(self, tmp_path: Path) -> None:
        fields = {
            "illustrates": ["Content/Gear", "Note"],
            "directory": "assets/art/gear",
            "opacity": True,
            "max_bytes": 5000,
            "max_edge": 600,
        }
        path = write_style(
            tmp_path, "Gear", fields, "\nPaint the item.\n\nNo text.\n\n"
        )
        parsed, _ = Record.parse(path, tmp_path)
        assert parsed is not None
        assert parse_style(parsed) == Style(
            "Gear",
            "Paint the item.\n\nNo text.",
            ("Content/Gear", "Note"),
            "assets/art/gear",
            True,
            5000,
            600,
        )

    @pytest.mark.parametrize(
        ("fields", "message"),
        [
            ({"illustrates": "Content/Gear"}, "illustrates must list record types"),
            ({"illustrates": ["Content/"]}, "illustrates must list record types"),
            (
                {"illustrates": ["Content/Gear/Ring"]},
                "illustrates must list record types",
            ),
            ({"illustrates": [" Content"]}, "illustrates must list record types"),
            ({"illustrates": [3]}, "illustrates must list record types"),
            ({"type": None}, "a style must be a Reference record"),
            ({"type": "[[Content]]"}, "a style must be a Reference record"),
            ({"directory": "content"}, "directory must be a folder inside assets/"),
            ({"opacity": "yes"}, "opacity must be true or false"),
            ({"max_bytes": 0}, "max_bytes must be a whole number"),
            ({"max_edge": "big"}, "max_edge must be a whole number"),
        ],
    )
    def test_refuses_a_field_of_the_wrong_form(
        self, tmp_path: Path, fields: dict[str, Any], message: str
    ) -> None:
        path = write_style(tmp_path, "Gear", fields)
        parsed, _ = Record.parse(path, tmp_path)
        assert parsed is not None
        with pytest.raises(ValueError, match=message):
            parse_style(parsed)


class TestReadStyles:
    def test_reads_every_style_in_path_order(self, tmp_path: Path) -> None:
        write_style(tmp_path, "Scrolls", {"opacity": True})
        write_style(tmp_path, "nested/Gear", {})
        (tmp_path / STYLE_DIRECTORY / "notes.txt").write_text("not a style")
        assert read_styles(tmp_path) == {
            "Gear": Style("Gear", ""),
            "Scrolls": Style("Scrolls", "", opacity=True),
        }

    def test_a_vault_without_styles_has_none(self, tmp_path: Path) -> None:
        assert read_styles(tmp_path) == {}

    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("---\ntype: [\n---\n", "reference/styles/Bad.md: "),
            (
                '---\ntype: "[[Reference]]"\nmax_edge: 0\n---\n',
                "reference/styles/Bad.md: max_edge",
            ),
            ("Just some style text.\n", "reference/styles/Bad.md: a style must be"),
        ],
    )
    def test_refuses_a_style_it_cannot_read(
        self, tmp_path: Path, text: str, message: str
    ) -> None:
        write_style(tmp_path, "Good", {})
        (tmp_path / STYLE_DIRECTORY / "Bad.md").write_text(text)
        with pytest.raises(ValueError, match=message):
            read_styles(tmp_path)


class TestChooseStyle:
    GEAR = '---\ntype: "[[Content]]"\nsubtype: Gear\n---\n'

    @pytest.mark.parametrize(
        ("styles", "name", "expected"),
        [
            ({}, None, None),
            ({"Gear": ["Content/Gear"]}, None, "Gear"),
            ({"Lore": ["Content/Lore"]}, None, None),
            ({"Gear": ["Content/Gear"], "Lore": ["Content/Lore"]}, None, "Gear"),
            ({"Gear": ["Content/Gear"], "Ink": []}, "Ink", "Ink"),
            ({"Gear": ["Content/Gear"], "All": ["Content"]}, "All", "All"),
        ],
    )
    def test_chooses_the_named_or_only_applicable_style(
        self,
        tmp_path: Path,
        styles: dict[str, list[str]],
        name: str | None,
        expected: str | None,
    ) -> None:
        for title, illustrates in styles.items():
            write_style(tmp_path, title, {"illustrates": illustrates})
        chosen = choose_style(tmp_path, record(tmp_path, self.GEAR), name)
        assert (None if chosen is None else chosen.name) == expected

    @pytest.mark.parametrize(
        ("name", "message"),
        [
            ("Missing", "no style Missing in reference/styles/"),
            (None, "styles All, Gear all apply; choose one with --style"),
        ],
    )
    def test_refuses_without_one_style(
        self, tmp_path: Path, name: str | None, message: str
    ) -> None:
        write_style(tmp_path, "Gear", {"illustrates": ["Content/Gear"]})
        write_style(tmp_path, "All", {"illustrates": ["Content"]})
        with pytest.raises(ValueError, match=message):
            choose_style(tmp_path, record(tmp_path, self.GEAR), name)
