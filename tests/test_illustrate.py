"""Pictures become budgeted WebP images that a record's image field names."""

import io
import os
import random
import shutil
from pathlib import Path, PurePosixPath

import pytest
from PIL import Image

from armarium import illustrate as module
from armarium.content import add_content
from armarium.illustrate import (
    Illustration,
    _as_opacity,
    _destination,
    _on_white,
    _plain,
    _read,
    _trimmed,
    _write,
    build_prompt,
    edges,
    encode,
    ingest,
    prompt,
    rules_text,
    set_field,
)
from armarium.parse import Frontmatter, Record
from armarium.style import ART_DIRECTORY, MAX_BYTES, MAX_EDGE, Style

STARTER = Path(__file__).resolve().parents[1] / "vaults/starter"


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    shutil.copytree(STARTER, root)
    add_content("Harness", "Gear", root, campaign=1)
    return root


def picture(path: Path, size: tuple[int, int], *, noise: bool = False) -> Path:
    """Save a flat red picture, or smooth colour noise, as a PNG."""
    img = Image.new("RGB", size, "red")
    if noise:
        generator = random.Random(1)
        pixels = bytes(generator.randrange(256) for _ in range(40 * 40 * 3))
        img = Image.frombytes("RGB", (40, 40), pixels).resize(
            size, Image.Resampling.BICUBIC
        )
    img.save(path)
    return path


def opened(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


def frontmatter(path: Path) -> Frontmatter:
    return Frontmatter.parse(path.read_text(encoding="utf-8-sig"))[0]


class TestEdges:
    @pytest.mark.parametrize(
        ("max_edge", "expected"),
        [
            (MAX_EDGE, (1200, 1080, 970, 870, 780, 700, 630, 560, 500, 450, 400, 360)),
            (720, (720, 640, 570, 510, 450, 400, 360)),
            (389, (389, 350)),
            (388, (388,)),
            (100, (100,)),
        ],
    )
    def test_steps_down_from_the_largest_edge(
        self, max_edge: int, expected: tuple[int, ...]
    ) -> None:
        assert edges(max_edge) == expected


class TestTrimmed:
    @pytest.mark.parametrize(
        ("border", "expected"),
        [
            ((255, 255, 255), (4, 2)),
            ((252, 254, 255), (4, 2)),
            ((240, 255, 255), (10, 9)),
        ],
    )
    def test_crops_borders_close_to_the_corner(
        self, border: tuple[int, int, int], expected: tuple[int, int]
    ) -> None:
        img = Image.new("RGB", (10, 10), "white")
        img.paste(Image.new("RGB", (4, 2), "black"), (3, 5))
        img.paste(Image.new("RGB", (10, 1), border), (0, 0))
        assert _trimmed(img).size == expected

    def test_keeps_a_uniform_image_whole(self) -> None:
        assert _trimmed(Image.new("RGB", (6, 3), "blue")).size == (6, 3)


class TestOnWhite:
    @pytest.mark.parametrize(
        ("pixel", "expected"),
        [((0, 0, 0, 0), (255, 255, 255)), ((200, 10, 10, 255), (200, 10, 10))],
    )
    def test_lays_the_image_on_white(
        self, pixel: tuple[int, int, int, int], expected: tuple[int, int, int]
    ) -> None:
        img = _on_white(Image.new("RGBA", (2, 2), pixel))
        assert img.mode == "RGB"
        assert img.getpixel((0, 0)) == expected


class TestAsOpacity:
    @pytest.mark.parametrize(("shade", "alpha"), [(255, 0), (0, 255), (128, 127)])
    def test_is_black_and_as_opaque_as_the_drawing_is_dark(
        self, shade: int, alpha: int
    ) -> None:
        img = _as_opacity(Image.new("RGB", (2, 2), (shade, shade, shade)))
        assert img.mode == "RGBA"
        assert img.getpixel((0, 0)) == (0, 0, 0, alpha)


class TestEncode:
    def test_writes_a_webp_without_enlarging(self, tmp_path: Path) -> None:
        data, edge = encode(picture(tmp_path / "a.png", (300, 200)))
        img = opened(data)
        assert (img.format, img.size, edge) == ("WEBP", (300, 200), 300)

    @pytest.mark.parametrize(("max_edge", "expected"), [(800, 800), (2000, 2000)])
    def test_keeps_within_the_largest_edge(
        self, tmp_path: Path, max_edge: int, expected: int
    ) -> None:
        source = picture(tmp_path / "a.png", (2400, 1200))
        data, edge = encode(source, max_edge=max_edge)
        assert edge == expected == max(opened(data).size)

    def test_shrinks_until_it_fits(self, tmp_path: Path) -> None:
        source = picture(tmp_path / "a.png", (1200, 1200), noise=True)
        data, edge = encode(source, max_bytes=50_000)
        assert len(data) <= 50_000 and edge == 780

    def test_keeps_transparency(self, tmp_path: Path) -> None:
        img = Image.new("RGBA", (40, 40), "red")
        img.paste(Image.new("RGBA", (38, 38), (0, 0, 0, 0)), (1, 1))
        img.save(tmp_path / "a.png")
        stored = opened(encode(tmp_path / "a.png")[0])
        assert stored.mode == "RGBA" and stored.getpixel((20, 20))[3] == 0

    @pytest.mark.parametrize(("mode", "expected"), [("L", "RGB"), ("LA", "RGBA")])
    def test_converts_other_modes(
        self, tmp_path: Path, mode: str, expected: str
    ) -> None:
        img = Image.new(mode, (20, 20), 0)
        img.paste(Image.new(mode, (18, 18), 128), (1, 1))
        img.save(tmp_path / "a.png")
        assert opened(encode(tmp_path / "a.png")[0]).mode == expected

    @pytest.mark.parametrize("inside", ["white", (0, 0, 0, 0)])
    def test_stores_a_drawing_as_black_opacity(
        self, tmp_path: Path, inside: str | tuple[int, ...]
    ) -> None:
        img = Image.new("RGBA", (96, 48), inside)
        for left in (8, 56):
            img.paste(Image.new("RGBA", (32, 32), "black"), (left, 8))
        img.save(tmp_path / "a.png")
        stored = opened(encode(tmp_path / "a.png", opacity=True)[0])
        assert stored.mode == "RGBA"
        assert stored.getpixel((16, 16))[3] > 240
        assert stored.getpixel((40, 16))[3] < 15

    def test_compresses_black_opacity(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = picture(tmp_path / "a.png", (300, 300), noise=True)
        compressed = encode(source, opacity=True)[0]
        monkeypatch.setattr(module, "OPACITY_QUALITY", 100)
        assert len(compressed) < len(encode(source, opacity=True)[0])

    @pytest.mark.parametrize(
        ("contents", "max_bytes", "message"),
        [(b"not a picture", 100_000, "not a picture"), (None, 50, "does not fit")],
    )
    def test_refuses(
        self, tmp_path: Path, contents: bytes | None, max_bytes: int, message: str
    ) -> None:
        source = tmp_path / "a.png"
        if contents is None:
            picture(source, (400, 400), noise=True)
        else:
            source.write_bytes(contents)
        with pytest.raises(ValueError, match=message):
            encode(source, max_bytes=max_bytes)


class TestSetField:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            (
                "---\ntype: x\nimage:\nsource: s\n---\nBody\n",
                "---\ntype: x\nimage: assets/a.webp\nsource: s\n---\nBody\n",
            ),
            (
                "---\nimage: >\n  old\n  text\n# kept\n---\n",
                "---\nimage: assets/a.webp\n# kept\n---\n",
            ),
            (
                "---\nimage:\n- a\n- b\ntags: [ 'x' ]\n---\n",
                "---\nimage: assets/a.webp\ntags: [ 'x' ]\n---\n",
            ),
            (
                "---\ntype: x\nimage_source: y\n---\nimage: body\n",
                "---\ntype: x\nimage_source: y\nimage: assets/a.webp\n---\nimage: body\n",
            ),
            (
                "---\r\ntype: x\r\n---\r\nBody\r\n",
                "---\r\ntype: x\r\nimage: assets/a.webp\r\n---\r\nBody\r\n",
            ),
        ],
    )
    def test_sets_only_the_field(self, text: str, expected: str) -> None:
        assert set_field(text, "image", "assets/a.webp") == expected

    def test_quotes_a_value_when_yaml_needs_it(self) -> None:
        updated = set_field("---\ntype: x\n---\n", "image", "assets/a: b.webp")
        assert Frontmatter.parse(updated)[0]["image"] == "assets/a: b.webp"

    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("Body\n", "no frontmatter"),
            ('---\n"image": old\n---\n', "without changing other fields"),
            ("---\nimage: &old x\nother: *old\n---\n", "without changing other fields"),
        ],
    )
    def test_refuses(self, text: str, message: str) -> None:
        with pytest.raises(ValueError, match=message):
            set_field(text, "image", "assets/a.webp")


def parsed(tmp_path: Path, text: str, name: str = "Lucky Ring") -> Record:
    path = tmp_path / f"{name}.md"
    path.write_text(text)
    record, _ = Record.parse(path, tmp_path)
    assert record is not None
    return record


class TestPlain:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("A [[Lucky Ring]] of [[content/Gold|gold]].", "A Lucky Ring of gold."),
            ("See [[Rules#Luck]] and [[rules/Luck#^b1]].", "See Rules and Luck."),
            (
                "**Bold**, *italic*, __strong__ and ***both***.",
                "Bold, italic, strong and both.",
            ),
            ("  plain  \n", "plain"),
        ],
    )
    def test_reads_as_prose(self, text: str, expected: str) -> None:
        assert _plain(text) == expected


class TestRulesText:
    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            (
                "> [!rules]\n> *Ring*, rare.\n>\n> Grants [[Luck]].\n\n## Notes\n",
                "Ring, rare.\n\nGrants Luck.",
            ),
            ("> [!RULES]- Folded\n> Text.\nAfter\n", "Text."),
            ("Intro.\n\n> [!rules]\n>   Indented.\n", "Indented."),
            ("> [!rules]\n>\n", ""),
            ("> [!note]\n> Not rules.\n", ""),
            ("> Just a quote.\n", ""),
            ("## Notes\n- N/A\n", ""),
        ],
    )
    def test_reads_the_rules_callout(
        self, tmp_path: Path, body: str, expected: str
    ) -> None:
        assert rules_text(parsed(tmp_path, "---\ntype: x\n---\n" + body)) == expected


class TestBuildPrompt:
    STYLE = Style("Gear", "Paint one item.")

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            (
                "---\nvisual: ' A ring on velvet. '\n---\n> [!rules]\n> Grants luck.\n",
                "Paint one item.\n\n<subject>Lucky Ring</subject>\n\n<rules>\nGrants luck."
                "\n</rules>\n\n<visual>\nA ring on velvet.\n</visual>",
            ),
            (
                "---\nvisual:\n---\n> [!rules]\n> Grants luck.\n",
                "Paint one item.\n\n<subject>Lucky Ring</subject>\n\n<rules>\nGrants luck.\n</rules>",
            ),
            (
                "---\nvisual: A ring.\n---\n## Notes\n",
                "Paint one item.\n\n<subject>Lucky Ring</subject>\n\n<visual>\nA ring.\n</visual>",
            ),
            (
                "---\nvisual: 3\n---\n",
                "Paint one item.\n\n<subject>Lucky Ring</subject>",
            ),
        ],
    )
    def test_assembles_the_parts(
        self, tmp_path: Path, text: str, expected: str
    ) -> None:
        assert build_prompt(self.STYLE, parsed(tmp_path, text)) == expected

    def test_a_style_without_text_opens_with_the_subject(self, tmp_path: Path) -> None:
        record = parsed(tmp_path, "---\ntype: x\n---\n")
        assert (
            build_prompt(Style("Bare", ""), record) == "<subject>Lucky Ring</subject>"
        )


class TestRead:
    def test_finds_and_parses_the_record(self, vault: Path) -> None:
        root, path, record = _read(TestIngest.RECORD, vault)
        assert (root, path) == (vault.resolve(), vault.resolve() / TestIngest.RECORD)
        assert record.frontmatter["subtype"] == "Gear"

    @pytest.mark.parametrize(
        ("relative", "text", "message"),
        [
            ("assets/notes.txt", "text", "is not a Markdown record"),
            ("content/Bad.md", "---\ntype: [\n---\n", "cannot parse the record: "),
        ],
    )
    def test_refuses_what_is_not_a_record(
        self, vault: Path, relative: str, text: str, message: str
    ) -> None:
        (vault / relative).write_text(text)
        with pytest.raises(ValueError, match=message):
            _read(Path(relative), vault)


class TestPrompt:
    def test_uses_the_style_that_applies(self, vault: Path) -> None:
        path = vault / TestIngest.RECORD
        path.write_text(
            path.read_text().replace("> [!rules]\n>\n", "> [!rules]\n> Hauls one.\n")
        )
        text = prompt(TestIngest.RECORD, vault)
        style = (
            (vault / "reference/styles/Gear.md")
            .read_text()
            .split("---\n", 2)[2]
            .strip()
        )
        assert (
            text
            == f"{style}\n\n<subject>Harness</subject>\n\n<rules>\nHauls one.\n</rules>"
        )

    def test_uses_the_style_named(self, vault: Path) -> None:
        (vault / "reference/styles/Ink.md").write_text(
            '---\ntype: "[[Reference]]"\n---\nInk it.\n'
        )
        assert (
            prompt(TestIngest.RECORD, vault, style="Ink")
            == "Ink it.\n\n<subject>Harness</subject>"
        )

    @pytest.mark.parametrize(
        ("relative", "text", "message"),
        [
            (
                "content/Port.md",
                '---\ntype: "[[Content]]"\nsubtype: Location\n---\n',
                "no style illustrates Content/Location records; choose one with --style",
            ),
            ("content/Loose.md", "Body\n", "no style illustrates untyped records"),
        ],
    )
    def test_needs_a_style(
        self, vault: Path, relative: str, text: str, message: str
    ) -> None:
        (vault / relative).write_text(text)
        with pytest.raises(ValueError, match=message):
            prompt(Path(relative), vault)


class TestDestination:
    @pytest.mark.parametrize(
        ("output", "expected"),
        [
            (None, "assets/art/gear/Lucky Ring.webp"),
            ("assets/gear/ring.webp", "assets/gear/ring.webp"),
            ("./assets/ring.webp", "assets/ring.webp"),
        ],
    )
    def test_chooses_a_path_in_assets(self, output: str | None, expected: str) -> None:
        record = Path("content/Lucky Ring.md")
        assert _destination(output, record, "assets/art/gear") == PurePosixPath(
            expected
        )

    @pytest.mark.parametrize(
        "output",
        [
            "/assets/ring.webp",
            "assets/../content/ring.webp",
            "content/ring.webp",
            "assets/ring.png",
            "assets.webp",
            "assets/.webp",
        ],
    )
    def test_refuses_a_path_outside_assets(self, output: str) -> None:
        with pytest.raises(ValueError, match="inside the vault's assets/"):
            _destination(output, Path("content/Lucky Ring.md"), ART_DIRECTORY)


class TestWrite:
    @pytest.mark.parametrize("existing", [None, b"old"])
    def test_replaces_the_contents(
        self, tmp_path: Path, existing: bytes | None
    ) -> None:
        path = tmp_path / "new/dir/a.webp"
        if existing is not None:
            path.parent.mkdir(parents=True)
            path.write_bytes(existing)
        _write(path, b"new")
        assert path.read_bytes() == b"new"
        assert os.listdir(path.parent) == ["a.webp"]

    def test_leaves_nothing_behind_on_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fail(*args: object) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(os, "replace", fail)
        with pytest.raises(OSError, match="disk full"):
            _write(tmp_path / "a.webp", b"new")
        assert os.listdir(tmp_path) == []


class TestIngest:
    RECORD = Path("campaigns/campaign_1/content/Harness.md")
    # The starter vault's Gear style puts Gear art in its own folder.
    IMAGE = "assets/art/gear/Harness.webp"

    @pytest.mark.parametrize("with_vault", [True, False])
    def test_writes_the_image_and_sets_the_field(
        self,
        vault: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        with_vault: bool,
    ) -> None:
        source = picture(tmp_path / "a.png", (300, 200))
        if with_vault:
            illustration = ingest(self.RECORD, source, vault)
        else:
            monkeypatch.chdir(vault)
            illustration = ingest(self.RECORD, source)
        record = vault.resolve() / self.RECORD
        data = (vault / self.IMAGE).read_bytes()
        assert illustration == Illustration(
            vault.resolve(), record, self.IMAGE, 300, len(data), None, "Gear"
        )
        assert frontmatter(record)["image"] == self.IMAGE
        assert opened(data).format == "WEBP"

    @pytest.mark.parametrize(
        ("previous", "output", "replaced"),
        [
            ("assets/old.webp", None, "assets/old.webp"),
            ("", None, None),
            (IMAGE, None, None),
            (IMAGE, "assets/new.webp", IMAGE),
        ],
    )
    def test_reports_the_image_it_replaces(
        self,
        vault: Path,
        tmp_path: Path,
        previous: str,
        output: str | None,
        replaced: str | None,
    ) -> None:
        path = vault / self.RECORD
        path.write_text(set_field(path.read_text(), "image", previous))
        source = picture(tmp_path / "a.png", (30, 20))
        illustration = ingest(self.RECORD, source, vault, output=output, overwrite=True)
        assert illustration.replaced == replaced

    def test_options_reach_the_encoder(
        self, vault: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[dict[str, object]] = []

        def encode(source: Path, **options: object) -> tuple[bytes, int]:
            calls.append(options)
            return b"webp", 4

        monkeypatch.setattr(module, "encode", encode)
        ingest(
            self.RECORD,
            tmp_path / "a.png",
            vault,
            max_bytes=10,
            max_edge=20,
            opacity=True,
        )
        assert calls == [{"max_bytes": 10, "max_edge": 20, "opacity": True}]
        assert (vault / self.IMAGE).read_bytes() == b"webp"

    @pytest.mark.parametrize(
        ("styles", "name", "image", "options", "style"),
        [
            (
                {},
                None,
                f"{ART_DIRECTORY}/Harness.webp",
                (MAX_BYTES, MAX_EDGE, False),
                None,
            ),
            (
                {
                    "Ink": "illustrates: [Content]\ndirectory: assets/ink\nopacity: true\n"
                    "max_bytes: 5000\nmax_edge: 600"
                },
                None,
                "assets/ink/Harness.webp",
                (5000, 600, True),
                "Ink",
            ),
            (
                {
                    "Ink": "directory: assets/ink\nopacity: true",
                    "Gear": "illustrates: [Content/Gear]",
                },
                "Ink",
                "assets/ink/Harness.webp",
                (MAX_BYTES, MAX_EDGE, True),
                "Ink",
            ),
            (
                {"Lore": "illustrates: [Content/Lore, Note]\ndirectory: assets/lore"},
                None,
                f"{ART_DIRECTORY}/Harness.webp",
                (MAX_BYTES, MAX_EDGE, False),
                None,
            ),
        ],
    )
    def test_a_style_supplies_the_settings(
        self,
        vault: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        styles: dict[str, str],
        name: str | None,
        image: str,
        options: tuple[int, int, bool],
        style: str | None,
    ) -> None:
        calls: list[tuple[object, ...]] = []

        def encode(source: Path, **kwargs: object) -> tuple[bytes, int]:
            calls.append(tuple(kwargs.values()))
            return b"webp", 4

        monkeypatch.setattr(module, "encode", encode)
        (vault / "reference/styles/Gear.md").unlink()
        for title, fields in styles.items():
            (vault / f"reference/styles/{title}.md").write_text(
                f'---\ntype: "[[Reference]]"\n{fields}\n---\nPaint it.\n'
            )
        illustration = ingest(self.RECORD, tmp_path / "a.png", vault, style=name)
        assert (illustration.image, illustration.style) == (image, style)
        assert calls == [options]

    def test_options_outrank_the_style(
        self, vault: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[tuple[object, ...]] = []

        def encode(source: Path, **kwargs: object) -> tuple[bytes, int]:
            calls.append(tuple(kwargs.values()))
            return b"webp", 4

        monkeypatch.setattr(module, "encode", encode)
        (vault / "reference/styles/Gear.md").write_text(
            '---\ntype: "[[Reference]]"\nillustrates: [Content/Gear]\n'
            "opacity: true\nmax_bytes: 5000\nmax_edge: 600\n---\n"
        )
        illustration = ingest(
            self.RECORD,
            tmp_path / "a.png",
            vault,
            directory="assets/other",
            max_bytes=9,
            max_edge=8,
            opacity=False,
        )
        assert calls == [(9, 8, False)]
        assert illustration.image == "assets/other/Harness.webp"

    @pytest.mark.parametrize(
        ("directory", "output", "image"),
        [
            ("assets/other", "assets/named.webp", "assets/named.webp"),
            ("assets/other", None, "assets/other/Harness.webp"),
        ],
    )
    def test_output_outranks_directory(
        self,
        vault: Path,
        tmp_path: Path,
        directory: str,
        output: str | None,
        image: str,
    ) -> None:
        source = picture(tmp_path / "a.png", (30, 20))
        illustration = ingest(
            self.RECORD, source, vault, directory=directory, output=output
        )
        assert illustration.image == image

    def test_refuses_a_directory_outside_assets(
        self, vault: Path, tmp_path: Path
    ) -> None:
        source = picture(tmp_path / "a.png", (30, 20))
        before = (vault / self.RECORD).read_text()
        with pytest.raises(ValueError, match="directory must be a folder inside"):
            ingest(self.RECORD, source, vault, directory="content")
        assert (vault / self.RECORD).read_text() == before

    @pytest.mark.parametrize(
        ("name", "extra", "message"),
        [
            ("Missing", None, "no style Missing in reference/styles/"),
            (
                None,
                "illustrates: [Content]",
                "styles Gear, Other all apply; choose one",
            ),
            (None, "max_edge: 0", "reference/styles/Other.md: max_edge must be"),
        ],
    )
    def test_refuses_without_one_usable_style(
        self,
        vault: Path,
        tmp_path: Path,
        name: str | None,
        extra: str | None,
        message: str,
    ) -> None:
        if extra is not None:
            (vault / "reference/styles/Other.md").write_text(
                f'---\ntype: "[[Reference]]"\n{extra}\n---\n'
            )
        source = picture(tmp_path / "a.png", (30, 20))
        with pytest.raises(ValueError, match=message):
            ingest(self.RECORD, source, vault, style=name)
        assert not (vault / self.IMAGE).exists()

    @pytest.mark.parametrize("overwrite", [False, True])
    def test_an_existing_image_needs_overwrite(
        self, vault: Path, tmp_path: Path, overwrite: bool
    ) -> None:
        (vault / self.IMAGE).parent.mkdir(parents=True)
        (vault / self.IMAGE).write_bytes(b"old")
        source = picture(tmp_path / "a.png", (30, 20))
        if overwrite:
            ingest(self.RECORD, source, vault, overwrite=True)
            assert (vault / self.IMAGE).read_bytes() != b"old"
        else:
            with pytest.raises(ValueError, match="already exists; pass --overwrite"):
                ingest(self.RECORD, source, vault)
            assert (vault / self.IMAGE).read_bytes() == b"old"

    def test_keeps_a_byte_order_mark(self, vault: Path, tmp_path: Path) -> None:
        path = vault / self.RECORD
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
        ingest(self.RECORD, picture(tmp_path / "a.png", (30, 20)), vault)
        assert path.read_bytes().startswith(b"\xef\xbb\xbf---\n")
        assert frontmatter(path)["image"] == self.IMAGE

    @pytest.mark.parametrize(
        ("setup", "message"),
        [
            ("not markdown", "is not a Markdown record"),
            ("directory", "is a directory or symlink"),
            ("not a picture", "is not a picture"),
            ("invalid yaml", "cannot parse the record"),
            ("unsettable", "without changing other fields"),
        ],
    )
    def test_writes_nothing_when_it_cannot_ingest(
        self,
        vault: Path,
        tmp_path: Path,
        setup: str,
        message: str,
    ) -> None:
        record = self.RECORD
        source = picture(tmp_path / "a.png", (30, 20))
        path = vault / record
        if setup == "not markdown":
            record = Path("assets/notes.txt")
            (vault / record).write_text("text")
        elif setup == "directory":
            (vault / self.IMAGE).mkdir(parents=True)
        elif setup == "not a picture":
            source.write_bytes(b"text")
        elif setup == "invalid yaml":
            path.write_text("---\ntype: [\n---\n")
        else:
            path.write_text(
                path.read_text().replace("summary:", '"image": x\nsummary:')
            )
        before = path.read_bytes()
        with pytest.raises(ValueError, match=message):
            ingest(record, source, vault)
        assert path.read_bytes() == before
        assert not (vault / self.IMAGE).is_file()
