"""Dedicated contracts for safe YAML loading, normalization and note parsing."""

from collections.abc import Iterator
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml
from yaml.nodes import MappingNode

from armarium.parse import FrontmatterLoader, Note


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
    def test_contents_and_location(self) -> None:
        note = Note(Path("example.md"), {"name": "Example"}, "## Notes\n", 4)
        assert note.path == Path("example.md")
        assert note.frontmatter == {"name": "Example"}
        assert note.body == "## Notes\n"
        assert note.body_start_line == 4
        with pytest.raises(FrozenInstanceError):
            setattr(note, "body", "changed")


class TestNoteParsedType:
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
        assert Note(Path("example.md"), metadata, "", 1).parsed_type == expected


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
        assert note == Note(path, metadata, body, start)
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
