"""Layout records declare how a kind of record prints as a handout."""

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from armarium.layout import (
    LAYOUT_DIRECTORY,
    POINTS,
    Layout,
    Mark,
    choose_layout,
    parse_layout,
    points,
    read_layouts,
)
from armarium.parse import Record

SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "vaults/starter/reference/schemas/reference.schema.json"
)


@pytest.fixture(autouse=True)
def reference_schema(tmp_path: Path) -> None:
    target = tmp_path / "reference/schemas/reference.schema.json"
    target.parent.mkdir(parents=True)
    shutil.copy(SCHEMA, target)


def write_layout(root: Path, name: str, fields: dict[str, Any]) -> Path:
    path = root / LAYOUT_DIRECTORY / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"type": "[[Reference]]", "subtype": "Layout", **fields}
    path.write_text(f"---\n{yaml.safe_dump(metadata)}---\n")
    return path


def record(root: Path, text: str, name: str = "content/A.md") -> Record:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    parsed, _ = Record.parse(path, root)
    assert parsed is not None
    return parsed


class TestPoints:
    @pytest.mark.parametrize(
        ("length", "expected"),
        [("72pt", 72), ("1in", 72), ("0.5in", 36), ("2.54cm", 72), ("25.4mm", 72)],
    )
    def test_converts_each_unit(self, length: str, expected: float) -> None:
        assert points(length) == pytest.approx(expected)

    @pytest.mark.parametrize("length", ["1", "1 in", "-1in", "1ft", "in", ".5in"])
    def test_refuses_anything_else(self, length: str) -> None:
        with pytest.raises(ValueError, match="is not a length such as 0.7in"):
            points(length)


class TestLayoutAppliesTo:
    @pytest.mark.parametrize(
        ("prints", "kind", "subtype", "expected"),
        [
            (("Content/Gear",), "Content", "Gear", True),
            (("Content/Gear",), "Content", "Spell", False),
            (("Content",), "Content", "Spell", True),
            ((), "Content", "Gear", False),
        ],
    )
    def test_matches_type_or_type_and_subtype(
        self, prints: tuple[str, ...], kind: str, subtype: str, expected: bool
    ) -> None:
        assert Layout(prints=prints).applies_to(kind, subtype) is expected


class TestParseLayout:
    @pytest.mark.parametrize("extra", ["", "\nprints:\nmargin:\nmark:\nfont:"])
    def test_takes_defaults(self, tmp_path: Path, extra: str) -> None:
        parsed = record(
            tmp_path,
            f'---\ntype: "[[Reference]]"\nsubtype: Layout{extra}\n---\n',
            "reference/layouts/Plain.md",
        )
        assert parse_layout(parsed) == Layout("Plain")

    def test_reads_every_field(self, tmp_path: Path) -> None:
        fields = {
            "prints": ["Content/Gear", "Content/Spell"],
            "callout": "handout",
            "title": False,
            "page": "a4",
            "margin": "18mm",
            "font": "fonts/Lora.ttf",
            "title_size": 48,
            "min_text_size": 16,
            "max_text_size": 36.5,
            "line_spacing": 1.16,
            "image_share": 0.6,
            "mark": {"field": "attunement", "text": "A"},
            "underline_links": True,
            "lowercase_links": True,
        }
        path = write_layout(tmp_path, "Gear", fields)
        parsed, _ = Record.parse(path, tmp_path)
        assert parsed is not None
        assert parse_layout(parsed) == Layout(
            "Gear",
            ("Content/Gear", "Content/Spell"),
            "handout",
            False,
            "a4",
            18 * POINTS["mm"],
            "fonts/Lora.ttf",
            48,
            16,
            36.5,
            1.16,
            0.6,
            Mark("attunement", "A"),
            True,
            True,
        )


class TestReadLayouts:
    def test_reads_every_layout_in_path_order(self, tmp_path: Path) -> None:
        write_layout(tmp_path, "Scrolls", {"image_share": 0.6})
        write_layout(tmp_path, "nested/Gear", {})
        (tmp_path / LAYOUT_DIRECTORY / "Notes.md").write_text("Just notes.\n")
        assert read_layouts(tmp_path) == {
            "Gear": Layout("Gear"),
            "Scrolls": Layout("Scrolls", image_share=0.6),
        }

    def test_a_vault_without_layouts_has_none(self, tmp_path: Path) -> None:
        assert read_layouts(tmp_path) == {}

    @pytest.mark.parametrize(
        ("fields", "message"),
        [
            ({"prints": "Content/Gear"}, "prints: 'Content/Gear' is not"),
            ({"prints": ["Content/Gear/Ring"]}, "prints.0: "),
            ({"callout": "hand out"}, "callout: 'hand out' does not match"),
            ({"callout": ""}, "callout: '' does not match"),
            ({"title": "no"}, "title: 'no' is not"),
            ({"page": "legal"}, "page: 'legal' is not one of"),
            ({"margin": "1"}, "margin: '1' does not match"),
            ({"margin": "-1in"}, "margin: '-1in' does not match"),
            ({"font": " "}, "font: ' ' does not match"),
            ({"title_size": 0}, "title_size: 0 is less than or equal to"),
            ({"min_text_size": "big"}, "min_text_size: 'big' is not"),
            ({"max_text_size": -2}, "max_text_size: -2 is less than or equal to"),
            ({"line_spacing": 0.9}, "line_spacing: 0.9 is less than the minimum"),
            ({"image_share": 1}, "image_share: 1 is greater than or equal to"),
            ({"image_share": 0}, "image_share: 0 is less than or equal to"),
            ({"mark": {"field": "attunement"}}, "mark: 'text' is a required"),
            ({"mark": {"field": "a", "text": "A", "size": 3}}, "mark: Additional"),
            ({"mark": {"field": "a", "text": " "}}, "mark.text: ' ' does not match"),
            ({"underline_links": "yes"}, "underline_links: 'yes' is not"),
            ({"lowercase_links": 1}, "lowercase_links: 1 is not"),
        ],
    )
    def test_refuses_a_field_of_the_wrong_form(
        self, tmp_path: Path, fields: dict[str, Any], message: str
    ) -> None:
        write_layout(tmp_path, "Gear", fields)
        with pytest.raises(
            ValueError, match=f"^reference/layouts/Gear.md: frontmatter.{message}"
        ):
            read_layouts(tmp_path)


class TestChooseLayout:
    GEAR = '---\ntype: "[[Content]]"\nsubtype: Gear\n---\n'
    LAYOUTS = {
        "Gear": Layout("Gear", ("Content/Gear",)),
        "Spells": Layout("Spells", ("Content/Spell",)),
        "Plain": Layout("Plain"),
    }

    @pytest.mark.parametrize(
        ("names", "name", "expected"),
        [
            ((), None, Layout()),
            (("Gear",), None, LAYOUTS["Gear"]),
            (("Spells",), None, Layout()),
            (("Gear", "Spells"), None, LAYOUTS["Gear"]),
            (("Gear", "Plain"), "Plain", LAYOUTS["Plain"]),
        ],
    )
    def test_chooses_the_named_or_only_applicable_layout(
        self,
        tmp_path: Path,
        names: tuple[str, ...],
        name: str | None,
        expected: Layout,
    ) -> None:
        layouts = {key: self.LAYOUTS[key] for key in names}
        assert choose_layout(layouts, record(tmp_path, self.GEAR), name) == expected

    @pytest.mark.parametrize(
        ("name", "message"),
        [
            ("Missing", "no layout Missing in reference/layouts/"),
            (None, "layouts Gear, All all apply; choose one with --layout"),
        ],
    )
    def test_refuses_without_one_layout(
        self, tmp_path: Path, name: str | None, message: str
    ) -> None:
        layouts = {"Gear": self.LAYOUTS["Gear"], "All": Layout("All", ("Content",))}
        with pytest.raises(ValueError, match=message):
            choose_layout(layouts, record(tmp_path, self.GEAR), name)
