"""Records print as player handouts, a page each, in one PDF."""

import re
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import reportlab
from PIL import Image as PILImage
from reportlab.platypus import (
    Flowable,
    Image,
    KeepInFrame,
    ListFlowable,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
)

from armarium.handout import (
    MARKDOWN,
    PAGES,
    Corner,
    Font,
    Page,
    _children,
    _close,
    _flowables,
    _Inline,
    _picture,
    _rows,
    body,
    fit,
    handout,
    height,
    page,
    register_font,
    write,
)
from armarium.layout import Layout, Mark
from armarium.parse import Record

STARTER = Path(__file__).resolve().parents[1] / "vaults/starter"
VERA = Path(reportlab.__file__).parent / "fonts/Vera.ttf"
TIMES = Font("Times-Roman", True)
WIDTH = PAGES["letter"][0] - 2 * Layout().margin
RULES = "> [!rules]\n> *Ring, rare.* Grants [[Luck|luck]] to its wearer.\n"


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    shutil.copytree(STARTER, root)
    return root


def write_record(
    root: Path,
    name: str,
    body_text: str = RULES,
    **fields: Any,
) -> Path:
    """Write a Gear record with the given body and frontmatter fields."""
    lines = ['type: "[[types/Content]]"', "subtype: Gear", "summary: A thing."]
    lines += [f"{key}: {value}" for key, value in fields.items()]
    path = root / "content" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + "\n".join(lines) + "\n---\n" + body_text)
    return path


def parsed(root: Path, path: Path) -> Record:
    record, _ = Record.parse(path, root)
    assert record is not None
    return record


def picture(path: Path, size: tuple[int, int] = (300, 200)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    PILImage.new("RGBA", size, (0, 0, 0, 128)).save(path)
    return path


def pages_in(data: bytes) -> int:
    return len(re.findall(rb"/Type /Page\b(?!s)", data))


class TestRegisterFont:
    @pytest.mark.parametrize(
        ("name", "faces"),
        [
            ("Times-Roman", True),
            ("Helvetica-Bold", True),
            ("Courier", True),
            ("Symbol", False),
        ],
    )
    def test_standard_fonts(self, tmp_path: Path, name: str, faces: bool) -> None:
        assert register_font(name, tmp_path) == Font(name, faces)

    @pytest.mark.parametrize("relative", [True, False])
    def test_a_font_file_is_one_face(self, tmp_path: Path, relative: bool) -> None:
        target = tmp_path / "fonts/Vera.ttf"
        target.parent.mkdir()
        shutil.copy(VERA, target)
        spec = "fonts/Vera.ttf" if relative else str(target)
        font = register_font(spec, tmp_path)
        assert font == Font(f"armarium:{target}", False)
        assert register_font(spec, tmp_path) == font

    def test_refuses_a_missing_font(self, tmp_path: Path) -> None:
        with pytest.raises(
            ValueError, match="font Fancy is neither a standard font nor a file"
        ):
            register_font("Fancy", tmp_path)

    def test_refuses_a_file_that_is_not_a_font(self, tmp_path: Path) -> None:
        (tmp_path / "notes.ttf").write_text("not a font")
        with pytest.raises(ValueError, match="cannot use font notes.ttf: "):
            register_font("notes.ttf", tmp_path)


class TestInlineConvert:
    @pytest.mark.parametrize(
        ("markdown", "faces", "layout", "expected"),
        [
            ("a < b & c", True, Layout(), "a &lt; b &amp; c"),
            ("drop <span>html</span>", True, Layout(), "drop html"),
            ("**bold** and *it*", True, Layout(), "<b>bold</b> and <i>it</i>"),
            ("**bold** and *it*", False, Layout(), "<u>bold</u> and <u>it</u>"),
            ("one\ntwo", True, Layout(), "one two"),
            ("one  \ntwo", True, Layout(), "one<br/>two"),
            ("use `code`", True, Layout(), "use code"),
            ("a [site](https://x.org)", True, Layout(), "a site"),
            ("Fire Bolt!", True, Layout(), "Fire Bolt!"),
            (
                "Fire Bolt!",
                True,
                Layout(underline_links=True, lowercase_links=True),
                "<u>fire bolt</u>!",
            ),
            (
                "*Fire* Bolt",
                True,
                Layout(lowercase_links=True),
                "<i>fire</i> bolt",
            ),
        ],
    )
    def test_converts_inline_markdown(
        self, markdown: str, faces: bool, layout: Layout, expected: str
    ) -> None:
        tokens = MARKDOWN.parseInline(markdown)[0].children or []
        assert _Inline(layout, Font("F", faces)).convert(tokens) == expected


class TestClose:
    def test_finds_the_matching_closer(self) -> None:
        tokens = MARKDOWN.parse("- a\n  - b\n\nafter\n")
        assert tokens[_close(tokens, 0)].type == "bullet_list_close"
        assert tokens[_close(tokens, 0) + 1].type == "paragraph_open"

    def test_an_unclosed_run_ends_at_the_last_token(self) -> None:
        tokens = MARKDOWN.parse("para\n")[:2]
        assert _close(tokens, 0) == 1


class TestChildren:
    def test_yields_each_top_level_block(self) -> None:
        tokens = MARKDOWN.parse("one\n\n- a\n- b\n\n---\n")
        spans = list(_children(tokens, 0, len(tokens)))
        assert [tokens[first].type for first, _ in spans] == [
            "paragraph_open",
            "bullet_list_open",
            "hr",
        ]
        assert [tokens[last].type for _, last in spans] == [
            "paragraph_close",
            "bullet_list_close",
            "hr",
        ]


class TestRows:
    def test_yields_each_row_header_first(self) -> None:
        tokens = MARKDOWN.parse("| A | B |\n| - | - |\n| 1 | 2 |\n| 3 | 4 |\n")
        rows = list(_rows(tokens, 0, len(tokens)))
        assert len(rows) == 3
        assert all(tokens[last].type == "tr_close" for _, last in rows)


class TestFlowables:
    @staticmethod
    def convert(markdown: str) -> list[Flowable]:
        tokens = MARKDOWN.parse(markdown)
        style = body("x", Layout(), TIMES, 12, WIDTH)[0].style
        inline = _Inline(Layout(), TIMES)
        return _flowables(tokens, 0, len(tokens), style, inline, WIDTH)

    @pytest.mark.parametrize(
        ("markdown", "kinds"),
        [
            ("One.\n\nTwo.\n", [Paragraph, Paragraph]),
            ("# Heading\n", [Paragraph]),
            ("```\ncode\n```\n", [Paragraph]),
            ("    indented\n", [Paragraph]),
            ("- a\n- b\n", [ListFlowable]),
            ("> quoted\n", [Paragraph]),
            ("| A |\n| - |\n| 1 |\n", [Table]),
            ("---\n\n<div>html</div>\n", []),
        ],
    )
    def test_kinds(self, markdown: str, kinds: list[type]) -> None:
        assert [type(flowable) for flowable in self.convert(markdown)] == kinds

    def test_a_heading_is_bold(self) -> None:
        (heading,) = self.convert("## Charges\n")
        assert heading.text == "<b>Charges</b>"

    def test_code_keeps_its_lines(self) -> None:
        (code,) = self.convert("```\na < b\nc\n```\n")
        assert code.text == "a &lt; b<br/>c"

    @pytest.mark.parametrize(
        ("markdown", "kind", "start"),
        [("- a\n- b\n", "bullet", "bulletchar"), ("3. a\n4. b\n", "1", 3)],
    )
    def test_lists(self, markdown: str, kind: str, start: object) -> None:
        (listing,) = self.convert(markdown)
        assert listing._bulletType == kind
        assert listing._start == start
        assert len(listing._flowables) == 2

    def test_an_empty_list_item_keeps_its_place(self) -> None:
        (listing,) = self.convert("- a\n-\n")
        assert len(listing._flowables) == 2

    def test_a_table_fills_the_width_in_equal_columns(self) -> None:
        (table,) = self.convert("| A | B | C |\n| - | - | - |\n| 1 | 2 | 3 |\n")
        assert table._colWidths == [WIDTH / 3] * 3
        assert [[cell.text for cell in row] for row in table._cellvalues] == [
            ["A", "B", "C"],
            ["1", "2", "3"],
        ]


class TestBody:
    def test_links_print_as_text_and_embeds_go(self) -> None:
        markdown = (
            "Grants [[Luck|luck]] and [[spells/Fire Bolt#Range]].\n\n![[Ring.webp|500]]"
        )
        flowables = body(markdown, Layout(), TIMES, 14, WIDTH)
        assert [flowable.text for flowable in flowables] == [
            "Grants luck and Fire Bolt."
        ]

    def test_sets_the_size_and_spacing(self) -> None:
        (paragraph,) = body("Text.", Layout(line_spacing=1.5), TIMES, 20, WIDTH)
        assert paragraph.style.fontSize == 20
        assert paragraph.style.leading == 30
        assert paragraph.style.fontName == "Times-Roman"


class TestHeight:
    def test_sums_heights_and_space(self) -> None:
        flowables = [Spacer(10, 30), Spacer(10, 12)]
        assert height(flowables, WIDTH) == 42
        paragraph = body("Text.", Layout(), TIMES, 10, WIDTH)[0]
        assert height([paragraph], WIDTH) == pytest.approx(10 * 1.2 + 10 * 0.35)


class TestFit:
    TEXT = "A sentence of rules text that runs on for a while. " * 12

    def measured(self, size: float, text: str = TEXT) -> float:
        return height(body(text, Layout(), TIMES, size, WIDTH), WIDTH)

    def test_short_text_takes_the_largest_size(self) -> None:
        assert fit("Short.", Layout(), TIMES, WIDTH, 1000) == (
            24,
            self.measured(24, "Short."),
        )

    def test_text_too_long_takes_the_smallest_size(self) -> None:
        assert fit(self.TEXT, Layout(), TIMES, WIDTH, 10) == (12, self.measured(12))

    def test_otherwise_the_largest_size_that_fits(self) -> None:
        target = self.measured(17) + 1
        size, text_height = fit(self.TEXT, Layout(), TIMES, WIDTH, target)
        assert size % 0.5 == 0 and 17 <= size < 24
        assert text_height == self.measured(size) <= target
        assert self.measured(size + 0.5) > target

    def test_refuses_sizes_the_wrong_way_round(self) -> None:
        layout = Layout("Odd", min_text_size=30, max_text_size=20)
        with pytest.raises(
            ValueError, match="layout Odd: min_text_size 30 is larger than"
        ):
            fit("Text.", layout, TIMES, WIDTH, 100)


class TestCorner:
    def test_takes_no_room(self) -> None:
        corner = Corner("A", "Times-Roman", 50)
        assert corner.wrap(400, 600) == (0, 0)
        assert corner.width == 400

    def test_prints_against_the_right_edge(self) -> None:
        corner = Corner("A", "Times-Roman", 50)
        corner.wrap(400, 600)
        corner.canv = MagicMock()
        corner.draw()
        corner.canv.setFont.assert_called_once_with("Times-Roman", 50)
        corner.canv.drawRightString.assert_called_once_with(400, -40, "A")


class TestPicture:
    @pytest.mark.parametrize("value", [None, '""'])
    def test_none(self, vault: Path, value: str | None) -> None:
        fields = {} if value is None else {"image": value}
        path = write_record(vault, "Ring", **fields)
        assert _picture(vault, parsed(vault, path)) is None

    def test_a_file_in_the_vault(self, vault: Path) -> None:
        art = picture(vault / "assets/art/ring.png")
        path = write_record(vault, "Ring", image="assets/art/ring.png")
        assert _picture(vault, parsed(vault, path)) == art

    @pytest.mark.parametrize("value", ["assets/art/missing.png", "7", "[a]"])
    def test_refuses_anything_else(self, vault: Path, value: str) -> None:
        path = write_record(vault, "Ring", image=value)
        with pytest.raises(ValueError, match="is not a file in the vault"):
            _picture(vault, parsed(vault, path))


class TestPage:
    def test_name_text_and_picture(self, vault: Path) -> None:
        picture(vault / "assets/art/ring.png", (300, 300))
        path = write_record(vault, "Ring", image="assets/art/ring.png")
        flowables, account = page(vault, parsed(vault, path), Layout("Gear"))
        assert [type(flowable) for flowable in flowables] == [
            Paragraph,
            Paragraph,
            Spacer,
            Image,
            PageBreak,
        ]
        assert flowables[0].text == "Ring"
        assert account.record == "content/Ring.md"
        assert account.layout == "Gear"
        assert account.text_size == 24
        assert account.picture is not None and account.picture > 3
        assert account.notes == ()
        image = flowables[3]
        assert image.drawWidth == pytest.approx(image.drawHeight)

    def test_a_wide_picture_fills_the_width(self, vault: Path) -> None:
        picture(vault / "assets/art/wide.png", (1000, 100))
        path = write_record(vault, "Ring", image="assets/art/wide.png")
        flowables, _ = page(vault, parsed(vault, path), Layout())
        assert flowables[3].drawWidth == pytest.approx(WIDTH)

    def test_without_a_picture_the_text_takes_the_page(self, vault: Path) -> None:
        text = "> [!rules]\n" + "> A long line of rules text runs on.\n" * 40
        path = write_record(vault, "Ring", text)
        flowables, account = page(vault, parsed(vault, path), Layout())
        assert account.picture is None
        assert not any(isinstance(flowable, Image) for flowable in flowables)
        with_picture = Layout(image_share=0.9)
        assert (
            account.text_size
            > fit(
                parsed(vault, path).body.callout("rules"),
                with_picture,
                TIMES,
                WIDTH,
                100,
            )[0]
        )

    @pytest.mark.parametrize(
        ("attuned", "marked"), [("true", True), ("false", False), ('"yes"', False)]
    )
    def test_a_mark_when_its_field_is_true(
        self, vault: Path, attuned: str, marked: bool
    ) -> None:
        path = write_record(vault, "Ring", attunement=attuned)
        layout = Layout(mark=Mark("attunement", "A"))
        flowables, _ = page(vault, parsed(vault, path), layout)
        assert isinstance(flowables[0], Corner) is marked
        title = flowables[1 if marked else 0]
        assert (title.style.rightIndent > 0) is marked

    def test_text_too_long_shrinks_and_leaves_no_room(self, vault: Path) -> None:
        picture(vault / "assets/art/ring.png")
        text = "> [!rules]\n" + "> A long line of rules text runs on and on.\n" * 200
        path = write_record(vault, "Ring", text, image="assets/art/ring.png")
        flowables, account = page(vault, parsed(vault, path), Layout())
        assert any(isinstance(flowable, KeepInFrame) for flowable in flowables)
        assert not any(isinstance(flowable, Image) for flowable in flowables)
        assert account.text_size == 12 and account.picture is None
        assert account.notes == (
            "its text overflows at 12pt and was shrunk to fit",
            "its text leaves no room for its picture",
        )

    def test_refuses_a_record_without_rules_text(self, vault: Path) -> None:
        for body_text in ("## Notes\n", "> [!rules]\n>\n"):
            path = write_record(vault, "Ring", body_text)
            with pytest.raises(
                ValueError, match="content/Ring.md has no rules text to print"
            ):
                page(vault, parsed(vault, path), Layout())

    def test_refuses_a_picture_it_cannot_read(self, vault: Path) -> None:
        (vault / "assets/art").mkdir(parents=True)
        (vault / "assets/art/ring.png").write_text("not a picture")
        path = write_record(vault, "Ring", image="assets/art/ring.png")
        with pytest.raises(ValueError, match="cannot read image ring.png: "):
            page(vault, parsed(vault, path), Layout())


class TestWrite:
    def test_renders_a_pdf(self, tmp_path: Path) -> None:
        data = write(
            [Paragraph("One"), PageBreak(), Paragraph("Two")],
            tmp_path / "loot.pdf",
            PAGES["a4"],
            36,
        )
        assert data.startswith(b"%PDF")
        assert pages_in(data) == 2
        assert b"/Title (loot)" in data
        assert b"/MediaBox [ 0 0 595.2756 841.8898 ]" in data


class TestHandout:
    def test_prints_each_record_on_a_page_in_order(
        self, vault: Path, tmp_path: Path
    ) -> None:
        for name in ("Ring", "Amulet"):
            write_record(vault, name)
        output = tmp_path / "out/loot.pdf"
        result = handout(
            [Path("content/Ring.md"), Path("content/Amulet.md")], output, vault
        )
        assert result.vault == vault.resolve()
        assert result.output == output
        assert [page.record for page in result.pages] == [
            "content/Ring.md",
            "content/Amulet.md",
        ]
        assert pages_in(output.read_bytes()) == 2

    def test_paths_from_the_working_directory(
        self, vault: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_record(vault, "Ring")
        monkeypatch.chdir(vault / "content")
        result = handout([Path("Ring.md")], tmp_path / "loot.pdf")
        assert result.vault == vault.resolve()

    def test_each_record_takes_its_layout(self, vault: Path, tmp_path: Path) -> None:
        (vault / "reference/handouts").mkdir()
        (vault / "reference/handouts/Gear.md").write_text(
            '---\ntype: "[[Reference]]"\nsubtype: Handout\nprints: [Content/Gear]\n'
            "max_text_size: 20\n---\n"
        )
        (vault / "reference/handouts/Big.md").write_text(
            '---\ntype: "[[Reference]]"\nsubtype: Handout\nmax_text_size: 30\n---\n'
        )
        write_record(vault, "Ring")
        output = tmp_path / "loot.pdf"
        chosen = handout([Path("content/Ring.md")], output, vault)
        named = handout(
            [Path("content/Ring.md")], output, vault, layout="Big", overwrite=True
        )
        assert chosen.pages == (Page("content/Ring.md", "Gear", 20, None),)
        assert named.pages == (Page("content/Ring.md", "Big", 30, None),)

    @pytest.mark.parametrize(
        ("records", "output", "message"),
        [
            ([], "loot.pdf", "name at least one record to print"),
            (["content/Ring.md"], "loot.txt", "loot.txt is not a .pdf path"),
            (["content/Ring.md"], "exists.pdf", "exists.pdf exists; pass --overwrite"),
            (["content/Missing.md"], "loot.pdf", "does not exist"),
            (["content/notes.txt"], "loot.pdf", "is not a Markdown record"),
            (["content/Broken.md"], "loot.pdf", "cannot parse content/Broken.md: "),
            (["content/Bare.md"], "loot.pdf", "has no rules text to print"),
        ],
    )
    def test_refuses(
        self,
        vault: Path,
        tmp_path: Path,
        records: list[str],
        output: str,
        message: str,
    ) -> None:
        write_record(vault, "Ring")
        write_record(vault, "Bare", "## Notes\n")
        (vault / "content/notes.txt").write_text("notes")
        (vault / "content/Broken.md").write_text("---\ntype: [\n---\n")
        (tmp_path / "exists.pdf").write_text("old")
        with pytest.raises(ValueError, match=message):
            handout([Path(r) for r in records], tmp_path / output, vault)
        assert not (tmp_path / "loot.pdf").exists()
        assert (tmp_path / "exists.pdf").read_text() == "old"

    def test_refuses_records_from_two_vaults(self, tmp_path: Path) -> None:
        first, second = tmp_path / "one", tmp_path / "two"
        for root in (first, second):
            shutil.copytree(STARTER, root)
            write_record(root, "Ring")
        with pytest.raises(ValueError, match="is not in the vault"):
            handout(
                [first / "content/Ring.md", second / "content/Ring.md"],
                tmp_path / "loot.pdf",
            )

    def test_refuses_layouts_with_different_pages(
        self, vault: Path, tmp_path: Path
    ) -> None:
        (vault / "reference/handouts").mkdir()
        (vault / "reference/handouts/Spells.md").write_text(
            '---\ntype: "[[Reference]]"\nsubtype: Handout\nprints: [Content/Lore]\n'
            "page: a4\n---\n"
        )
        write_record(vault, "Ring")
        lore = write_record(vault, "Rumour")
        lore.write_text(lore.read_text().replace("subtype: Gear", "subtype: Lore"))
        with pytest.raises(ValueError, match="differ in page size or margin"):
            handout(
                [Path("content/Ring.md"), Path("content/Rumour.md")],
                tmp_path / "loot.pdf",
                vault,
            )
