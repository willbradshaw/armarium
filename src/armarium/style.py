"""Read a vault's illustration styles: how each kind of art is made and stored."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from armarium.lib import DIRECTORY, find_files, parse_wikilink
from armarium.parse import Record

STYLE_DIRECTORY = "reference/styles"
ART_DIRECTORY = "assets/art"
MAX_BYTES = 100_000
MAX_EDGE = 1200

# A record kind a style illustrates: a type, or a type and subtype.
KIND = re.compile(r"[^/\s](?:[^/]*[^/\s])?(?:/[^/\s](?:[^/]*[^/\s])?)?")


@dataclass(frozen=True)
class Style:
    """How one kind of art is made and stored, as a style record declares it.

    Attributes:
        name: The style record's filename without .md.
        prompt: The record's body: what an image model is told about the style.
        illustrates: Record kinds the style applies to, each a type or
            ``Type/Subtype``, such as ``Content/Gear``.
        directory: Vault-relative folder inside assets/ that its art goes in.
        opacity: Whether its art is a drawing on white stored as black
            opacity on a transparent ground.
        max_bytes: The largest art file allowed, in bytes.
        max_edge: The largest long edge allowed, in pixels.
        references: Link targets of the files or records that show the style.
        sample: How many references to send with each picture, or None for
            all of them.
    """

    name: str
    prompt: str
    illustrates: tuple[str, ...] = ()
    directory: str = ART_DIRECTORY
    opacity: bool = False
    max_bytes: int = MAX_BYTES
    max_edge: int = MAX_EDGE
    references: tuple[str, ...] = ()
    sample: int | None = None

    def applies_to(self, kind: str | None, subtype: object) -> bool:
        """Say whether the style illustrates records of a type and subtype.

        Args:
            kind: The record's type name, or None for an untyped record.
            subtype: The record's subtype field, if any.

        Returns:
            bool: Whether the type, or the type and subtype, is among
                illustrates.
        """
        return kind is not None and (
            kind in self.illustrates
            or (isinstance(subtype, str) and f"{kind}/{subtype}" in self.illustrates)
        )


def _count(data: Mapping[str, Any], field: str) -> int | None:
    """Read an optional positive whole number from a style's frontmatter.

    Returns:
        int | None: The number, or None when the field is absent or null.

    Raises:
        ValueError: The field holds anything else.
    """
    value = data.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a whole number of at least 1")
    return value


def parse_style(record: Record) -> Style:
    """Read a style from its record.

    Every field is optional; an absent or null field takes Style's default.

    Args:
        record: A record in the vault's reference/styles/.

    Returns:
        Style: The style the record declares.

    Raises:
        ValueError: A field holds a value of the wrong form.
    """
    data = record.frontmatter
    illustrates = data.get("illustrates") or []
    if not isinstance(illustrates, list) or not all(
        isinstance(kind, str) and KIND.fullmatch(kind) for kind in illustrates
    ):
        raise ValueError(
            "illustrates must list record types, each a type or Type/Subtype"
        )
    directory = data.get("directory") or ART_DIRECTORY
    if (
        not isinstance(directory, str)
        or DIRECTORY.fullmatch(directory) is None
        or not directory.startswith("assets/")
    ):
        raise ValueError("directory must be a folder inside assets/")
    opacity = data.get("opacity")
    if opacity is not None and not isinstance(opacity, bool):
        raise ValueError("opacity must be true or false")
    references = data.get("references") or []
    if not isinstance(references, list):
        raise ValueError("references must list wikilinks")
    targets: list[str] = []
    for reference in references:
        try:
            targets.append(parse_wikilink(reference))
        except ValueError as exc:
            raise ValueError(f"references must list wikilinks: {exc}") from exc
    return Style(
        record.path.stem,
        record.body.text.strip(),
        tuple(illustrates),
        directory,
        bool(opacity),
        _count(data, "max_bytes") or MAX_BYTES,
        _count(data, "max_edge") or MAX_EDGE,
        tuple(targets),
        _count(data, "sample"),
    )


def read_styles(root: Path) -> dict[str, Style]:
    """Read every style in a vault.

    Args:
        root: Vault root.

    Returns:
        dict[str, Style]: Style name to style, in path order, for each
            Markdown file in reference/styles/ and its subfolders. Empty when
            the folder does not exist.

    Raises:
        ValueError: A style cannot be parsed, or declares a field wrongly.
        OSError: A file cannot be read.
    """
    directory = root / STYLE_DIRECTORY
    if not directory.is_dir() or directory.is_symlink():
        return {}
    styles: dict[str, Style] = {}
    for path in find_files(directory, ".md"):
        record, diagnostics = Record.parse(path, root)
        relative = path.relative_to(root).as_posix()
        if record is None:
            raise ValueError(f"{relative}: {diagnostics[0].message}")
        try:
            styles[path.stem] = parse_style(record)
        except ValueError as exc:
            raise ValueError(f"{relative}: {exc}") from exc
    return styles


def choose_style(root: Path, record: Record, name: str | None = None) -> Style | None:
    """Choose the style a record is illustrated in.

    Args:
        root: Vault root.
        record: The record to illustrate.
        name: The style to use, or None to choose the one that illustrates
            the record's type and subtype.

    Returns:
        Style | None: The named style, or the only style that applies to the
            record; None when no name is given and none applies.

    Raises:
        ValueError: No style has the name, several apply, or a style cannot
            be read.
        OSError: A file cannot be read.
    """
    styles = read_styles(root)
    if name is not None:
        if name not in styles:
            raise ValueError(f"no style {name} in {STYLE_DIRECTORY}/")
        return styles[name]
    kind = record.frontmatter.type
    subtype = record.frontmatter.get("subtype")
    matches = [style for style in styles.values() if style.applies_to(kind, subtype)]
    if len(matches) > 1:
        names = ", ".join(style.name for style in matches)
        raise ValueError(f"styles {names} all apply; choose one with --style")
    return matches[0] if matches else None
