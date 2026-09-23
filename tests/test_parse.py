"""Dedicated contracts for safe YAML loading, normalization and note parsing."""

from collections.abc import Iterator
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml
from yaml.nodes import MappingNode

from armarium.parse import (
    Block,
    Body,
    Frontmatter,
    FrontmatterLoader,
    Link,
    Note,
    Section,
)


class TestFrontmatterLoader:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("name: Example", {"name": "Example"}),
            ("date: 2026-01-02", {"date": "2026-01-02"}),
            ("items: [one, two]", {"items": ["one", "two"]}),
        ],
    )
    def test_safe_values(self, text: str, expected: dict[str, Any]) -> None:
        assert yaml.load(text, Loader=FrontmatterLoader) == expected

    def test_rejects_python_objects(self) -> None:
        with pytest.raises(yaml.constructor.ConstructorError):
            yaml.load("!!python/object:builtins.object {}", Loader=FrontmatterLoader)


class TestFrontmatterLoaderConstructMapping:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("{}", {}),
            ("name: Example\nitems: [one]", {"name": "Example", "items": ["one"]}),
        ],
    )
    def test_mapping(self, text: str, expected: dict[str, Any]) -> None:
        loader = FrontmatterLoader(text)
        try:
            node = loader.get_single_node()
            assert isinstance(node, MappingNode)
            assert loader.construct_mapping(node, deep=True) == expected
        finally:
            loader.dispose()

    @pytest.mark.parametrize(
        ("text", "exception", "message"),
        [
            (
                "name: first\nname: second",
                yaml.constructor.ConstructorError,
                "duplicate key",
            ),
            (
                "outer: {name: first, name: second}",
                yaml.constructor.ConstructorError,
                "duplicate key",
            ),
            ("? [one, two]\n: value", ValueError, "keys must be strings"),
        ],
    )
    def test_invalid_mapping(
        self, text: str, exception: type[Exception], message: str
    ) -> None:
        loader = FrontmatterLoader(text)
        try:
            node = loader.get_single_node()
            assert isinstance(node, MappingNode)
            with pytest.raises(exception, match=message):
                loader.construct_mapping(node, deep=True)
        finally:
            loader.dispose()


class TestFrontmatterLoaderGetSingleData:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("", None),
            ("date: 2026-01-02", {"date": "2026-01-02"}),
            ("dates: [2026-01-02T03:04:00Z]", {"dates": ["2026-01-02T03:04:00+00:00"]}),
            (
                "first: &items [2026-01-02]\nsecond: *items",
                {"first": ["2026-01-02"], "second": ["2026-01-02"]},
            ),
        ],
    )
    def test_normalized_document(self, text: str, expected: Any) -> None:
        loader = FrontmatterLoader(text)
        try:
            assert loader.get_single_data() == expected
        finally:
            loader.dispose()

    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("x: .nan", "non-JSON"),
            ("1: value", "keys must be strings"),
            ("x: &x [*x]", "recursive YAML aliases"),
        ],
    )
    def test_invalid_document(self, text: str, message: str) -> None:
        loader = FrontmatterLoader(text)
        try:
            with pytest.raises(ValueError, match=message):
                loader.get_single_data()
        finally:
            loader.dispose()


class TestFrontmatterLoaderNormalize:
    @pytest.fixture
    def loader(self) -> Iterator[FrontmatterLoader]:
        loader = FrontmatterLoader("")
        try:
            yield loader
        finally:
            loader.dispose()

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, None),
            ("text", "text"),
            (True, True),
            (42, 42),
            (1.25, 1.25),
            (date(2026, 1, 2), "2026-01-02"),
            (
                datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc),
                "2026-01-02T03:04:00+00:00",
            ),
            ({"dates": [date(2026, 1, 2)]}, {"dates": ["2026-01-02"]}),
        ],
    )
    def test_json_values(
        self, loader: FrontmatterLoader, value: Any, expected: Any
    ) -> None:
        result = loader._normalize(value)
        assert result == expected
        assert type(result) is type(expected)

    @pytest.mark.parametrize(
        ("value", "message"),
        [
            ({1: "value"}, "keys must be strings"),
            (float("nan"), "non-JSON"),
            (float("inf"), "non-JSON"),
            (-float("inf"), "non-JSON"),
            (b"bytes", "non-JSON"),
            ({"set"}, "non-JSON"),
        ],
    )
    def test_invalid_values(
        self, loader: FrontmatterLoader, value: Any, message: str
    ) -> None:
        with pytest.raises(ValueError, match=message):
            loader._normalize(value)

    @pytest.mark.parametrize("container", [[], {}], ids=["list", "mapping"])
    def test_cycles(self, loader: FrontmatterLoader, container: Any) -> None:
        if isinstance(container, list):
            container.append(container)
        else:
            container["self"] = container
        with pytest.raises(ValueError, match="recursive YAML aliases"):
            loader._normalize(container)

    def test_shared_aliases_are_copied_without_mutating_input(
        self, loader: FrontmatterLoader
    ) -> None:
        shared = [date(2026, 1, 2)]
        source = {"first": shared, "second": shared}
        result = loader._normalize(source)
        assert result == {"first": ["2026-01-02"], "second": ["2026-01-02"]}
        assert result["first"] is not result["second"]
        assert source["first"] is source["second"] is shared
        assert shared == [date(2026, 1, 2)]


class TestNote:
    def test_contents(self) -> None:
        note = Note(
            Path("example.md"), Frontmatter({"name": "Example"}), Body("## Notes\n", 4)
        )
        assert note.path == Path("example.md")
        assert note.frontmatter == {"name": "Example"}
        assert note.body == Body("## Notes\n", 4)
        with pytest.raises(FrozenInstanceError):
            setattr(note, "body", Body("changed", 1))


class TestNoteLinks:
    def test_frontmatter_then_body(self) -> None:
        note = Note(
            Path("example.md"),
            Frontmatter({"nested": ["[[Meta]]"]}),
            Body("[[broken [[Other]]\n", 8),
        )
        assert note.links == (
            Link("Meta", "nested.0", 0),
            Link("", "", 8, "use [[target]] with balanced double brackets on one line"),
            Link("Other", "", 8),
        )


class TestFrontmatter:
    def test_mapping(self) -> None:
        frontmatter = Frontmatter({"type": "[[Content]]", "n": 1})
        assert frontmatter["n"] == 1 and frontmatter.get("missing") is None
        assert dict(frontmatter) == {"type": "[[Content]]", "n": 1}
        assert list(frontmatter) == ["type", "n"] and len(frontmatter) == 2
        assert frontmatter == {"type": "[[Content]]", "n": 1}
        assert Frontmatter() == {} and Frontmatter(frontmatter) == frontmatter
        assert repr(Frontmatter({"a": 1})) == "Frontmatter({'a': 1})"


class TestFrontmatterType:
    @pytest.mark.parametrize(
        ("metadata", "expected"),
        [
            ({"type": "[[Content]]"}, "Content"),
            ({"type": "[[types/Content.md]]"}, "Content"),
            ({}, None),
            ({"type": None}, None),
            ({"type": 42}, None),
            ({"type": "[[types/Content|Alias]]"}, None),
            ({"type": "[[Content#Heading]]"}, None),
            ({"type": "[[ ]]"}, None),
            ({"type": "Content"}, None),
        ],
    )
    def test_declared_type(
        self, metadata: dict[str, Any], expected: str | None
    ) -> None:
        assert Frontmatter(metadata).type == expected


class TestFrontmatterCampaigns:
    def test_mappings_only(self) -> None:
        frontmatter = Frontmatter(
            {
                "campaign_2": {"first_session": None},
                "campaign_1": {},
                "campaign_x": {},
                "campaign_3": None,
                "campaign_4": "[[S]]",
                "other": {},
            }
        )
        assert frontmatter.campaigns == {
            "campaign_2": {"first_session": None},
            "campaign_1": {},
        }


class TestLink:
    @pytest.mark.parametrize(
        ("location", "field"),
        [
            ("", ""),
            ("status", "status"),
            ("subjects.0", "subjects"),
            ("campaign_1.held_by.2", "campaign_1.held_by"),
            ("custom.1.links.0.0", "custom.links"),
        ],
    )
    def test_field(self, location: str, field: str) -> None:
        assert Link("Target", location, 0).field == field


class TestFrontmatterLinks:
    @pytest.mark.parametrize(
        ("metadata", "expected"),
        [
            (
                {"subjects": ["[[First]]", "[[Second]]"]},
                (Link("First", "subjects.0", 0), Link("Second", "subjects.1", 0)),
            ),
            (
                {"campaign_1": {"first_session": "[[Session]]"}},
                (Link("Session", "campaign_1.first_session", 0),),
            ),
            (
                {
                    "custom": [None, {"links": [["[[Nested]]"]]}, "[[Last]]"],
                    "after": "[[After|Alias]] [[After.md#Heading]]",
                },
                (
                    Link("Nested", "custom.1.links.0.0", 0),
                    Link("Last", "custom.2", 0),
                    Link("After", "after", 0),
                    Link("After.md", "after", 0),
                ),
            ),
            (
                {
                    "count": 1,
                    "flag": False,
                    "fraction": 1.5,
                    "empty": None,
                    "list": [],
                    "mapping": {},
                    "summary": "plain text",
                },
                (),
            ),
            (
                {"subjects": ["[[broken", "[[Missing]]"]},
                (
                    Link(
                        "",
                        "subjects.0",
                        0,
                        "use [[target]] with balanced double brackets on one line",
                    ),
                    Link("Missing", "subjects.1", 0),
                ),
            ),
        ],
    )
    def test_frontmatter(
        self, metadata: dict[str, Any], expected: tuple[Link, ...]
    ) -> None:
        from copy import deepcopy

        original = deepcopy(metadata)
        frontmatter = Frontmatter(metadata)
        assert frontmatter.links == expected
        assert frontmatter.links is frontmatter.links
        assert frontmatter == original


FENCE = "`" * 3


class TestBodyLinks:
    def test_lines(self) -> None:
        body = Body(
            f"[[broken [[Other]]\n\n{FENCE}\n[[#^block]] ![[image.png]]\n{FENCE}\n", 8
        )
        assert body.links == (
            Link("", "", 8, "use [[target]] with balanced double brackets on one line"),
            Link("Other", "", 8),
            Link("", "", 11),
            Link("image.png", "", 11),
        )
        assert body.links is body.links


class TestBodySections:
    def test_tree_and_blocks(self) -> None:
        text = (
            "Preamble paragraph.\n\n"
            "# Title\n"
            "Intro ^intro\n\n"
            "## Appearances\n\n"
            "- [[S-1-001]]: Met the\n  crew. ^first\n"
            "* [[S-1-002]]: Left.\n  - nested item\n\n  Second paragraph.\n"
            "+ Third.\n\n"
            "Stray paragraph.\n\n"
            f"{FENCE}\n## Not a heading\n- [[X]]: not an item\n{FENCE}\n\n"
            "### campaign_1\n"
            "- [[S-1-003]]: Sub.\n\n"
            "Setext\n---\n"
            "1. ordered\n"
            "> quoted\n> - quoted item\n\n"
            "| a | b |\n| - | - |\n| 1 | 2 |\n\n"
            "***\n"
            "[[S-1-004]]: not a reference definition\n"
        )
        body = Body(text, 3)  # source lines are body lines + 2
        assert body.preamble == (Block("paragraph", 3, "Preamble paragraph."),)
        assert body.sections == (
            Section(
                "Title",
                1,
                5,
                (Block("paragraph", 6, "Intro", block_id="intro"),),
                (
                    Section(
                        "Appearances",
                        2,
                        8,
                        (
                            Block(
                                "list",
                                10,
                                children=(
                                    Block(
                                        "item",
                                        10,
                                        "[[S-1-001]]: Met the crew.",
                                        block_id="first",
                                    ),
                                ),
                            ),
                            Block(
                                "list",
                                12,
                                children=(
                                    Block(
                                        "item",
                                        12,
                                        "[[S-1-002]]: Left.",
                                        (
                                            Block(
                                                "list",
                                                13,
                                                children=(
                                                    Block("item", 13, "nested item"),
                                                ),
                                            ),
                                            Block("paragraph", 15, "Second paragraph."),
                                        ),
                                    ),
                                ),
                            ),
                            Block("list", 16, children=(Block("item", 16, "Third."),)),
                            Block("paragraph", 18, "Stray paragraph."),
                            Block(
                                "code", 20, "## Not a heading\n- [[X]]: not an item\n"
                            ),
                        ),
                        (
                            Section(
                                "campaign_1",
                                3,
                                25,
                                (
                                    Block(
                                        "list",
                                        26,
                                        children=(
                                            Block("item", 26, "[[S-1-003]]: Sub."),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                    Section(
                        "Setext",
                        2,
                        28,
                        (
                            Block(
                                "ordered_list",
                                30,
                                children=(Block("item", 30, "ordered"),),
                            ),
                            Block(
                                "quote",
                                31,
                                children=(
                                    Block("paragraph", 31, "quoted"),
                                    Block(
                                        "list",
                                        32,
                                        children=(Block("item", 32, "quoted item"),),
                                    ),
                                ),
                            ),
                            Block("table", 34),
                            Block("rule", 38),
                            Block(
                                "paragraph",
                                39,
                                "[[S-1-004]]: not a reference definition",
                            ),
                        ),
                    ),
                ),
            ),
        )
        assert body.sections is body.sections

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("", ()),
            ("No headings\n- item\n", ()),
            ("## A\n## B\n", (Section("A", 2, 1), Section("B", 2, 2))),
            (
                "## Empty item\n-\n- \n",
                (
                    Section(
                        "Empty item",
                        2,
                        1,
                        (
                            Block(
                                "list", 2, children=(Block("item", 2), Block("item", 3))
                            ),
                        ),
                    ),
                ),
            ),
            (
                "## Code\n    indented code\n",
                (Section("Code", 2, 1, (Block("code", 2, "indented code\n"),)),),
            ),
            ("##No space\n", ()),
            ("### Deep\n# Top\n", (Section("Deep", 3, 1), Section("Top", 1, 2))),
            (
                "## Q\n> # quoted heading\n",
                (
                    Section(
                        "Q",
                        2,
                        1,
                        (
                            Block(
                                "quote",
                                2,
                                children=(Block("heading", 2, "quoted heading"),),
                            ),
                        ),
                    ),
                ),
            ),
            (
                "## Id\nText\n^abc-1\n",
                (
                    Section(
                        "Id", 2, 1, (Block("paragraph", 2, "Text", block_id="abc-1"),)
                    ),
                ),
            ),
        ],
    )
    def test_edges(self, text: str, expected: tuple[Section, ...]) -> None:
        assert Body(text, 1).sections == expected

    def test_preamble_only(self) -> None:
        body = Body("Just text\n\n- item\n", 1)
        assert body.preamble == (
            Block("paragraph", 1, "Just text"),
            Block("list", 3, children=(Block("item", 3, "item"),)),
        )
        assert body.sections == ()


class TestNoteParse:
    @pytest.mark.parametrize(
        ("text", "metadata", "body", "start"),
        [
            ("", {}, "", 1),
            ("## Notes\n", {}, "## Notes\n", 1),
            (
                "---\nname: Example\n---\n## Notes\n",
                {"name": "Example"},
                "## Notes\n",
                4,
            ),
            ("---\n---\n", {}, "", 3),
            ("---\nnull\n---", {}, "", 4),
            (
                "\ufeff---\ndate: 2026-01-02\n---\nBody",
                {"date": "2026-01-02"},
                "Body",
                4,
            ),
            (
                "---\nfirst: &name Example\nsecond: *name\n---\n",
                {"first": "Example", "second": "Example"},
                "",
                5,
            ),
            (
                "---\r\nname: Example\r\n---\r\nBody\r\n",
                {"name": "Example"},
                "Body\n",
                4,
            ),
        ],
    )
    def test_note(
        self, tmp_path: Path, text: str, metadata: dict[str, Any], body: str, start: int
    ) -> None:
        path = tmp_path / "example.md"
        original = text.encode("utf-8")
        path.write_bytes(original)
        note, diagnostics = Note.parse(path, tmp_path)
        assert diagnostics == []
        assert note == Note(path, Frontmatter(metadata), Body(body, start))
        assert path.read_bytes() == original

    @pytest.mark.parametrize(
        ("text", "message", "line"),
        [
            ("---\nname: first\nname: second\n---\n", "duplicate key", 3),
            ("---\nname: Example", "no closing", 0),
            ("---\n[one, two]\n---", "must be a mapping", 0),
            ("---\nx: [\n---", "expected", 3),
            ("---\nx: .nan\n---", "non-JSON", 0),
            ("---\n1: value\n---", "keys must be strings", 0),
            ("---\nx: &x [*x]\n---", "recursive YAML aliases", 0),
            (
                "---\nx: !!python/object:builtins.object {}\n---",
                "could not determine",
                2,
            ),
        ],
    )
    def test_invalid_note(
        self, tmp_path: Path, text: str, message: str, line: int
    ) -> None:
        path = tmp_path / "broken.md"
        original = text.encode("utf-8")
        path.write_bytes(original)
        note, diagnostics = Note.parse(path, tmp_path)
        assert note is None and len(diagnostics) == 1
        diagnostic = diagnostics[0]
        assert (
            diagnostic.path,
            diagnostic.rule,
            diagnostic.line,
            diagnostic.severity,
        ) == ("broken.md", "parse.invalid", line, "error")
        assert message in diagnostic.message
        assert path.read_bytes() == original

    @pytest.mark.parametrize(
        "failure", ["missing", "directory", "encoding", "symlink", "parent"]
    )
    def test_read_failure(self, tmp_path: Path, failure: str) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = root / "note.md"
        if failure == "directory":
            path.mkdir()
        elif failure == "encoding":
            path.write_bytes(b"\xff")
        elif failure in {"symlink", "parent"}:
            outside = tmp_path / "outside.md"
            outside.write_text("outside")
            if failure == "symlink":
                path.symlink_to(outside)
            else:
                path = root / ".." / "outside.md"
        note, diagnostics = Note.parse(path, root)
        assert note is None and len(diagnostics) == 1
        assert diagnostics[0].rule == "parse.invalid"
        assert diagnostics[0].path == path.relative_to(root).as_posix()
        if failure in {"symlink", "parent"}:
            assert "escapes the vault boundary" in diagnostics[0].message
            assert outside.read_text() == "outside"

    def test_path_outside_root_is_a_caller_error(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            Note.parse(tmp_path / "outside.md", tmp_path / "vault")

    def test_deep_yaml_returns_a_diagnostic(self, tmp_path: Path) -> None:
        path = tmp_path / "deep.md"
        path.write_text("---\nx: " + "[" * 2000 + "0" + "]" * 2000 + "\n---\n")
        note, diagnostics = Note.parse(path, tmp_path)
        assert note is None and len(diagnostics) == 1
        assert diagnostics[0].rule == "parse.invalid"
