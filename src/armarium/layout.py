"""Read a vault's handout layouts: how each kind of record prints as a handout."""

import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from armarium.lib import matches_kind
from armarium.parse import Record
from armarium.schemas import read_subtype_records

LAYOUT_DIRECTORY = "reference/layouts"

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
    defaults = Layout()
    fields: dict[str, Any] = {
        name: data.get(name)
        for name in (
            "callout",
            "title",
            "page",
            "font",
            "title_size",
            "min_text_size",
            "max_text_size",
            "line_spacing",
            "image_share",
            "underline_links",
            "lowercase_links",
        )
        if data.get(name) is not None
    }
    mark = data.get("mark")
    margin = data.get("margin")
    return replace(
        defaults,
        name=record.path.stem,
        prints=tuple(data.get("prints") or ()),
        margin=defaults.margin if margin is None else points(margin),
        mark=None if mark is None else Mark(mark["field"], mark["text"]),
        **fields,
    )


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
