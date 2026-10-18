"""Editing frontmatter in place keeps a record's formatting."""

import pytest

from armarium.edit import _fields, _reads_as, _scalar, emit, rewrite_frontmatter


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
