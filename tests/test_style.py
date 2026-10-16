"""Style records declare how a kind of art is made and stored."""

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from armarium.parse import Record
from armarium.style import (
    STYLE_DIRECTORY,
    Style,
    art_directory,
    choose_style,
    is_style,
    parse_style,
    read_styles,
)

SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "vaults/starter/reference/schemas/reference.schema.json"
)


@pytest.fixture(autouse=True)
def reference_schema(tmp_path: Path) -> None:
    target = tmp_path / "reference/schemas/reference.schema.json"
    target.parent.mkdir(parents=True)
    shutil.copy(SCHEMA, target)


def write_style(root: Path, name: str, fields: dict[str, Any], body: str = "") -> Path:
    path = root / STYLE_DIRECTORY / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"type": "[[Reference]]", "subtype": "Style", **fields}
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


class TestIsStyle:
    @pytest.mark.parametrize(
        ("frontmatter", "expected"),
        [
            ('type: "[[Reference]]"\nsubtype: Style', True),
            ('type: "[[Reference]]"', False),
            ('type: "[[Reference]]"\nsubtype: Index', False),
            ('type: "[[types/Content]]"\nsubtype: Style', False),
            ("subtype: Style", False),
        ],
    )
    def test_needs_reference_and_style(
        self, tmp_path: Path, frontmatter: str, expected: bool
    ) -> None:
        parsed = record(tmp_path, f"---\n{frontmatter}\n---\n")
        assert is_style(parsed) is expected


class TestParseStyle:
    @pytest.mark.parametrize("value", ["", "\nillustrates:\nreferences:\nsample:"])
    def test_takes_defaults(self, tmp_path: Path, value: str) -> None:
        parsed = record(
            tmp_path,
            f'---\ntype: "[[Reference]]"\nsubtype: Style{value}\n---\n',
            "reference/styles/Plain.md",
        )
        assert parse_style(parsed) == Style("Plain", "")

    def test_reads_every_field(self, tmp_path: Path) -> None:
        fields = {
            "illustrates": ["Content/Gear", "Note"],
            "directory": "assets/art/gear",
            "opacity": True,
            "max_bytes": 5000,
            "max_edge": 600,
            "references": ["[[Lucky Ring]]", "[[assets/art/gear/Rope.webp]]"],
            "sample": 3,
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
            ("Lucky Ring", "assets/art/gear/Rope.webp"),
            3,
        )


class TestReadStyles:
    def test_reads_every_style_in_path_order(self, tmp_path: Path) -> None:
        write_style(tmp_path, "Scrolls", {"opacity": True})
        write_style(tmp_path, "nested/Gear", {})
        (tmp_path / STYLE_DIRECTORY / "notes.txt").write_text("not a style")
        assert read_styles(tmp_path) == {
            "Gear": Style("Gear", ""),
            "Scrolls": Style("Scrolls", "", opacity=True),
        }

    @pytest.mark.parametrize(
        "text",
        [
            '---\ntype: "[[Reference]]"\nmax_edge: 0\n---\n',
            '---\ntype: "[[Reference]]"\nsubtype: Index\n---\n',
            "Just some notes.\n",
        ],
    )
    def test_passes_over_other_records(self, tmp_path: Path, text: str) -> None:
        write_style(tmp_path, "Gear", {})
        (tmp_path / STYLE_DIRECTORY / "Other.md").write_text(text)
        assert read_styles(tmp_path) == {"Gear": Style("Gear", "")}

    def test_a_vault_without_styles_has_none(self, tmp_path: Path) -> None:
        assert read_styles(tmp_path) == {}

    @pytest.mark.parametrize(
        ("fields", "message"),
        [
            ({"illustrates": "Content/Gear"}, "illustrates: 'Content/Gear' is not"),
            ({"illustrates": ["Content/"]}, "illustrates.0: 'Content/' does not"),
            ({"illustrates": ["Content/Gear/Ring"]}, "illustrates.0: "),
            ({"illustrates": [" Content"]}, "illustrates.0: "),
            ({"illustrates": [3]}, "illustrates.0: 3 is not"),
            ({"directory": "content"}, "directory: 'content' does not"),
            ({"directory": "assets"}, "directory: 'assets' does not"),
            ({"directory": "assets/../content"}, "directory: "),
            ({"directory": "assets/art/"}, "directory: "),
            ({"opacity": "maybe"}, "opacity: 'maybe' is not"),
            ({"max_bytes": 0}, "max_bytes: 0 is less than the minimum of 1"),
            ({"max_edge": "big"}, "max_edge: 'big' is not"),
            ({"max_edge": 2.5}, "max_edge: 2.5 is not"),
            ({"references": "[[Ring]]"}, "references: '\\[\\[Ring\\]\\]' is not"),
            ({"references": ["Ring"]}, "references.0: 'Ring' does not"),
            ({"references": ["[[Rope|Rope]]"]}, "references.0: "),
            ({"sample": -2}, "sample: -2 is less than the minimum of 1"),
        ],
    )
    def test_refuses_a_field_of_the_wrong_form(
        self, tmp_path: Path, fields: dict[str, Any], message: str
    ) -> None:
        write_style(tmp_path, "Gear", fields)
        with pytest.raises(
            ValueError, match=f"^reference/styles/Gear.md: frontmatter.{message}"
        ):
            read_styles(tmp_path)

    def test_refuses_a_record_it_cannot_parse(self, tmp_path: Path) -> None:
        write_style(tmp_path, "Good", {})
        (tmp_path / STYLE_DIRECTORY / "Bad.md").write_text("---\ntype: [\n---\n")
        with pytest.raises(ValueError, match="^reference/styles/Bad.md: "):
            read_styles(tmp_path)

    def test_refuses_without_a_reference_schema(self, tmp_path: Path) -> None:
        write_style(tmp_path, "Gear", {})
        (tmp_path / "reference/schemas/reference.schema.json").unlink()
        with pytest.raises(
            ValueError,
            match="^reference/styles/Gear.md: no vault-local schema for Reference$",
        ):
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
