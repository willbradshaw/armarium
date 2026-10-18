"""Relinking plans and makes the link changes that moving a record needs."""

import codecs
from pathlib import Path

import pytest

from armarium.relink import (
    _DROP,
    Change,
    Plan,
    Relinker,
    _display,
    _fields,
    _quote,
    _reads_as,
    _scalar,
    _write,
    emit,
    rewrite_frontmatter,
)

SESSION = """---
type: "[[Session]]"
prepared_locations: ["[[Quay Nine]]", "[[Port Briselle]]"]
campaign_1:
  held_by: '[[quay nine]]'
---
Opening at [[quay nine]].
# Notes
## Events
The crew met at [[Quay Nine|the quay]] and again at [[content/Quay Nine#Notes]].
| Place | Note |
| --- | --- |
| [[Quay Nine]] | busy |

![[Quay Nine.md]] and [[Port Briselle]].
"""


def write(root: Path, relative: str, text: str = "") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path.resolve() / "vault"
    for directory in ("reference/types", "campaigns"):
        (root / directory).mkdir(parents=True)
    write(
        root, "content/Quay Nine.md", "---\n---\n## Notes\nSee [[Quay Nine#Notes]].\n"
    )
    write(root, "content/Port Briselle.md", "---\n---\n")
    write(root, "campaigns/campaign_1/sessions/S-1-001.md", SESSION)
    write(root, "campaigns/campaign_2/content/Harbour.md", "---\n---\n")
    write(root, "campaigns/campaign_2/content/Gull.md", "---\n---\nAt [[Harbour]].\n")
    write(root, "docs/guide.md", "See [[Quay Nine]].\n")
    write(root, "bases/places.base", 'filters: "[[Quay Nine]]"\n')
    write(root, "reference/templates/Place.md", "---\n---\n[[Quay Nine]]\n")
    write(root, "notes/Plans.md", "---\n---\n[map](Quay%20Nine.md) [[Port Briselle]]\n")
    return root


def relinker(root: Path, moves: dict[str, str | None], **options: bool) -> Relinker:
    return Relinker(
        root,
        {root / old: None if new is None else root / new for old, new in moves.items()},
        **options,
    )


class TestChangeOutput:
    @pytest.mark.parametrize(
        ("change", "expected"),
        [
            (
                Change("a.md", "Notes", 4, "[[A]] → [[B]]"),
                "a.md\tNotes\t4\t[[A]] → [[B]]",
            ),
            (Change("a.md", "subjects", 0, "x"), "a.md\tsubjects\t\tx"),
            (Change("a.md", "", 0, "renamed to b.md"), "a.md\t\t\trenamed to b.md"),
        ],
    )
    def test_tab_separated(self, change: Change, expected: str) -> None:
        assert change.output == expected


class TestPlanApply:
    def test_writes_renames_and_deletes(self, tmp_path: Path) -> None:
        old, other, gone = (write(tmp_path, n, "x") for n in ("a.md", "b.md", "c.md"))
        plan = Plan(
            texts={old: "new a", other: "new b", gone: "never written"},
            renamed={old: tmp_path / "A2.md"},
            deleted={gone},
        )
        plan.apply()
        assert sorted(p.name for p in tmp_path.iterdir()) == ["A2.md", "b.md"]
        assert (tmp_path / "A2.md").read_text() == "new a"
        assert other.read_text() == "new b"

    def test_case_only_rename(self, tmp_path: Path) -> None:
        old = write(tmp_path, "quay.md", "x")
        Plan(renamed={old: tmp_path / "Quay.md"}).apply()
        assert [p.name for p in tmp_path.iterdir()] == ["Quay.md"]


class TestWrite:
    @pytest.mark.parametrize("bom", [b"", codecs.BOM_UTF8])
    def test_keeps_bom_and_line_endings(self, tmp_path: Path, bom: bytes) -> None:
        path = tmp_path / "a.md"
        path.write_bytes(bom + b"old\r\n")
        _write(path, "new\r\nline\r\n")
        assert path.read_bytes() == bom + b"new\r\nline\r\n"
        assert [p.name for p in tmp_path.iterdir()] == ["a.md"]


class TestRelinkerInit:
    def test_targets_include_files_sharing_an_arriving_name(self, vault: Path) -> None:
        relinked = relinker(
            vault, {"content/Quay Nine.md": "campaigns/campaign_1/content/Harbour.md"}
        )
        assert relinked.targets == {
            vault / "content/Quay Nine.md",
            vault / "campaigns/campaign_2/content/Harbour.md",
        }

    def test_after_index_holds_the_new_path(self, vault: Path) -> None:
        relinked = relinker(
            vault, {"content/Quay Nine.md": "campaigns/campaign_1/content/Harbour.md"}
        )
        source = vault / "notes/Plans.md"
        assert relinked.after.resolve("Quay Nine", source) == (None, "link.missing")
        assert relinked.after.resolve("campaign_1/content/Harbour", source)[0] == (
            vault / "campaigns/campaign_1/content/Harbour.md"
        )
        assert relinked.after.resolve("Harbour", source)[1] == "link.ambiguous"

    def test_deleted_file_leaves_the_after_index(self, vault: Path) -> None:
        relinked = relinker(vault, {"content/Quay Nine.md": None})
        assert relinked.after.resolve("Quay Nine", vault / "notes/Plans.md")[0] is None


class TestRelinkerDestination:
    @pytest.mark.parametrize(
        ("contents", "expected"),
        [
            ("Quay Nine", ("content/Quay Nine.md", "content/Quay Ten.md")),
            (
                "quay nine.md#Notes|the quay",
                ("content/Quay Nine.md", "content/Quay Ten.md"),
            ),
            ("Port Briselle", None),
            ("#Notes", None),
            ("Nowhere", None),
            ("", None),
        ],
    )
    def test_destination(
        self, vault: Path, contents: str, expected: tuple[str, str] | None
    ) -> None:
        relinked = relinker(vault, {"content/Quay Nine.md": "content/Quay Ten.md"})
        found = relinked.destination(contents, vault / "notes/Plans.md")
        assert found == (
            None if expected is None else tuple(vault / path for path in expected)
        )

    def test_deleted(self, vault: Path) -> None:
        relinked = relinker(vault, {"content/Quay Nine.md": None})
        assert relinked.destination("Quay Nine", vault / "notes/Plans.md") == (
            vault / "content/Quay Nine.md",
            None,
        )


class TestRelinkerSpell:
    @pytest.mark.parametrize(
        ("new", "target", "expected"),
        [
            ("content/Quay Ten.md", "Quay Nine", "Quay Ten"),
            ("content/Quay Ten.md", "content/quay nine", "content/Quay Ten"),
            ("content/Quay Ten.md", "Quay Nine.md", "Quay Ten.md"),
            ("content/Quay Ten.md", "/content/Quay Nine", "/content/Quay Ten"),
            (
                "campaigns/campaign_1/content/Harbour.md",
                "Quay Nine",
                "campaign_1/content/Harbour",
            ),
            (
                "campaigns/campaign_1/content/Harbour.md",
                "Quay Nine.MD",
                "campaign_1/content/Harbour.md",
            ),
        ],
    )
    def test_moved(self, vault: Path, new: str, target: str, expected: str) -> None:
        relinked = relinker(vault, {"content/Quay Nine.md": new})
        spelled = relinked.spell(
            target,
            vault / "content/Quay Nine.md",
            vault / new,
            vault / "notes/Plans.md",
        )
        assert spelled == expected

    @pytest.mark.parametrize(
        ("target", "expected"),
        [
            ("Harbour", "campaign_2/content/Harbour"),
            ("content/Harbour", "campaign_2/content/Harbour"),
            (
                "campaigns/campaign_2/content/Harbour",
                "campaigns/campaign_2/content/Harbour",
            ),
        ],
    )
    def test_file_that_comes_to_share_a_name(
        self, vault: Path, target: str, expected: str
    ) -> None:
        relinked = relinker(
            vault, {"content/Quay Nine.md": "campaigns/campaign_1/content/Harbour.md"}
        )
        harbour = vault / "campaigns/campaign_2/content/Harbour.md"
        assert relinked.spell(target, harbour, harbour, harbour) == expected

    def test_full_path(self, vault: Path) -> None:
        write(vault, "x/campaign_1/content/Quay Ten.md")
        new = vault / "campaigns/campaign_1/content/Quay Ten.md"
        old = vault / "content/Quay Nine.md"
        relinked = relinker(vault, {"content/Quay Nine.md": str(new)})
        assert relinked.spell("Quay Nine", old, new, old) == (
            "campaigns/campaign_1/content/Quay Ten"
        )

    def test_refuses_when_no_path_is_unique(self, vault: Path) -> None:
        write(vault, "x/content/Quay Ten.md")
        relinked = relinker(vault, {"content/Quay Nine.md": "content/Quay Ten.md"})
        new = vault / "content/Quay Ten.md"
        old = vault / "content/Quay Nine.md"
        with pytest.raises(ValueError, match="no link can name content/Quay Ten.md"):
            relinked.spell("Quay Nine", old, new, old)


class TestRelinkerReplacement:
    @pytest.mark.parametrize(
        ("contents", "options", "expected"),
        [
            ("Quay Nine", {}, "[[Quay Ten]]"),
            (" Quay Nine #Notes", {}, "[[ Quay Ten #Notes]]"),
            ("Quay Nine|the quay", {}, "[[Quay Ten|the quay]]"),
            ("Quay Nine\\|the quay", {}, "[[Quay Ten\\|the quay]]"),
            ("Quay Nine", {"keep_text": True}, "[[Quay Ten|Quay Nine]]"),
            (
                "content/Quay Nine.md#^a",
                {"keep_text": True},
                "[[content/Quay Ten.md#^a|Quay Nine]]",
            ),
            ("Quay Nine|the quay", {"keep_text": True}, "[[Quay Ten|the quay]]"),
            ("Port Briselle", {}, None),
        ],
    )
    def test_body(
        self, vault: Path, contents: str, options: dict[str, bool], expected: str | None
    ) -> None:
        relinked = relinker(
            vault, {"content/Quay Nine.md": "content/Quay Ten.md"}, **options
        )
        source = vault / "notes/Plans.md"
        assert relinked.replacement(contents, source, body=True) == expected

    def test_table_escapes_the_new_bar(self, vault: Path) -> None:
        relinked = relinker(
            vault, {"content/Quay Nine.md": "content/Quay Ten.md"}, keep_text=True
        )
        source = vault / "notes/Plans.md"
        assert (
            relinked.replacement("Quay Nine", source, body=True, table=True)
            == "[[Quay Ten\\|Quay Nine]]"
        )

    def test_frontmatter_stays_canonical(self, vault: Path) -> None:
        relinked = relinker(
            vault, {"content/Quay Nine.md": "content/Quay Ten.md"}, keep_text=True
        )
        source = vault / "notes/Plans.md"
        assert relinked.replacement("Quay Nine", source, body=False) == "[[Quay Ten]]"

    def test_unchanged_spelling(self, vault: Path) -> None:
        relinked = relinker(
            vault, {"content/Quay Nine.md": "campaigns/campaign_1/content/Harbour.md"}
        )
        gull = vault / "campaigns/campaign_2/content/Gull.md"
        assert (
            relinked.replacement("campaign_2/content/Harbour", gull, body=True) is None
        )

    @pytest.mark.parametrize(
        ("contents", "expected"),
        [("Quay Nine", "Quay Nine"), ("Quay Nine|the quay", "the quay")],
    )
    def test_deleted_becomes_text(
        self, vault: Path, contents: str, expected: str
    ) -> None:
        relinked = relinker(vault, {"content/Quay Nine.md": None})
        source = vault / "notes/Plans.md"
        assert relinked.replacement(contents, source, body=True) == expected


class TestRelinkerSubstitute:
    @pytest.mark.parametrize(
        ("moves", "text", "expected", "changed"),
        [
            (
                {"content/Quay Nine.md": "content/Quay Ten.md"},
                "At ![[Quay Nine]] by [[Port Briselle]].",
                "At ![[Quay Ten]] by [[Port Briselle]].",
                [("![[Quay Nine]]", "![[Quay Ten]]")],
            ),
            (
                {"content/Quay Nine.md": None},
                "At ![[Quay Nine]] and [[Quay Nine|the quay]].",
                "At Quay Nine and the quay.",
                [
                    ("![[Quay Nine]]", "Quay Nine"),
                    ("[[Quay Nine|the quay]]", "the quay"),
                ],
            ),
            ({"content/Quay Nine.md": None}, "No links.", "No links.", []),
        ],
    )
    def test_substitute(
        self,
        vault: Path,
        moves: dict[str, str | None],
        text: str,
        expected: str,
        changed: list[tuple[str, str]],
    ) -> None:
        relinked = relinker(vault, moves)
        result = relinked.substitute(text, vault / "notes/Plans.md", body=True)
        assert result == (expected, changed)


class TestRelinkerRelink:
    def test_rewrites_frontmatter_and_body(self, vault: Path) -> None:
        path = vault / "campaigns/campaign_1/sessions/S-1-001.md"
        relinked = relinker(
            vault, {"content/Quay Nine.md": "content/Quay Ten.md"}, keep_text=True
        )
        result = relinked.relink(path, SESSION)
        assert result is not None
        text, changes = result
        assert text == (
            SESSION.replace('["[[Quay Nine]]"', '["[[Quay Ten]]"')
            .replace("'[[quay nine]]'", "'[[Quay Ten]]'")
            .replace("at [[quay nine]]", "at [[Quay Ten|quay nine]]")
            .replace("[[Quay Nine|the quay]]", "[[Quay Ten|the quay]]")
            .replace(
                "[[content/Quay Nine#Notes]]", "[[content/Quay Ten#Notes|Quay Nine]]"
            )
            .replace("| [[Quay Nine]] |", "| [[Quay Ten\\|Quay Nine]] |")
            .replace("![[Quay Nine.md]]", "![[Quay Ten.md|Quay Nine]]")
        )
        relative = "campaigns/campaign_1/sessions/S-1-001.md"
        assert [(c.relative, c.where, c.line) for c in changes] == [
            (relative, "prepared_locations", 0),
            (relative, "campaign_1.held_by", 0),
            (relative, "", 7),
            (relative, "Notes > Events", 10),
            (relative, "Notes > Events", 10),
            (relative, "Notes > Events", 13),
            (relative, "Notes > Events", 15),
        ]

    def test_no_change(self, vault: Path) -> None:
        relinked = relinker(vault, {"content/Port Briselle.md": "content/Port.md"})
        assert (
            relinked.relink(vault / "notes/Plans.md", "---\n---\nNo links.\n") is None
        )

    def test_rewritten_field_changes_the_line_count(self, vault: Path) -> None:
        text = (
            '---\nsubjects:\n  - "[[Quay Nine]]"\n  - "[[Port Briselle]]"\n---\n'
            "## Notes\n[[Quay Nine]]\n"
        )
        relinked = relinker(vault, {"content/Quay Nine.md": None})
        result = relinked.relink(vault / "notes/Plans.md", text)
        assert result is not None
        assert result[0] == (
            '---\nsubjects: ["[[Port Briselle]]"]\n---\n## Notes\nQuay Nine\n'
        )
        assert [(c.where, c.line, c.text) for c in result[1]] == [
            ("subjects", 0, "[[Quay Nine]] removed"),
            ("Notes", 7, "[[Quay Nine]] → Quay Nine"),
        ]

    def test_unparseable(self, vault: Path) -> None:
        relinked = relinker(vault, {"content/Quay Nine.md": None})
        with pytest.raises(ValueError, match="closing"):
            relinked.relink(vault / "notes/Plans.md", "---\n[[Quay Nine]]\n")


class TestRelinkerValue:
    @pytest.mark.parametrize(
        ("value", "listed", "expected", "texts"),
        [
            ("[[Quay Nine]]", False, None, ["[[Quay Nine]] removed"]),
            ("[[Quay Nine]]", True, "drop", ["[[Quay Nine]] removed"]),
            (
                "At [[Quay Nine]].",
                False,
                "At Quay Nine.",
                ["[[Quay Nine]] → Quay Nine"],
            ),
            (
                ["[[Port Briselle]]", "[[Quay Nine]]"],
                False,
                ["[[Port Briselle]]"],
                ["[[Quay Nine]] removed"],
            ),
            (
                {"held_by": "[[Quay Nine]]", "n": 3},
                False,
                {"held_by": None, "n": 3},
                ["[[Quay Nine]] removed"],
            ),
            (3, False, 3, []),
        ],
    )
    def test_deleted(
        self,
        vault: Path,
        value: object,
        listed: bool,
        expected: object,
        texts: list[str],
    ) -> None:
        relinked = relinker(vault, {"content/Quay Nine.md": None})
        changes: list[Change] = []
        result = relinked._value(
            value,
            "field",
            vault / "notes/Plans.md",
            "notes/Plans.md",
            changes,
            listed=listed,
        )
        assert (result is _DROP) if expected == "drop" else result == expected
        assert [c.text for c in changes] == texts

    def test_locations(self, vault: Path) -> None:
        relinked = relinker(vault, {"content/Quay Nine.md": "content/Quay Ten.md"})
        changes: list[Change] = []
        result = relinked._value(
            {"campaign_1": {"held_by": ["[[Quay Nine]]"]}, "x": "[[Quay Nine]]"},
            "",
            vault / "notes/Plans.md",
            "notes/Plans.md",
            changes,
            listed=False,
        )
        assert result == {
            "campaign_1": {"held_by": ["[[Quay Ten]]"]},
            "x": "[[Quay Ten]]",
        }
        assert [c.where for c in changes] == ["campaign_1.held_by", "x"]


class TestRelinkerRaw:
    @pytest.mark.parametrize(
        ("name", "line", "expected"),
        [
            ("Quay Ten", 'a: "[[Quay Nine]]"\n', 'a: "[[Quay Ten]]"\n'),
            ("Wren's Rest", "a: '[[Quay Nine]]'\n", "a: '[[Wren''s Rest]]'\n"),
            ("Wren's Rest", 'a: "[[Quay Nine]]"\n', 'a: "[[Wren\'s Rest]]"\n'),
            ("Quay Ten", "a: [[Port Briselle]]\n", "a: [[Port Briselle]]\n"),
        ],
    )
    def test_quoting(self, vault: Path, name: str, line: str, expected: str) -> None:
        relinked = relinker(vault, {"content/Quay Nine.md": f"content/{name}.md"})
        assert relinked._raw(line, vault / "notes/Plans.md") == expected

    def test_deleted_links_are_left_for_regeneration(self, vault: Path) -> None:
        relinked = relinker(vault, {"content/Quay Nine.md": None})
        line = 'a: "[[Quay Nine]]"\n'
        assert relinked._raw(line, vault / "notes/Plans.md") == line


class TestRelinkerUnchanged:
    def test_lists_links_outside_records(self, vault: Path) -> None:
        relinked = relinker(vault, {"content/Quay Nine.md": "content/Quay Ten.md"})
        assert relinked.unchanged() == [
            "bases/places.base:1: [[Quay Nine]] not changed: not a record",
            "docs/guide.md:1: [[Quay Nine]] not changed: not a record",
            "notes/Plans.md:3: Markdown link (Quay%20Nine.md) not changed: only "
            "wikilinks are rewritten",
            "reference/templates/Place.md:3: [[Quay Nine]] not changed: not a record",
        ]

    def test_nothing_for_unrelated_files(self, vault: Path) -> None:
        relinked = relinker(vault, {"content/Port Briselle.md": "content/Port.md"})
        assert relinked.unchanged() == []


class TestRelinkerPlan:
    def test_plans_every_record(self, vault: Path) -> None:
        plan = relinker(
            vault, {"content/Quay Nine.md": "campaigns/campaign_1/content/Harbour.md"}
        ).plan()
        assert sorted(p.relative_to(vault).as_posix() for p in plan.texts) == [
            "campaigns/campaign_1/sessions/S-1-001.md",
            "campaigns/campaign_2/content/Gull.md",
            "content/Quay Nine.md",
        ]
        assert plan.texts[vault / "content/Quay Nine.md"] == (
            "---\n---\n## Notes\nSee [[campaign_1/content/Harbour#Notes]].\n"
        )
        assert plan.texts[vault / "campaigns/campaign_2/content/Gull.md"] == (
            "---\n---\nAt [[campaign_2/content/Harbour]].\n"
        )
        assert len(plan.notes) == 4
        assert all(path.read_text() != plan.texts.get(path) for path in plan.texts)

    def test_refuses_unparseable_records(self, vault: Path) -> None:
        write(vault, "content/Broken.md", "---\na: [[[Quay Nine]]\n")
        with pytest.raises(ValueError, match="content/Broken.md: "):
            relinker(vault, {"content/Quay Nine.md": "content/Quay Ten.md"}).plan()


class TestDisplay:
    @pytest.mark.parametrize(
        ("target", "expected"),
        [
            ("Quay Nine", "Quay Nine"),
            ("content/Quay Nine.MD", "Quay Nine"),
            ("a/b", "b"),
        ],
    )
    def test_display(self, target: str, expected: str) -> None:
        assert _display(target) == expected


class TestQuote:
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
        assert _quote(line, line.index("[[X]]")) == expected


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
