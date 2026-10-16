"""Read a vault's illustration styles: how each kind of art is made and stored."""

from dataclasses import dataclass
from pathlib import Path

from armarium.lib import DIRECTORY, find_files, parse_wikilink
from armarium.parse import Record
from armarium.schemas import select_schema

STYLE_DIRECTORY = "reference/styles"
ART_DIRECTORY = "assets/art"
MAX_BYTES = 100_000
MAX_EDGE = 1200


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
        references: Link targets of the images, or of the records whose
            image field names one, that show the style.
        sample: How many references to send with each candidate, drawn at
            random, or None to send them all with every request.
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


def art_directory(value: object) -> str:
    """Check a folder that art goes in.

    Args:
        value: The folder, as a style or option gives it.

    Returns:
        str: The folder, a vault-relative path inside assets/.

    Raises:
        ValueError: The value is not a folder inside assets/.
    """
    if (
        not isinstance(value, str)
        or DIRECTORY.fullmatch(value) is None
        or not value.startswith("assets/")
    ):
        raise ValueError("directory must be a folder inside assets/")
    return value


def is_style(record: Record) -> bool:
    """Say whether a record is a style: a Reference record of subtype Style.

    Args:
        record: Any parsed record.

    Returns:
        bool: Whether the record declares the Reference type and Style subtype.
    """
    return (
        record.frontmatter.type == "Reference"
        and record.frontmatter.get("subtype") == "Style"
    )


def parse_style(record: Record) -> Style:
    """Read a style from its record.

    Every field is optional; an absent or null field takes Style's default.
    The vault's Reference schema checks each field's form.

    Args:
        record: A style that satisfies the vault's Reference schema.

    Returns:
        Style: The style the record declares.

    Raises:
        ValueError: A reference is not a wikilink.
    """
    data = record.frontmatter
    return Style(
        record.path.stem,
        record.body.text.strip(),
        tuple(data.get("illustrates") or ()),
        data.get("directory") or ART_DIRECTORY,
        bool(data.get("opacity")),
        data.get("max_bytes") or MAX_BYTES,
        data.get("max_edge") or MAX_EDGE,
        tuple(parse_wikilink(link) for link in data.get("references") or ()),
        data.get("sample"),
    )


def read_styles(root: Path) -> dict[str, Style]:
    """Read every style in a vault.

    Args:
        root: Vault root.

    Returns:
        dict[str, Style]: Style name to style, in path order, for each style
            in reference/styles/ and its subfolders. Empty when the folder
            does not exist.

    Raises:
        ValueError: A record cannot be parsed, or a style fails the vault's
            Reference schema.
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
        if not is_style(record):
            continue
        schema, diagnostics = select_schema(record, root)
        if schema is not None:
            diagnostics = schema.validate(record)
        if diagnostics:
            failure = diagnostics[0]
            field = f"{failure.field}: " if failure.field else ""
            raise ValueError(f"{relative}: {field}{failure.message}")
        styles[path.stem] = parse_style(record)
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
