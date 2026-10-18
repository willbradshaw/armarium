"""Merging combines two records and repoints the links to the one that goes."""

import shutil
from pathlib import Path

import pytest

from armarium.merge import (
    Conflicts,
    Merger,
    _block_ids,
    _content,
    _empty,
    _heading,
    _join,
    _show,
    merge,
)
from armarium.parse import Frontmatter
from armarium.relink import Relinker
from armarium.validate import validate

EXAMPLE = Path(__file__).resolve().parents[1] / "vaults/example"
SILAS = "campaigns/campaign_2/content/Silas Rook.md"
OREN = "campaigns/campaign_2/content/Oren Vale.md"


@pytest.fixture
def example(tmp_path: Path) -> Path:
    root = tmp_path.resolve() / "example"
    shutil.copytree(EXAMPLE, root)
    return root


@pytest.fixture
def merger(example: Path) -> Merger:
    source, target = example / SILAS, example / OREN
    relinker = Relinker(example, {source: target}, keep_text=True)
    return Merger(example, source, target, relinker)


def settle(root: Path) -> None:
    """Edit Silas Rook so that he no longer disagrees with Oren Vale."""
    path = root / SILAS
    text = path.read_text()
    text = text.replace(text.split("summary: ")[1].split("\n")[0], "", 1)
    text = text[: text.index("- [[S-2-001]]: Asserted")] + "- N/A\n"
    path.write_text(text)


class TestConflicts:
    @pytest.mark.parametrize(
        ("conflicts", "expected"),
        [(["a"], "1 conflict; "), (["a", "b"], "2 conflicts; ")],
    )
    def test_message(self, conflicts: list[str], expected: str) -> None:
        error = Conflicts(conflicts)
        assert str(error).startswith(expected)
        assert error.details == conflicts


class TestMergerConflict:
    def test_notes(self, merger: Merger) -> None:
        merger.conflict("summary", "differs")
        assert merger.conflicts == ["summary: differs"]


class TestMergerKey:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("[[Tern]]", "campaigns/campaign_2/content/Tern.md"),
            ("[[campaign_2/content/tern.md]]", "campaigns/campaign_2/content/Tern.md"),
            ("[[Nowhere]]", "[[Nowhere]]"),
            ("[[#Notes]]", "[[#Notes]]"),
            ("text", "text"),
            (3, 3),
        ],
    )
    def test_key(
        self, merger: Merger, example: Path, value: object, expected: object
    ) -> None:
        key = merger.key(value)
        assert (
            key.relative_to(example).as_posix() if isinstance(key, Path) else key
        ) == (expected)


class TestMergerValue:
    @pytest.mark.parametrize(
        ("kept", "merged", "expected"),
        [
            ("a", None, "a"),
            (None, "b", "b"),
            ("", "b", "b"),
            ([], ["[[Tern]]"], ["[[Tern]]"]),
            ("[[Tern]]", "[[campaign_2/content/Tern]]", "[[Tern]]"),
            (
                ["[[Tern]]", "x"],
                ["[[campaign_2/content/Tern]]", "y", "y"],
                ["[[Tern]]", "x", "y"],
            ),
            ({"a": 1}, {"b": 2}, {"a": 1, "b": 2}),
        ],
    )
    def test_combines(
        self, merger: Merger, kept: object, merged: object, expected: object
    ) -> None:
        assert merger.value("field", kept, merged) == expected
        assert merger.conflicts == []

    @pytest.mark.parametrize(
        ("kept", "merged"), [("a", "b"), ("[[Tern]]", "[[Copper Finch]]"), ("a", ["a"])]
    )
    def test_conflict_keeps_the_target(
        self, merger: Merger, kept: object, merged: object
    ) -> None:
        assert merger.value("field", kept, merged) == kept
        assert len(merger.conflicts) == 1
        assert merger.conflicts[0].startswith("field: ")
        assert OREN in merger.conflicts[0] and SILAS in merger.conflicts[0]


class TestMergerMapping:
    def test_order_and_history(self, merger: Merger) -> None:
        kept = {"a": 1, "campaign_2": {"first_session": "[[S-2-001]]"}, "z": 0}
        merged = {
            "b": 2,
            "a": 1,
            "c": 3,
            "campaign_2": {"first_session": "[[S-2-002]]", "held_by": None},
            "d": 4,
        }
        assert list(merger.mapping("", kept, merged).items()) == [
            ("b", 2),
            ("a", 1),
            ("c", 3),
            ("campaign_2", {"first_session": "[[S-2-001]]", "held_by": None}),
            ("d", 4),
            ("z", 0),
        ]
        assert merger.conflicts == []


class TestMergerFrontmatter:
    def test_aliases_and_fields(self, merger: Merger) -> None:
        kept = Frontmatter({"type": "[[types/Content]]", "summary": "A", "x": None})
        merged = Frontmatter(
            {"type": "[[Content]]", "aliases": ["Rook", "oren vale"], "x": 1, "y": 2}
        )
        assert merger.frontmatter(kept, merged) == {
            "type": "[[types/Content]]",
            "summary": "A",
            "aliases": ["Rook", "Silas Rook"],
            "x": 1,
            "y": 2,
        }
        assert merger.conflicts == []

    def test_existing_aliases(self, merger: Merger) -> None:
        kept = Frontmatter({"aliases": "Captain"})
        assert merger.frontmatter(kept, Frontmatter())["aliases"] == [
            "Captain",
            "Silas Rook",
        ]

    def test_alias_taken(self, merger: Merger) -> None:
        kept = Frontmatter({"type": "[[types/Content]]"})
        merged = Frontmatter({"aliases": ["Tern"]})
        merger.frontmatter(kept, merged)
        assert merger.conflicts == [
            "aliases: Tern is already a name of campaigns/campaign_2/content/Tern.md"
        ]

    def test_link_to_itself(self, merger: Merger) -> None:
        kept = Frontmatter({"parent_location": "[[Oren Vale]]"})
        merger.frontmatter(kept, Frontmatter())
        assert merger.conflicts == [
            "parent_location: [[Oren Vale]] would link the record to itself"
        ]


class TestMergerBody:
    KEPT = (
        "\n## Notes\n\nKept.\n\n## Extra\n\nSame.\n\n## Active Clues\n\n"
        "![[kept.base]]\n\n## Appearances\n\n- [[S-2-001]]: Kept.\n"
    )

    def test_note(self, merger: Merger) -> None:
        assert merger.body("Kept.\n", "Merged.\n", "Note") == "Kept.\n\nMerged.\n"

    def test_content(self, merger: Merger) -> None:
        merged = (
            "> [!handout]\n> Words\n\n## Notes\n\nMerged.\n\n## Only\n\nNew.\n\n"
            "## Extra\n\nSame.\n\n## Active Clues\n\n![[merged.base]]\n\n"
            "## Appearances\n\n- [[S-2-002]]: Merged.\n"
        )
        assert merger.body(self.KEPT, merged, "Content") == (
            "> [!handout]\n> Words\n\n## Notes\n\nKept.\n\nMerged.\n\n## Only\n\nNew.\n\n"
            "## Extra\n\nSame.\n\n## Active Clues\n\n![[kept.base]]\n\n"
            "## Appearances\n\n- [[S-2-001]]: Kept.\n- [[S-2-002]]: Merged.\n"
        )
        assert merger.conflicts == []

    def test_extra_sections_end_a_body_without_notes(self, merger: Merger) -> None:
        assert merger.body("## A\nx\n", "## B\ny\n", "Content") == "## A\nx\n## B\ny\n"

    @pytest.mark.parametrize(
        ("merged", "conflict"),
        [
            ("> [!rules]\n> Other\n## Notes\n", "body: the text before Notes differs"),
            ("## Extra\n\nDifferent.\n", "Extra: the section differs"),
            ("## Notes\nA ^kept\n", "body: both records have the block ^kept"),
        ],
    )
    def test_conflicts(self, merger: Merger, merged: str, conflict: str) -> None:
        kept = "> [!rules]\n> Mine\n" + self.KEPT.replace(
            "Kept.\n\n## Extra", "K ^KEPT\n\n## Extra"
        )
        merger.body(kept, merged, "Content")
        assert [c for c in merger.conflicts if c.startswith(conflict)]


class TestMergerAppearances:
    def test_orders_by_campaign_and_session(
        self, merger: Merger, example: Path
    ) -> None:
        write = example / "campaigns/campaign_1/sessions/S-1-001.md"
        assert write.exists()
        result = merger.appearances(
            "## Appearances\n\n- [[S-2-002]]: Two.\n- [[S-1-001]]: One.\n\n",
            "## Appearances\n- [[S-2-001]]: First.\n- [[S-1-001]]: One.\n",
        )
        assert result == (
            "## Appearances\n\n- [[S-1-001]]: One.\n- [[S-2-001]]: First.\n"
            "- [[S-2-002]]: Two.\n\n"
        )
        assert merger.conflicts == []

    def test_none(self, merger: Merger) -> None:
        result = merger.appearances("## Appearances\n\n- N/A\n", "")
        assert result == "## Appearances\n\n- N/A\n"

    @pytest.mark.parametrize(
        ("merged", "conflict"),
        [
            ("- [[S-2-001]]: Other.\n", "both records have an item for S-2-001"),
            ("- [[Tern]]: Not a session.\n", "cannot read the item - [[Tern]]"),
            ("Prose.\n", "cannot read the item Prose."),
        ],
    )
    def test_conflicts(self, merger: Merger, merged: str, conflict: str) -> None:
        merger.appearances(
            "## Appearances\n- [[S-2-001]]: Kept.\n", "## Appearances\n" + merged
        )
        assert len(merger.conflicts) == 1
        assert merger.conflicts[0].startswith(f"Appearances: {conflict}")


class TestMergerSession:
    @pytest.mark.parametrize(
        ("contents", "expected"),
        [
            ("S-2-002", ("campaigns/campaign_2/sessions/S-2-002.md", (2, 2))),
            ("S-1-001|one", ("campaigns/campaign_1/sessions/S-1-001.md", (1, 1))),
            ("Tern", None),
            ("Nowhere", None),
            ("#Notes", None),
            ("reference/views/content-clues.base", None),
        ],
    )
    def test_session(
        self, merger: Merger, example: Path, contents: str, expected: object
    ) -> None:
        found = merger.session(contents)
        if found is not None:
            found = (found[0].relative_to(example).as_posix(), found[1])
        assert found == expected


class TestShow:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [("short", "short"), (3, "3"), ("x" * 70, "x" * 57 + "...")],
    )
    def test_show(self, value: object, expected: str) -> None:
        assert _show(value) == expected


class TestBlockIds:
    def test_block_ids(self) -> None:
        text = "A ^One\n\n- b ^two-2\n\n```\nc ^three\n```\n"
        assert _block_ids(text) == {"one", "two-2"}


class TestHeading:
    def test_heading(self) -> None:
        assert _heading("## Notes\r\nText\n") == "## Notes\r\n"


class TestContent:
    @pytest.mark.parametrize(
        ("section", "expected"), [("## Notes\nA\nB\n", "A\nB\n"), ("## Notes", "")]
    )
    def test_content(self, section: str, expected: str) -> None:
        assert _content(section) == expected


class TestEmpty:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [("", True), ("\n \n", True), ("- N/A\n", True), ("A", False)],
    )
    def test_empty(self, text: str, expected: bool) -> None:
        assert _empty(text) is expected


class TestJoin:
    @pytest.mark.parametrize(
        ("kept", "merged", "expected"),
        [
            ("\nA\n\n", "\nB\n", "\nA\n\nB\n\n"),
            ("\nA\n", "- N/A\n", "\nA\n"),
            ("\n- N/A\n\n", "\nB\n", "\nB\n\n"),
            ("A", "B", "A\n\nB\n"),
            ("A\r\n", "B\r\n", "A\r\n\r\nB\r\n"),
        ],
    )
    def test_join(self, kept: str, merged: str, expected: str) -> None:
        assert _join(kept, merged) == expected


class TestMerge:
    def test_refuses_conflicts(self, example: Path) -> None:
        before = {p: p.read_bytes() for p in example.rglob("*") if p.is_file()}
        with pytest.raises(Conflicts) as exc:
            merge(Path(SILAS), Path(OREN), example)
        assert [c.split(":")[0] for c in exc.value.details] == [
            "summary",
            "Appearances",
        ]
        assert before == {p: p.read_bytes() for p in example.rglob("*") if p.is_file()}

    def test_merges(self, example: Path) -> None:
        settle(example)
        plan = merge(Path(SILAS), Path(OREN), example)
        assert plan.changes[0].output == f"{SILAS}\t\t\tmerged into {OREN}"
        assert plan.notes[-1] == f"{OREN}: review the text merged from {SILAS}"
        assert all(change.relative != SILAS for change in plan.changes[1:])
        plan.files.apply()
        assert not (example / SILAS).exists()
        oren = (example / OREN).read_text()
        assert 'aliases: ["Silas Rook"]\n' in oren
        assert "Silas works alone" in oren
        session = (example / "campaigns/campaign_2/sessions/S-2-001.md").read_text()
        assert "[[Silas Rook]]" not in session
        assert "[[Oren Vale|Silas Rook]]" in session
        assert not validate(example).failed

    def test_broken_anchor(self, example: Path) -> None:
        settle(example)
        note = example / "campaigns/campaign_2/notes/Storm timing.md"
        note.write_text(note.read_text() + "\nSee [[Silas Rook#^gone]].\n")
        with pytest.raises(Conflicts) as exc:
            merge(Path(SILAS), Path(OREN), example)
        assert len(exc.value.details) == 1
        assert exc.value.details[0].startswith(
            "campaigns/campaign_2/notes/Storm timing.md:"
        )
        assert "names no heading or block" in exc.value.details[0]

    def test_missing_campaign_block(self, example: Path) -> None:
        settle(example)
        path = example / SILAS
        path.write_text(
            path.read_text()
            .replace("- N/A", "- [[S-2-002]]: Later.")
            .replace(
                'campaign_2:\n  first_session: "[[S-2-001]]"\n  last_session: "[[S-2-001]]"\n',
                "",
            )
        )
        oren = example / OREN
        oren.write_text(
            oren.read_text().replace(
                'campaign_2:\n  first_session: "[[S-2-001]]"\n  last_session: "[[S-2-001]]"\n',
                "",
            )
        )
        with pytest.raises(Conflicts) as exc:
            merge(Path(SILAS), Path(OREN), example)
        assert exc.value.details == [
            "campaign_2: neither record has this campaign's block"
        ]

    def test_moves_history(self, example: Path) -> None:
        settle(example)
        path = example / SILAS
        path.write_text(path.read_text().replace("- N/A", "- [[S-2-002]]: Later."))
        merge(Path(SILAS), Path(OREN), example).files.apply()
        oren = (example / OREN).read_text()
        assert 'last_session: "[[S-2-002]]"' in oren
        assert "- [[S-2-001]]: Struck" in oren and "- [[S-2-002]]: Later." in oren

    @pytest.mark.parametrize(
        ("source", "target", "message"),
        [
            (OREN, OREN, "cannot be merged into itself"),
            (SILAS, "content/Captain Mara Vey.md", None),
            ("content/Captain Mara Vey.md", OREN, "belongs to campaign_2"),
            ("content/Wake-lark.md", "content/Captain Mara Vey.md", "is a Object"),
            (
                "campaigns/campaign_2/sessions/S-2-001.md",
                "campaigns/campaign_2/sessions/S-2-002.md",
                "is a Session record",
            ),
            ("notes/Coast design notes.md", "content/Wake-lark.md", "only two Content"),
        ],
    )
    def test_refuses(
        self, example: Path, source: str, target: str, message: str | None
    ) -> None:
        if message is None:
            settle(example)
            assert merge(Path(source), Path(target), example).files.deletes
            return
        with pytest.raises(ValueError, match=message):
            merge(Path(source), Path(target), example)

    def test_notes(self, example: Path) -> None:
        notes = example / "notes"
        (notes / "A.md").write_text('---\ntype: "[[types/Note]]"\n---\nFirst.\n')
        (notes / "B.md").write_text('---\ntype: "[[types/Note]]"\n---\nSecond.\n')
        merge(notes / "A.md", notes / "B.md").files.apply()
        assert (notes / "B.md").read_text() == (
            '---\ntype: "[[types/Note]]"\naliases: ["A"]\n---\nSecond.\n\nFirst.\n'
        )
