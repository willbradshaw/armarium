"""Editing frontmatter in place keeps a record's formatting."""

import pytest
import yaml

from armarium.edit import (
    _fields,
    _reads_as,
    _scalar,
    emit,
    open_quote,
    requote,
    rewrite_frontmatter,
    set_field,
)
from armarium.parse import Frontmatter


class TestRewriteFrontmatter:
    LINES = [
        "---\n",
        "# keep\n",
        'a: "[[X]]"\n',
        "b:\n",
        "  - 1\n",
        "\n",
        "c: 2\n",
        "---\n",
    ]

    def test_edits_lines_when_they_read_as_expected(self) -> None:
        result = rewrite_frontmatter(
            self.LINES,
            {"a": "[[Y]]", "b": [1], "c": 2},
            lambda line: line.replace("[[X]]", "[[Y]]"),
        )
        assert result == [line.replace("[[X]]", "[[Y]]") for line in self.LINES]

    def test_writes_changed_fields_afresh(self) -> None:
        result = rewrite_frontmatter(
            self.LINES, {"a": "[[X]]", "b": [], "c": 2, "d": None}, lambda line: line
        )
        assert result == [
            "---\n",
            "# keep\n",
            'a: "[[X]]"\n',
            "b: []\n",
            "\n",
            "c: 2\n",
            "d:\n",
            "---\n",
        ]

    def test_keeps_crlf(self) -> None:
        lines = ["---\r\n", "a: 1\r\n", "---\r\n"]
        assert rewrite_frontmatter(lines, {"a": 2}) == [
            "---\r\n",
            "a: 2\r\n",
            "---\r\n",
        ]

    def test_refuses_what_cannot_be_written(self) -> None:
        with pytest.raises(ValueError, match="edit it by hand"):
            rewrite_frontmatter(["---\n", "a: 1\n", "---\n"], {"a": float("nan")})


class TestReadsAs:
    @pytest.mark.parametrize(
        ("lines", "expected"),
        [
            (["---\n", "a: 1\n", "---\n"], True),
            (["---\n", "a: 2\n", "---\n"], False),
            (["---\n", "a: [\n", "---\n"], False),
        ],
    )
    def test_reads_as(self, lines: list[str], expected: bool) -> None:
        assert _reads_as(lines, {"a": 1}) is expected


class TestFields:
    def test_spans(self) -> None:
        lines = [
            "# comment\n",
            'type: "[[X]]"\n',
            "'quoted key': 1\n",
            "aliases:\n",
            "- A\n",
            "  # inner\n",
            "\n",
            "# before c\n",
            "campaign_1:\n",
            "  first_session:\n",
        ]
        assert _fields(lines) == {
            "type": (1, 2),
            "quoted key": (2, 3),
            "aliases": (3, 6),
            "campaign_1": (8, 10),
        }


class TestEmit:
    @pytest.mark.parametrize(
        ("key", "value", "expected"),
        [
            ("summary", None, ["summary:"]),
            ("summary", "A [[Quay]] pilot", ['summary: "A [[Quay]] pilot"']),
            ("subjects", ["[[A]]", "[[B]]"], ['subjects: ["[[A]]", "[[B]]"]']),
            ("subjects", [], ["subjects: []"]),
            ("odd key", 1, ['"odd key": 1']),
            ("campaign_1", {}, ["campaign_1: {}"]),
            (
                "campaign_1",
                {"first_session": "[[S-1-001]]", "held_by": None},
                ["campaign_1:", '  first_session: "[[S-1-001]]"', "  held_by:"],
            ),
        ],
    )
    def test_emit(self, key: str, value: object, expected: list[str]) -> None:
        assert emit(key, value) == expected


class TestScalar:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, ""),
            (True, "true"),
            (3, "3"),
            ("é", '"é"'),
            ([None, "a", {"b": 1}], '[null, "a", {"b": 1}]'),
        ],
    )
    def test_scalar(self, value: object, expected: str) -> None:
        assert _scalar(value) == expected


class TestSetField:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            (
                "---\ntype: x\nimage:\nsource: s\n---\nBody\n",
                '---\ntype: x\nimage: "assets/a.webp"\nsource: s\n---\nBody\n',
            ),
            (
                "---\nimage: >\n  old\n  text\n# kept\n---\n",
                '---\nimage: "assets/a.webp"\n# kept\n---\n',
            ),
            (
                "---\nimage:\n- a\n- b\ntags: [ 'x' ]\n---\n",
                "---\nimage: \"assets/a.webp\"\ntags: [ 'x' ]\n---\n",
            ),
            (
                "---\ntype: x\nimage_source: y\n---\nimage: body\n",
                '---\ntype: x\nimage_source: y\nimage: "assets/a.webp"\n---\nimage: body\n',
            ),
            (
                "---\r\ntype: x\r\n---\r\nBody\r\n",
                '---\r\ntype: x\r\nimage: "assets/a.webp"\r\n---\r\nBody\r\n',
            ),
        ],
    )
    def test_sets_only_the_field(self, text: str, expected: str) -> None:
        assert set_field(text, "image", "assets/a.webp") == expected

    def test_quoted_key(self) -> None:
        text = '---\n"image": old\n---\n'
        assert set_field(text, "image", "a.webp") == '---\nimage: "a.webp"\n---\n'

    def test_quotes_a_value_when_yaml_needs_it(self) -> None:
        updated = set_field("---\ntype: x\n---\n", "image", "assets/a: b.webp")
        assert Frontmatter.parse(updated)[0]["image"] == "assets/a: b.webp"

    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("Body\n", "no frontmatter"),
            ("---\nimage: &old x\nother: *old\n---\n", "cannot be rewritten"),
        ],
    )
    def test_refuses(self, text: str, message: str) -> None:
        with pytest.raises(ValueError, match=message):
            set_field(text, "image", "assets/a.webp")


class TestOpenQuote:
    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ('a: "[[X]]"', '"'),
            ("a: '[[X]]'", "'"),
            ("a: [[X]]", ""),
            ('a: ["[[Y]]", [[X]]', ""),
            ('a: "say \\"[[X]]', '"'),
            ("a: 'it''s [[X]]", "'"),
        ],
    )
    def test_quote(self, line: str, expected: str) -> None:
        assert open_quote(line, line.index("[[X]]")) == expected


class TestRequote:
    @pytest.mark.parametrize(
        ("quote", "expected"),
        [
            ('"', 'say \\"[[A\\\\B]]\\" it\'s'),
            ("'", "say \"[[A\\B]]\" it''s"),
            ("", 'say "[[A\\B]]" it\'s'),
        ],
    )
    def test_reads_as_the_text(self, quote: str, expected: str) -> None:
        text = 'say "[[A\\B]]" it\'s'
        assert requote(text, quote) == expected
        if quote:
            assert yaml.safe_load(f"a: {quote}{expected}{quote}") == {"a": text}
