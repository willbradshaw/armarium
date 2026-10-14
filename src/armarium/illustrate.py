"""Illustrate a record: assemble the prompt for its picture, and take the
picture into the vault as its image within a size budget."""

import io
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml
from PIL import Image, ImageChops, ImageOps, UnidentifiedImageError

from armarium.lib import WIKILINK
from armarium.parse import Frontmatter, Record
from armarium.style import MAX_BYTES, MAX_EDGE, Style, art_directory, choose_style
from armarium.trace import locate

FIELD = "image"
# The field holding a record's art direction.
VISUAL = "visual"
# The first line of the callout holding a record's rules text.
RULES = re.compile(r"\[!rules\][+-]?(?:[ \t].*)?", re.IGNORECASE)
# Emphasis markers around a run of text.
EMPHASIS = re.compile(r"(\*{1,3}|_{1,3})(.+?)\1")
# Each long edge tried is this fraction of the one before, rounded down to
# ten pixels, and none is tried below MIN_EDGE.
EDGE_STEP = 0.9
MIN_EDGE = 350
QUALITIES = (80, 70, 60)
# At and below this edge, lower qualities are tried before a smaller size:
# shrinking further starts to show, while these qualities barely differ.
QUALITY_FLOOR_EDGE = 450
# Encoder effort: higher methods cost far more time for a few percent fewer
# bytes.
METHOD = 4
# Border pixels within this distance of the corner's colour, on every band,
# are trimmed.
TRIM_FUZZ = 3
# Black opacity is all alpha, which WebP keeps lossless unless told otherwise,
# at about three times the bytes. Compressed this hard it still shows no
# banding, and the bytes saved buy a larger image.
OPACITY_QUALITY = 20


@dataclass(frozen=True)
class Illustration:
    """A picture taken into a vault as a record's image.

    Attributes:
        vault: The vault root.
        record: The record whose image field now names the picture.
        image: The written image's vault-relative path, as the field holds it.
        edge: The written image's long edge, in pixels.
        size: The written image's size, in bytes.
        replaced: The field's previous value when it named another image,
            otherwise None.
        style: The style whose settings were used, or None.
    """

    vault: Path
    record: Path
    image: str
    edge: int
    size: int
    replaced: str | None
    style: str | None = None


def edges(max_edge: int) -> tuple[int, ...]:
    """List the long-edge sizes to try, largest first.

    Args:
        max_edge: The largest long edge allowed, in pixels.

    Returns:
        tuple[int, ...]: The largest allowed edge, then each EDGE_STEP of the
        one before, rounded down to ten pixels, down to MIN_EDGE.
    """
    sizes = [max_edge]
    while (edge := int(sizes[-1] * EDGE_STEP) // 10 * 10) >= MIN_EDGE:
        sizes.append(edge)
    return tuple(sizes)


def _trimmed(img: "Image.Image") -> "Image.Image":
    """Crop near-uniform borders, taking the corner pixel as the border colour.

    Args:
        img: The image to crop.

    Returns:
        Image.Image: The cropped image, or the whole image when it is uniform.
    """
    background = Image.new(img.mode, img.size, img.getpixel((0, 0)))
    bands = ImageChops.difference(img, background).split()
    combined = bands[0]
    for band in bands[1:]:
        combined = ImageChops.lighter(combined, band)
    bbox = combined.point(lambda value: 255 if value > TRIM_FUZZ else 0).getbbox()
    return img.crop(bbox) if bbox else img


def _on_white(img: "Image.Image") -> "Image.Image":
    """Lay an image on a white ground.

    Args:
        img: The image, with or without transparency.

    Returns:
        Image.Image: The image in RGB, white wherever it was clear.
    """
    ground = Image.new("RGBA", img.size, "white")
    ground.alpha_composite(img.convert("RGBA"))
    return ground.convert("RGB")


def _as_opacity(img: "Image.Image") -> "Image.Image":
    """Turn a drawing on white into black opacity on a transparent ground.

    The result is black throughout and as opaque as the drawing is dark: white
    is clear, and a grey wash lets the page show through.

    Args:
        img: The drawing, on a white ground.

    Returns:
        Image.Image: The drawing in RGBA.
    """
    art = Image.new("RGBA", img.size, "black")
    art.putalpha(ImageOps.invert(img.convert("L")))
    return art


def encode(
    source: Path,
    *,
    max_bytes: int = MAX_BYTES,
    max_edge: int = MAX_EDGE,
    opacity: bool = False,
) -> tuple[bytes, int]:
    """Encode a picture as a WebP within a byte budget.

    Near-uniform borders are trimmed, then the long edge steps down through
    `edges` until the WebP fits, never enlarging the picture. At and below
    QUALITY_FLOOR_EDGE each of QUALITIES is tried before a smaller size.
    Transparency is kept and metadata dropped.

    Args:
        source: Picture in any format Pillow reads.
        max_bytes: The largest WebP allowed, in bytes.
        max_edge: The largest long edge allowed, in pixels.
        opacity: Store a monochrome drawing on white as black opacity on a
            transparent ground.

    Returns:
        tuple[bytes, int]: The WebP and its long edge in pixels.

    Raises:
        ValueError: The source is not a picture Pillow reads, or does not fit
            the budget at the smallest size and lowest quality.
        OSError: The source cannot be read.
    """
    try:
        with Image.open(source) as opened:
            img = opened.copy()
    except UnidentifiedImageError as exc:
        raise ValueError(f"{source} is not a picture Pillow can read") from exc
    if img.mode not in ("RGB", "RGBA"):
        alpha = "A" in img.getbands() or "transparency" in img.info
        img = img.convert("RGBA" if alpha else "RGB")
    if opacity and img.mode == "RGBA":
        # The drawing's darkness is read from a white ground.
        img = _on_white(img)
    img = _trimmed(img)
    options = {"alpha_quality": OPACITY_QUALITY} if opacity else {}
    for edge in edges(max_edge):
        scaled = img.copy()
        scaled.thumbnail((edge, edge), Image.Resampling.LANCZOS)
        if opacity:
            scaled = _as_opacity(scaled)
        qualities = QUALITIES if edge <= QUALITY_FLOOR_EDGE else QUALITIES[:1]
        for quality in qualities:
            buffer = io.BytesIO()
            scaled.save(buffer, "WEBP", quality=quality, method=METHOD, **options)
            if buffer.tell() <= max_bytes:
                return buffer.getvalue(), max(scaled.size)
    raise ValueError(
        f"{source} does not fit in {max_bytes} bytes even at the smallest size "
        "and lowest quality"
    )


def set_field(text: str, key: str, value: str) -> str:
    """Set one top-level frontmatter field, leaving every other line as it is.

    The field's line, with any indented lines continuing it, is replaced; an
    absent field is added at the end of the frontmatter.

    Args:
        text: Whole text of a record.
        key: Top-level field name.
        value: Text the field should hold.

    Returns:
        str: The record's text with the field set.

    Raises:
        ValueError: The record has no frontmatter, or the field cannot be set
            without changing another field.
        yaml.YAMLError: The frontmatter is invalid YAML.
    """
    frontmatter, length = Frontmatter.parse(text)
    if not length:
        raise ValueError("record has no frontmatter")
    lines = text.splitlines(keepends=True)
    newline = "\r\n" if lines[0].endswith("\r\n") else "\n"
    dumped = yaml.safe_dump({key: value}, allow_unicode=True, width=1 << 16)
    line = dumped.rstrip("\n") + newline
    start = next(
        (
            number
            for number in range(1, length - 1)
            if re.match(rf"{re.escape(key)}[ \t]*:", lines[number])
        ),
        length - 1,
    )
    end = start
    if start < length - 1:
        end += 1
        while end < length - 1 and lines[end][:1] in (" ", "\t", "-"):
            end += 1
    updated = "".join(lines[:start]) + line + "".join(lines[end:])
    try:
        unchanged = dict(Frontmatter.parse(updated)[0]) == {**frontmatter, key: value}
    except yaml.YAMLError, ValueError:
        unchanged = False
    if not unchanged:
        raise ValueError(
            f"cannot set {key} without changing other fields; set it by hand"
        )
    return updated


def _plain(text: str) -> str:
    """Turn Markdown into plain prose: links become their text, emphasis goes.

    Args:
        text: Markdown text.

    Returns:
        str: The text with each wikilink replaced by its display text, or
            else by its target's name, and emphasis markers removed.
    """

    def label(match: re.Match[str]) -> str:
        target, _, alias = match.group(1).partition("|")
        return alias or target.partition("#")[0].rsplit("/", 1)[-1]

    return EMPHASIS.sub(r"\2", WIKILINK.sub(label, text)).strip()


def rules_text(record: Record) -> str:
    """Read the rules callout that opens a record such as Gear, as plain prose.

    Args:
        record: The record.

    Returns:
        str: The text of the record's first ``> [!rules]`` callout, without
            its marker line or quote markers, as `_plain` gives it; empty
            when the record has none.
    """
    for block in record.body.iter_blocks():
        if block.kind == "quote" and RULES.match(
            block.children[0].text if block.children else ""
        ):
            break
    else:
        return ""
    lines: list[str] = []
    for line in record.body.text.splitlines()[block.line - record.body.line + 1 :]:
        if not line.lstrip().startswith(">"):
            break
        lines.append(re.sub(r"^\s*>\s?", "", line))
    return _plain("\n".join(lines))


def build_prompt(style: Style, record: Record) -> str:
    """Assemble what an image model is told to paint a record's picture.

    Args:
        style: The style the picture is painted in.
        record: The record the picture illustrates.

    Returns:
        str: The style's prompt, the record's name, then its rules text and
            its visual field, each in a tagged block and left out when empty.
            The visual field is art direction, and outranks the rules text.
    """
    visual = record.frontmatter.get(VISUAL)
    parts = [style.prompt, "", f"<subject>{record.path.stem}</subject>"]
    for tag, text in (
        ("rules", rules_text(record)),
        ("visual", visual.strip() if isinstance(visual, str) else ""),
    ):
        if text:
            parts += ["", f"<{tag}>", text, f"</{tag}>"]
    return "\n".join(parts).strip()


def _read(record: Path, vault: Path | None) -> tuple[Path, Path, Record]:
    """Find and parse the record to illustrate.

    Args:
        record: The record's path. With a vault, a relative path is taken
            from the vault root; without one, from the working directory.
        vault: Vault root, or None to discover it from the record's location.

    Returns:
        tuple[Path, Path, Record]: The vault root, the record's path and the
            parsed record.

    Raises:
        ValueError: The record is not a Markdown file in a vault, or cannot
            be parsed.
    """
    root, path = locate(record, vault)
    if path.suffix != ".md":
        raise ValueError(f"{path} is not a Markdown record")
    parsed, diagnostics = Record.parse(path, root)
    if parsed is None:
        raise ValueError(f"cannot parse the record: {diagnostics[0].message}")
    return root, path, parsed


def prompt(record: Path, vault: Path | None = None, *, style: str | None = None) -> str:
    """Assemble the prompt for a record's picture, as `build_prompt` does.

    Args:
        record: The record to illustrate. With a vault, a relative path is
            taken from the vault root; without one, from the working directory.
        vault: Vault root, or None to discover it from the record's location.
        style: The style to paint in, or None to choose one by the record's
            type.

    Returns:
        str: The prompt.

    Raises:
        ValueError: The record is not a Markdown file in a vault or cannot be
            parsed, or there is no one style to paint in.
        OSError: A file cannot be read.
    """
    root, _, parsed = _read(record, vault)
    chosen = choose_style(root, parsed, style)
    if chosen is None:
        kind = parsed.frontmatter.type or "untyped"
        subtype = parsed.frontmatter.get("subtype")
        if isinstance(subtype, str):
            kind += f"/{subtype}"
        raise ValueError(
            f"no style illustrates {kind} records; choose one with --style"
        )
    return build_prompt(chosen, parsed)


def _destination(output: str | None, record: Path, directory: str) -> PurePosixPath:
    """Choose the vault-relative path an image is written to.

    Args:
        output: Path the user asked for, relative to the vault root, or None.
        record: The record being illustrated.
        directory: Vault-relative folder that art goes in by default.

    Returns:
        PurePosixPath: The asked-for path, or the record's name with .webp in
            the directory.

    Raises:
        ValueError: The path is not a .webp file inside the vault's assets/.
    """
    relative = PurePosixPath(output or f"{directory}/{record.stem}.webp")
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or relative.parts[:1] != ("assets",)
        or len(relative.parts) < 2
        or relative.suffix != ".webp"
    ):
        raise ValueError(f"{output} is not a .webp path inside the vault's assets/")
    return relative


def _write(path: Path, data: bytes) -> None:
    """Replace a file's contents in one step, creating missing directories.

    Args:
        path: File to write.
        data: Its new contents.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    except BaseException:
        os.unlink(temporary)
        raise


def ingest(
    record: Path,
    picture: Path,
    vault: Path | None = None,
    *,
    style: str | None = None,
    directory: str | None = None,
    output: str | None = None,
    max_bytes: int | None = None,
    max_edge: int | None = None,
    opacity: bool | None = None,
    overwrite: bool = False,
) -> Illustration:
    """Take a picture into a vault and name it in a record's image field.

    The picture is encoded as `encode` describes and written into the vault's
    assets/, and the record's image field is set to its vault-relative path.
    The style named, or else the only style that applies to the record,
    supplies the folder, budget and storage that options leave unset; without
    a style they take Style's defaults. Nothing is written when the picture
    cannot be encoded or the field cannot be set. The record is not validated
    here.

    Args:
        record: The record to illustrate. With a vault, a relative path is
            taken from the vault root; without one, from the working directory.
        picture: The picture to take in, in any format Pillow reads.
        vault: Vault root, or None to discover it from the record's location.
        style: The style to use, or None to choose one by the record's type.
        directory: Vault-relative folder inside assets/ to write into, or
            None for the style's.
        output: Vault-relative .webp path inside assets/ to write, or None for
            the record's name in the directory. It outranks directory.
        max_bytes: The largest image allowed, in bytes, or None for the
            style's.
        max_edge: The largest long edge allowed, in pixels, or None for the
            style's.
        opacity: Whether to store a monochrome drawing on white as black
            opacity on a transparent ground, or None for the style's choice.
        overwrite: Replace an existing file at the destination.

    Returns:
        Illustration: What was written.

    Raises:
        ValueError: The record is not a Markdown file in a vault, or cannot
            be parsed; no style or several apply as choose_style describes;
            the directory or destination is not allowed, or the destination
            already exists; or the picture cannot be encoded or the field set.
        OSError: A file cannot be read or written.
    """
    root, path, parsed = _read(record, vault)
    chosen = choose_style(root, parsed, style)
    settings = chosen or Style("", "")
    folder = settings.directory if directory is None else art_directory(directory)
    relative = _destination(output, path, folder)
    destination = root / relative
    if destination.is_dir() or destination.is_symlink():
        raise ValueError(f"{relative} is a directory or symlink")
    if destination.exists() and not overwrite:
        raise ValueError(f"{relative} already exists; pass --overwrite to replace it")
    data = path.read_bytes()
    bom = data.startswith(b"\xef\xbb\xbf")
    text = data.decode("utf-8-sig")
    image, edge = encode(
        picture,
        max_bytes=settings.max_bytes if max_bytes is None else max_bytes,
        max_edge=settings.max_edge if max_edge is None else max_edge,
        opacity=settings.opacity if opacity is None else opacity,
    )
    updated = set_field(text, FIELD, relative.as_posix())
    previous = parsed.frontmatter.get(FIELD)
    _write(destination, image)
    if updated != text:
        _write(path, updated.encode("utf-8-sig" if bom else "utf-8"))
    return Illustration(
        root,
        path,
        relative.as_posix(),
        edge,
        len(image),
        previous
        if isinstance(previous, str)
        and previous.strip()
        and previous != relative.as_posix()
        else None,
        None if chosen is None else chosen.name,
    )
