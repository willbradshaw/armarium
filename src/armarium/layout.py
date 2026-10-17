"""Read a vault's handout layouts: how each kind of record prints as a handout."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from armarium.lib import matches_kind
from armarium.parse import Body, Frontmatter, Record
from armarium.schemas import read_subtype_records, select_schema

LAYOUT_DIRECTORY = "reference/layouts"

# Each layout field that may be given in place of a layout's own, with the
# kind of value it takes (text, a number, a switch or a mark) and what it sets.
OVERRIDES = {
    "callout": ("text", "the type of the callout whose text prints"),
    "title": ("switch", "print the record's name at the top"),
    "page": ("text", "the paper size: letter or a4"),
    "margin": ("text", "the margin on every side, such as 0.7in or 18mm"),
    "font": ("text", "a standard PDF font, or the path of a TrueType font file"),
    "title_size": ("number", "the name's font size, in points"),
    "min_text_size": ("number", "the text's smallest font size, in points"),
    "max_text_size": ("number", "the text's largest font size, in points"),
    "line_spacing": ("number", "the distance between lines, times the font size"),
    "image_share": (
        "number",
        "the share of the space below the name left to the picture, 0 to 1",
    ),
    "mark": ("mark", "TEXT beside the name when the record's FIELD is true"),
    "underline_links": ("switch", "underline link text"),
    "lowercase_links": ("switch", "print link text in lowercase"),
}

# Points in each unit a length may be given in.
POINTS = {"pt": 1.0, "in": 72.0, "cm": 72 / 2.54, "mm": 72 / 25.4}
# A length: a number and its unit, such as 0.7in.
LENGTH = re.compile(r"([0-9]+(?:\.[0-9]+)?)(in|mm|cm|pt)")


def points(length: str) -> float:
    """Convert a length to points.

    Args:
        length: A number and its unit, such as ``0.7in`` or ``18mm``.

    Returns:
        float: The length in points.

    Raises:
        ValueError: The value is not such a length.
    """
    match = LENGTH.fullmatch(length)
    if match is None:
        raise ValueError(f"{length!r} is not a length such as 0.7in or 18mm")
    return float(match[1]) * POINTS[match[2]]


@dataclass(frozen=True)
class Mark:
    """Text printed in a handout's top right corner when a field is true.

    Attributes:
        field: The frontmatter field that puts the mark on the page.
        text: The text of the mark.
    """

    field: str
    text: str


@dataclass(frozen=True)
class Layout:
    """How one kind of record prints as a handout, as a layout record declares it.

    Attributes:
        name: The layout record's filename without .md, or "" for the
            defaults used when no layout applies.
        prints: Record kinds the layout applies to, each a type or
            ``Type/Subtype``, such as ``Content/Gear``.
        callout: The type of the callout whose text prints, such as rules.
        title: Whether the record's name prints at the top of the page.
        page: The paper size, letter or a4.
        margin: The margin on every side, in points.
        font: A standard PDF font's name, or the path of a TrueType font
            file, absolute or relative to the vault root.
        title_size: The title's font size, in points.
        min_text_size: The smallest font size of the text, in points.
        max_text_size: The largest font size of the text, in points.
        line_spacing: The distance between lines, as a multiple of the size.
        image_share: The share of the space below the title that the text
            leaves to the picture.
        mark: Text printed in the top right corner when a field is true, or
            None for no mark.
        underline_links: Whether link text is underlined.
        lowercase_links: Whether link text is printed in lowercase.
    """

    name: str = ""
    prints: tuple[str, ...] = ()
    callout: str = "rules"
    title: bool = True
    page: str = "letter"
    margin: float = 0.7 * POINTS["in"]
    font: str = "Times-Roman"
    title_size: float = 36
    min_text_size: float = 12
    max_text_size: float = 24
    line_spacing: float = 1.2
    image_share: float = 0.5
    mark: Mark | None = None
    underline_links: bool = False
    lowercase_links: bool = False

    def applies_to(self, kind: str | None, subtype: object) -> bool:
        """Say whether the layout prints records of a type and subtype.

        Args:
            kind: The record's type name, or None for an untyped record.
            subtype: The record's subtype field, if any.

        Returns:
            bool: Whether the type, or the type and subtype, is among prints.
        """
        return matches_kind(self.prints, kind, subtype)


def _fields(data: Mapping[str, Any]) -> dict[str, Any]:
    """Read the fields a layout sets, other than prints.

    Args:
        data: Layout fields as frontmatter holds them, such as margin as a
            length and mark as a mapping.

    Returns:
        dict[str, Any]: Layout's attribute for each field that is set, with
            margin in points and mark a Mark. A null field is not set, except
            mark, whose null removes the mark.
    """
    fields = {
        name: data[name]
        for name in OVERRIDES
        if name not in ("margin", "mark") and data.get(name) is not None
    }
    if data.get("margin") is not None:
        fields["margin"] = points(data["margin"])
    if "mark" in data:
        mark = data["mark"]
        fields["mark"] = None if mark is None else Mark(mark["field"], mark["text"])
    return fields


def parse_layout(record: Record) -> Layout:
    """Read a layout from its record.

    Every field is optional; an absent or null field takes Layout's default.
    The vault's Reference schema checks each field's form.

    Args:
        record: A layout that satisfies the vault's Reference schema.

    Returns:
        Layout: The layout the record declares.
    """
    data = record.frontmatter
    return replace(
        Layout(),
        name=record.path.stem,
        prints=tuple(data.get("prints") or ()),
        **_fields(data),
    )


def check_overrides(root: Path, overrides: Mapping[str, object]) -> None:
    """Check layout fields given in place of a layout's own, as its record would be.

    Args:
        root: Vault root, whose Reference schema checks the fields.
        overrides: Fields among OVERRIDES, in frontmatter form.

    Raises:
        ValueError: A field is not among OVERRIDES, the vault has no
            Reference schema, or a value fails it.
    """
    unknown = sorted(set(overrides) - set(OVERRIDES))
    if unknown:
        raise ValueError(f"cannot override {', '.join(unknown)}")
    record = Record(
        root / LAYOUT_DIRECTORY / "overrides.md",
        Frontmatter({"type": "[[Reference]]", "subtype": "Layout", **overrides}),
        Body(""),
    )
    schema, diagnostics = select_schema(record, root)
    if schema is not None:
        diagnostics = schema.validate(record)
    if diagnostics:
        failure = diagnostics[0]
        _, _, path = failure.field.partition(".")
        name = path.partition(".")[0]
        raise ValueError(
            f"--{name.replace('_', '-')}: {failure.message}"
            if name
            else failure.message
        )


def override(layout: Layout, overrides: Mapping[str, object]) -> Layout:
    """Replace some of a layout's fields.

    Args:
        layout: The layout.
        overrides: Fields that check_overrides accepts, in frontmatter form.

    Returns:
        Layout: The layout with those fields in place of its own; its name
            and prints are unchanged.
    """
    return replace(layout, **_fields(overrides))


def read_layouts(root: Path) -> dict[str, Layout]:
    """Read every layout in a vault.

    Args:
        root: Vault root.

    Returns:
        dict[str, Layout]: Layout name to layout, in path order, for each
            layout in reference/layouts/ and its subfolders. Empty when the
            folder does not exist.

    Raises:
        ValueError: A record cannot be parsed, or a layout fails the vault's
            Reference schema.
        OSError: A file cannot be read.
    """
    return {
        record.path.stem: parse_layout(record)
        for record in read_subtype_records(root, LAYOUT_DIRECTORY, "Layout")
    }


def choose_layout(
    layouts: dict[str, Layout], record: Record, name: str | None = None
) -> Layout:
    """Choose the layout a record prints in.

    Args:
        layouts: The vault's layouts, by name.
        record: The record to print.
        name: The layout to use, or None to choose the one that prints the
            record's type and subtype.

    Returns:
        Layout: The named layout, or the only layout that applies to the
            record, or the defaults when no name is given and none applies.

    Raises:
        ValueError: No layout has the name, or several apply.
    """
    if name is not None:
        if name not in layouts:
            raise ValueError(f"no layout {name} in {LAYOUT_DIRECTORY}/")
        return layouts[name]
    kind = record.frontmatter.type
    subtype = record.frontmatter.get("subtype")
    matches = [
        layout for layout in layouts.values() if layout.applies_to(kind, subtype)
    ]
    if len(matches) > 1:
        names = ", ".join(layout.name for layout in matches)
        raise ValueError(f"layouts {names} all apply; choose one with --layout")
    return matches[0] if matches else Layout()
