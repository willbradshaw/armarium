"""Print records as player handouts: one page each, in a PDF."""

import io
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from html import escape
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token
from PIL import Image as PILImage
from PIL import UnidentifiedImageError
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFError, TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    KeepInFrame,
    ListFlowable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from armarium.layout import POINTS, Layout, choose_layout, read_layouts
from armarium.lib import WIKILINK, wikilink_text
from armarium.parse import Record
from armarium.trace import locate

PAGES = {"letter": LETTER, "a4": A4}
# The gap between the text and the picture.
GAP = 0.25 * POINTS["in"]
# Room left unused below the picture, against rounding in measurement.
SLACK = 0.25 * POINTS["in"]
# The mark's size as a multiple of the title's.
MARK_SCALE = 1.4
# Font sizes are tried to this precision, in points.
STEP = 0.5
# A height no page reaches, for measuring text without a limit.
UNBOUNDED = 1e6
# Characters around a link's text while its Markdown is converted; both lie in
# Unicode's private use area, so no record's text holds them.
LINK_START, LINK_END = "", ""
# An embedded file, such as ![[Ring.webp|500]], which a handout leaves out.
EMBED = re.compile(r"!\[\[[^\[\]\r\n]+\]\]")
MARKDOWN = MarkdownIt("commonmark").enable("table")


@dataclass(frozen=True)
class Page:
    """One record's page in a handout.

    Attributes:
        record: The record's vault-relative path.
        layout: The layout it printed in, or "" for the defaults.
        text_size: The font size its text took, in points.
        picture: The height its picture took, in inches, or None without one.
        notes: What a reader should know about the page, such as text that
            had to shrink below the layout's smallest size.
    """

    record: str
    layout: str
    text_size: float
    picture: float | None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Handout:
    """A written handout.

    Attributes:
        vault: The vault root.
        output: The PDF written.
        pages: Each record's page, in print order.
    """

    vault: Path
    output: Path
    pages: tuple[Page, ...]


@dataclass(frozen=True)
class Font:
    """A font registered for printing.

    Attributes:
        name: Its registered name.
        faces: Whether it has bold and italic faces; without them, emphasis
            is underlined.
    """

    name: str
    faces: bool


def register_font(spec: str, root: Path) -> Font:
    """Make a layout's font available to print with.

    Args:
        spec: A standard PDF font's name, such as Times-Roman, or the path of
            a TrueType font file, absolute or relative to the vault root.
        root: Vault root.

    Returns:
        Font: The font. A standard font of the Times, Helvetica or Courier
            families has bold and italic faces; a font file is one face.

    Raises:
        ValueError: The font is neither a standard font nor a usable
            TrueType font file.
    """
    if spec in pdfmetrics.standardFonts:
        return Font(spec, spec.split("-")[0] in {"Times", "Helvetica", "Courier"})
    path = Path(spec).expanduser()
    path = path if path.is_absolute() else root / path
    if not path.is_file():
        raise ValueError(f"font {spec} is neither a standard font nor a file")
    name = f"armarium:{path}"
    if name not in pdfmetrics.getRegisteredFontNames():
        try:
            pdfmetrics.registerFont(TTFont(name, str(path)))
        except TTFError as exc:
            raise ValueError(f"cannot use font {spec}: {exc}") from exc
        pdfmetrics.registerFontFamily(
            name, normal=name, bold=name, italic=name, boldItalic=name
        )
    return Font(name, False)


@dataclass
class _Inline:
    """Turns a Markdown paragraph's inline tokens into ReportLab markup.

    Attributes:
        layout: The layout setting how link text looks.
        font: The font, which decides how emphasis looks.
    """

    layout: Layout
    font: Font
    _in_link: bool = False

    def convert(self, tokens: Sequence[Token]) -> str:
        """Convert inline tokens to markup.

        Args:
            tokens: An inline token's children.

        Returns:
            str: ReportLab paragraph markup.
        """
        bold, italic = ("b", "i") if self.font.faces else ("u", "u")
        tags = {
            "strong_open": f"<{bold}>",
            "strong_close": f"</{bold}>",
            "em_open": f"<{italic}>",
            "em_close": f"</{italic}>",
            "softbreak": " ",
            "hardbreak": "<br/>",
        }
        parts: list[str] = []
        for token in tokens:
            if token.type in {"text", "code_inline"}:
                parts.append(self._text(token.content))
            elif token.type in tags:
                parts.append(tags[token.type])
        return "".join(parts)

    def _text(self, text: str) -> str:
        """Escape text, marking up the link text inside it."""
        parts: list[str] = []
        for piece in re.split(f"([{LINK_START}{LINK_END}])", text):
            if piece in {LINK_START, LINK_END}:
                self._in_link = piece == LINK_START
                if self.layout.underline_links:
                    parts.append("<u>" if self._in_link else "</u>")
            elif piece:
                lower = self._in_link and self.layout.lowercase_links
                parts.append(escape(piece.lower() if lower else piece, quote=False))
        return "".join(parts)


def _close(tokens: Sequence[Token], start: int) -> int:
    """Find the token that closes the one opened at start."""
    depth = 0
    for position in range(start, len(tokens)):
        depth += tokens[position].nesting
        if depth == 0:
            return position
    return len(tokens) - 1


def _children(
    tokens: Sequence[Token], start: int, end: int
) -> Iterator[tuple[int, int]]:
    """Yield the span of each block between two positions, opener to closer."""
    position = start
    while position < end:
        close = _close(tokens, position) if tokens[position].nesting == 1 else position
        yield position, close
        position = close + 1


def _flowables(
    tokens: Sequence[Token],
    start: int,
    end: int,
    style: ParagraphStyle,
    inline: _Inline,
    width: float,
) -> list[Flowable]:
    """Convert a run of Markdown block tokens to flowables.

    Args:
        tokens: Every token of the Markdown.
        start: The first token of the run.
        end: The position after its last token.
        style: The style for text.
        inline: The converter for each block's inline tokens.
        width: The width the blocks fill, in points.

    Returns:
        list[Flowable]: Paragraphs, lists and tables. Code prints as text;
            horizontal rules and HTML are left out.
    """
    flowables: list[Flowable] = []
    for first, last in _children(tokens, start, end):
        token = tokens[first]
        kind = token.type.removesuffix("_open")
        if kind in {"paragraph", "heading"}:
            text = inline.convert(tokens[first + 1].children or [])
            flowables.append(
                Paragraph(f"<b>{text}</b>" if kind == "heading" else text, style)
            )
        elif kind in {"fence", "code_block"}:
            lines = escape(token.content.rstrip("\n"), quote=False).split("\n")
            flowables.append(Paragraph("<br/>".join(lines), style))
        elif kind in {"bullet_list", "ordered_list"}:
            items = [
                _flowables(tokens, item + 1, close, style, inline, width)
                or [Spacer(0, 0)]
                for item, close in _children(tokens, first + 1, last)
            ]
            flowables.append(
                ListFlowable(
                    items,
                    bulletType="1" if kind == "ordered_list" else "bullet",
                    start=int(token.attrGet("start") or 1)
                    if kind == "ordered_list"
                    else None,
                    bulletFontName=style.fontName,
                    bulletFontSize=style.fontSize,
                    leftIndent=style.fontSize * 1.2,
                    spaceAfter=style.spaceAfter,
                )
            )
        elif kind == "blockquote":
            flowables += _flowables(tokens, first + 1, last, style, inline, width)
        elif kind == "table":
            rows = [
                [
                    Paragraph(inline.convert(tokens[cell + 1].children or []), style)
                    for cell, _ in _children(tokens, row + 1, row_end)
                ]
                for row, row_end in _rows(tokens, first, last)
            ]
            columns = max(len(row) for row in rows)
            table = Table(rows, colWidths=[width / columns] * columns)
            table.setStyle(
                TableStyle(
                    [
                        ("LINEBELOW", (0, 0), (-1, 0), 0.5, "black"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            flowables.append(table)
    return flowables


def _rows(tokens: Sequence[Token], start: int, end: int) -> Iterator[tuple[int, int]]:
    """Yield the span of each row of a table, header first."""
    for position in range(start, end):
        if tokens[position].type == "tr_open":
            yield position, _close(tokens, position)


def body(
    markdown: str, layout: Layout, font: Font, size: float, width: float
) -> list[Flowable]:
    """Lay out a callout's text at one font size.

    Args:
        markdown: The text.
        layout: The layout setting line spacing and link text.
        font: The font to print in.
        size: The font size, in points.
        width: The width the text fills, in points.

    Returns:
        list[Flowable]: The text's paragraphs, lists and tables. Embedded
            files are left out, and each link prints as its text.
    """
    marked = WIKILINK.sub(
        lambda match: f"{LINK_START}{wikilink_text(match[1])}{LINK_END}",
        EMBED.sub("", markdown),
    )
    tokens = MARKDOWN.parse(marked)
    style = ParagraphStyle(
        "text",
        fontName=font.name,
        fontSize=size,
        leading=size * layout.line_spacing,
        spaceAfter=size * 0.35,
        alignment=TA_LEFT,
    )
    return _flowables(tokens, 0, len(tokens), style, _Inline(layout, font), width)


def height(flowables: Sequence[Flowable], width: float) -> float:
    """Measure flowables stacked at a width.

    Args:
        flowables: What to measure.
        width: The width they fill, in points.

    Returns:
        float: Their total height with the space around each, in points.
    """
    return sum(
        flowable.wrap(width, UNBOUNDED)[1]
        + flowable.getSpaceBefore()
        + flowable.getSpaceAfter()
        for flowable in flowables
    )


def fit(
    markdown: str, layout: Layout, font: Font, width: float, target: float
) -> tuple[float, float]:
    """Choose the largest font size at which text fits its space.

    Args:
        markdown: The text.
        layout: The layout giving the range of sizes.
        font: The font to print in.
        width: The width the text fills, in points.
        target: The height the text should fit within, in points.

    Returns:
        tuple[float, float]: The size, to the nearest half point, and the
            text's height at it. The size is the layout's largest when the
            text fits at it, and its smallest when it fits at none.

    Raises:
        ValueError: The layout's smallest size is larger than its largest.
    """
    low, high = layout.min_text_size, layout.max_text_size
    if low > high:
        raise ValueError(
            f"layout {layout.name}: min_text_size {low} is larger than "
            f"max_text_size {high}"
        )

    def measured(size: float) -> float:
        return height(body(markdown, layout, font, size, width), width)

    if measured(high) <= target:
        return high, measured(high)
    steps = int((high - low) / STEP)
    best = low
    first, last = 1, steps
    while first <= last:
        middle = (first + last) // 2
        size = low + middle * STEP
        if measured(size) <= target:
            best, first = size, middle + 1
        else:
            last = middle - 1
    return best, measured(best)


class Corner(Flowable):
    """A mark printed in the top right corner of the space below it.

    Takes no room of its own; the title beside it leaves room for it.
    """

    def __init__(self, text: str, font: str, size: float) -> None:
        """Hold the mark.

        Args:
            text: The mark.
            font: The registered font to print it in.
            size: Its font size, in points.
        """
        super().__init__()
        self.text, self.font, self.size = text, font, size

    def wrap(
        self, available_width: float, available_height: float
    ) -> tuple[float, float]:
        """Take the full width and no height."""
        self.width = available_width
        return 0, 0

    def draw(self) -> None:
        """Print the mark against the right edge, its top at the space's top."""
        self.canv.setFont(self.font, self.size)
        self.canv.drawRightString(self.width, -self.size * 0.8, self.text)


def _picture(root: Path, record: Record) -> Path | None:
    """Find the file a record's image field names, if any.

    Raises:
        ValueError: The field names no file in the vault.
    """
    value = record.frontmatter.get("image")
    if value is None or value == "":
        return None
    path = root / str(value)
    if not isinstance(value, str) or not path.is_file():
        raise ValueError(f"image {value} is not a file in the vault")
    return path


def page(root: Path, record: Record, layout: Layout) -> tuple[list[Flowable], Page]:
    """Lay out one record's page.

    Args:
        root: Vault root.
        record: The record to print.
        layout: The layout to print it in.

    Returns:
        tuple[list[Flowable], Page]: The page's flowables, and an account of
            it.

    Raises:
        ValueError: The record has no text in the layout's callout, its
            image names no readable picture, or the layout's font cannot be
            used.
    """
    relative = record.path.relative_to(root).as_posix()
    markdown = record.body.callout(layout.callout)
    if not markdown:
        raise ValueError(f"{relative} has no [!{layout.callout}] text to print")
    font = register_font(layout.font, root)
    page_width, page_height = PAGES[layout.page]
    width = page_width - 2 * layout.margin
    room = page_height - 2 * layout.margin - SLACK
    flowables: list[Flowable] = []
    notes: list[str] = []

    if layout.title:
        title_style = ParagraphStyle(
            "title",
            fontName=font.name,
            fontSize=layout.title_size,
            leading=layout.title_size * 1.15,
            spaceAfter=layout.title_size * 0.15,
        )
        mark = layout.mark
        if mark is not None and record.frontmatter.get(mark.field) is True:
            size = layout.title_size * MARK_SCALE
            flowables.append(Corner(mark.text, font.name, size))
            title_style.rightIndent = (
                pdfmetrics.stringWidth(mark.text, font.name, size)
                + layout.title_size * 0.25
            )
        title = Paragraph(escape(record.path.stem, quote=False), title_style)
        flowables.append(title)
        room -= height([title], width)

    picture = _picture(root, record)
    if picture is None:
        target = room
    else:
        room -= GAP
        target = (1 - layout.image_share) * room
    size, text_height = fit(markdown, layout, font, width, target)
    text = body(markdown, layout, font, size, width)
    if text_height > room:
        notes.append(f"its text overflows at {size:g}pt and was shrunk to fit")
        flowables.append(KeepInFrame(width, room, text, mode="shrink"))
        text_height = room
    else:
        flowables += text

    shown: float | None = None
    if picture is not None:
        try:
            with PILImage.open(picture) as source:
                picture_width, picture_height = source.size
        except (OSError, UnidentifiedImageError) as exc:
            raise ValueError(f"cannot read image {picture.name}: {exc}") from exc
        space = room - text_height
        shown_height = min(space, width * picture_height / picture_width)
        if shown_height <= 0:
            notes.append("its text leaves no room for its picture")
        else:
            image = Image(
                str(picture),
                shown_height * picture_width / picture_height,
                shown_height,
            )
            image.hAlign = "CENTER"
            flowables += [Spacer(0, GAP), image]
            shown = round(shown_height / POINTS["in"], 2)
    flowables.append(PageBreak())
    return flowables, Page(relative, layout.name, size, shown, tuple(notes))


def write(
    story: list[Flowable], output: Path, size: tuple[float, float], margin: float
) -> bytes:
    """Render flowables to PDF bytes."""
    buffer = io.BytesIO()
    width, page_height = size
    frame = Frame(
        margin,
        margin,
        width - 2 * margin,
        page_height - 2 * margin,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    document = BaseDocTemplate(
        buffer,
        pagesize=size,
        pageTemplates=[PageTemplate(frames=[frame])],
        title=output.stem,
        creator="Armarium",
    )
    document.build(story)
    return buffer.getvalue()


def handout(
    records: Sequence[Path],
    output: Path,
    vault: Path | None = None,
    *,
    layout: str | None = None,
    overwrite: bool = False,
) -> Handout:
    """Print records as a handout: one page each, in order, in one PDF.

    Each page holds the record's name, the text of the callout its layout
    names, rules by default, and its picture. The layout is the one that
    prints the record's kind, or the named one, or the defaults. The text
    takes the largest size at which it fits its share of the page, and the
    picture the room left.

    Args:
        records: The records' paths. With a vault, relative ones are taken
            from the vault root; without one, from the working directory.
        output: The PDF to write, relative to the working directory.
        vault: Vault root, or None to discover it from the first record.
        layout: The layout in reference/layouts/ to print every record in,
            or None to choose one per record.
        overwrite: Whether to replace an existing file at output.

    Returns:
        Handout: The vault, the PDF and an account of each page.

    Raises:
        ValueError: A record is not a Markdown record in the vault or has no
            text to print, a layout cannot be read or chosen, the output is not
            a .pdf path or exists without overwrite, or a picture or font
            cannot be used.
        OSError: A file cannot be read or the PDF cannot be written.
    """
    if not records:
        raise ValueError("name at least one record to print")
    if output.suffix.lower() != ".pdf":
        raise ValueError(f"{output} is not a .pdf path")
    if output.exists() and not overwrite:
        raise ValueError(f"{output} exists; pass --overwrite to replace it")
    root: Path | None = None
    parsed: list[Record] = []
    for path in records:
        found, located = locate(path, vault)
        if root is None:
            root = found
        elif found != root:
            raise ValueError(f"{path} is not in the vault {root}")
        if located.suffix != ".md":
            raise ValueError(f"{located} is not a Markdown record")
        record, diagnostics = Record.parse(located, found)
        if record is None:
            raise ValueError(f"cannot parse {path}: {diagnostics[0].message}")
        parsed.append(record)
    assert root is not None
    layouts = read_layouts(root)
    chosen = [choose_layout(layouts, record, layout) for record in parsed]
    sizes = {(item.page, item.margin) for item in chosen}
    if len(sizes) > 1:
        raise ValueError("the layouts differ in page size or margin; print them apart")
    page_size, margin = sizes.pop()
    story: list[Flowable] = []
    pages: list[Page] = []
    for record, choice in zip(parsed, chosen, strict=True):
        flowables, account = page(root, record, choice)
        story += flowables
        pages.append(account)
    data = write(story[:-1], output, PAGES[page_size], margin)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return Handout(root, output, tuple(pages))
