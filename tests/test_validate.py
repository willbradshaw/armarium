"""Single-file validation outcomes and composition of parser/schema checks."""

import json
import shutil
from collections.abc import Callable
from dataclasses import FrozenInstanceError
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from armarium.index import VaultIndex
from armarium.lib import Result, check_vault, find_files, find_vault
from armarium.parse import Note
from armarium.validate import (
    LINK_TARGETS,
    Target,
    _link_targets,
    _validate_wikilink_status,
    validate,
    validate_directory,
    validate_filename,
    validate_markdown,
    validate_placement,
    validate_wikilink,
    validate_wikilinks,
)


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault with spaces"
    (root / "reference/types").mkdir(parents=True)
    (root / "reference/schemas").mkdir()
    (root / "campaigns").mkdir()
    (root / "content").mkdir()
    return root


@pytest.fixture
def write_note(vault: Path) -> Callable[..., Path]:
    (vault / "reference/types/Widget.md").write_text('---\ntype: "[[Type]]"\n---\n')

    def write(
        metadata: dict[str, Any],
        body: str = "## Notes\n",
        name: str = "content/Test.md",
    ) -> Path:
        path = vault / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\n" + yaml.safe_dump(metadata) + "---\n" + body)
        return path

    return write


def write_records(root: Path, records: dict[str, str]) -> None:
    """Write frontmatter-only records plus placed definitions of every built-in type."""
    for name in (
        "Type",
        "Content",
        "Player",
        "Session",
        "Clue",
        "Transcript",
        "Reference",
        "Status",
    ):
        records.setdefault(f"reference/types/{name}.md", 'type: "[[Type]]"')
    for relative, text in records.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\n{text}\n---\n")


class TestValidateMarkdown:
    @pytest.mark.parametrize("explicit", [False, True])
    @pytest.mark.parametrize("relative", [False, True])
    def test_valid_record(
        self,
        vault: Path,
        write_note: Callable[..., Path],
        monkeypatch: pytest.MonkeyPatch,
        explicit: bool,
        relative: bool,
    ) -> None:
        path = write_note(
            {"type": "[[types/Widget]]", "date": date(2026, 1, 2)},
            name="content/Test.MD",
        )
        schema = vault / "reference/schemas/widget.schema.json"
        schema.write_text(
            json.dumps(
                {
                    "properties": {
                        "frontmatter": {
                            "properties": {"date": {"const": "2026-01-02"}}
                        },
                        "body": {"const": "## Notes\n"},
                    }
                }
            )
        )
        before = (path.read_bytes(), schema.read_bytes())
        monkeypatch.chdir(vault.parent)
        selected = path.relative_to(vault.parent) if relative else path
        root = Path(vault.name) if relative else vault
        result = validate_markdown(selected, root if explicit else None)
        assert result.diagnostics == [] and not result.failed
        assert (result.checked, result.skipped, result.unsupported) == (1, 0, 0)
        assert (path.read_bytes(), schema.read_bytes()) == before

    @pytest.mark.parametrize(
        ("schema", "rule", "unsupported", "failed"),
        [
            (None, "schema.unsupported", 1, True),
            ("{", "schema.invalid", 0, True),
            ('{"type": 12}', "schema.invalid", 0, True),
            ('{"$ref": "https://example.invalid/schema"}', "schema.invalid", 0, True),
            ("false", "schema.instance", 0, True),
        ],
    )
    def test_schema_outcomes(
        self,
        vault: Path,
        write_note: Callable[..., Path],
        schema: str | None,
        rule: str,
        unsupported: int,
        failed: bool,
    ) -> None:
        path = write_note({"type": "[[Widget]]"})
        if schema is not None:
            (vault / "reference/schemas/widget.schema.json").write_text(schema)
        before = path.read_bytes()
        result = validate_markdown(path)
        assert (result.checked, result.skipped, result.unsupported) == (
            1,
            0,
            unsupported,
        )
        assert result.failed is failed
        assert len(result.diagnostics) == 1
        assert result.diagnostics[0].rule == rule
        assert result.diagnostics[0].path == "content/Test.md"
        assert path.read_bytes() == before

    @pytest.mark.parametrize(
        "kind", [None, 42, "Widget", "[[Widget|Alias]]", "[[Widget#Heading]]"]
    )
    @pytest.mark.parametrize(
        "name",
        [
            "content/Test.md",
            "reference/types/Widget.md",
            "reference/statuses/Hinted.md",
        ],
    )
    def test_invalid_type(
        self, vault: Path, write_note: Callable[..., Path], kind: Any, name: str
    ) -> None:
        path = write_note({"type": kind}, name=name)
        result = validate_markdown(path)
        assert result.failed
        assert (result.checked, result.skipped, result.unsupported) == (1, 0, 0)
        assert [(d.rule, d.field) for d in result.diagnostics] == [
            ("record.type", "type")
        ]

    @pytest.mark.parametrize(
        "name",
        [
            "content/Untyped.md",
            "index.md",
            "reference/Untyped.md",
            "reference/types/Untyped.md",
            "reference/statuses/Untyped.md",
            "reference/types/nested/Untyped.md",
            "reference/statuses/nested/Untyped.md",
            "campaigns/campaign_1/reference/types/Untyped.md",
            "reference/templates-copy/Untyped.md",
        ],
    )
    @pytest.mark.parametrize(
        "text", ["plain Markdown", "---\nsummary: Missing type\n---\n"]
    )
    def test_missing_type_is_an_error(self, vault: Path, name: str, text: str) -> None:
        path = vault / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        result = validate_markdown(path)
        assert result.failed
        assert (result.checked, result.skipped, result.unsupported) == (1, 0, 0)
        assert [(d.rule, d.field, d.severity) for d in result.diagnostics] == [
            ("record.type", "type", "error")
        ]
        assert "required" in result.diagnostics[0].message
        assert path.read_text() == text

    @pytest.mark.parametrize("directory", ["types", "statuses"])
    def test_typed_definitions_receive_schema_checks(
        self, vault: Path, write_note: Callable[..., Path], directory: str
    ) -> None:
        path = write_note(
            {"type": "[[Widget]]"}, name=f"reference/{directory}/Typed.md"
        )
        (vault / "reference/schemas/widget.schema.json").write_text("false")
        result = validate_markdown(path)
        assert result.failed and result.checked == 1 and result.skipped == 0
        assert result.diagnostics[0].rule == "schema.instance"

    @pytest.mark.parametrize(
        ("name", "metadata", "rule"),
        [
            (
                "reference/templates/Widget.md",
                {"type": "[[Widget]]"},
                "record.template",
            ),
            ("reference/templates/nested/Widget.md", {"type": None}, "record.template"),
        ],
    )
    def test_explicit_skips(
        self,
        vault: Path,
        write_note: Callable[..., Path],
        name: str,
        metadata: dict[str, Any],
        rule: str,
    ) -> None:
        path = write_note(metadata, name=name)
        before = path.read_bytes()
        result = validate_markdown(path)
        assert not result.failed
        assert (result.checked, result.skipped, result.unsupported) == (0, 1, 0)
        assert [(d.rule, d.severity) for d in result.diagnostics] == [(rule, "info")]
        assert path.read_bytes() == before

    @pytest.mark.parametrize(
        "name",
        [
            "content/Bad.md",
            "reference/templates/Bad.md",
            "reference/types/Bad.md",
            "reference/statuses/Bad.md",
        ],
    )
    def test_parse_errors_precede_skips(self, vault: Path, name: str) -> None:
        path = vault / name
        path.parent.mkdir(parents=True, exist_ok=True)
        text = "---\nname: first\nname: second\n---\n"
        path.write_text(text)
        result = validate_markdown(path)
        assert result.failed
        assert (result.checked, result.skipped, result.unsupported) == (1, 0, 0)
        assert [(d.rule, d.line) for d in result.diagnostics] == [("parse.invalid", 3)]
        assert path.read_text() == text

    def test_selected_file_only_and_diagnostic_order(
        self, vault: Path, write_note: Callable[..., Path]
    ) -> None:
        path = write_note({"type": "[[Widget]]"})
        (vault / "content/Unrelated.md").write_text("---\nbroken: [\n---\n")
        (vault / "reference/schemas/widget.schema.json").write_text(
            json.dumps(
                {
                    "properties": {
                        "frontmatter": {"type": "array"},
                        "body": {"type": "integer"},
                    }
                }
            )
        )
        result = validate_markdown(path)
        assert result.checked == 1
        assert [d.field for d in result.diagnostics] == ["body", "frontmatter"]
        assert all(d.path == "content/Test.md" for d in result.diagnostics)

    @pytest.mark.parametrize(
        "problem",
        [
            "missing",
            "directory",
            "extension",
            "symlink",
            "outside-vault",
            "unknown-vault",
        ],
    )
    def test_invocation_errors(self, vault: Path, tmp_path: Path, problem: str) -> None:
        path = vault / "content/note.md"
        root: Path | None = vault
        if problem == "directory":
            path.mkdir()
        elif problem == "extension":
            path = path.with_suffix(".json")
            path.write_text("{}")
        elif problem == "symlink":
            target = vault / "content/target.md"
            target.write_text("note")
            path.symlink_to(target)
        elif problem in {"outside-vault", "unknown-vault"}:
            path = tmp_path / "outside.md"
            path.write_text("note")
            if problem == "unknown-vault":
                root = None
        with pytest.raises(ValueError):
            validate_markdown(path, root)

    def test_explicit_incomplete_vault(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"
        path.write_text('---\ntype: "[[Widget]]"\n---\n')
        result = validate_markdown(path, tmp_path)
        assert result.unsupported == 1 and result.failed

    @pytest.mark.parametrize(
        "kind",
        [
            "content",
            "clue",
            "session",
            "transcript",
            "player",
            "reference",
            "type",
            "status",
        ],
    )
    @pytest.mark.parametrize("source", ["starter", "example"])
    def test_shipped_schema_integration(
        self, tmp_path: Path, kind: str, source: str
    ) -> None:
        root = tmp_path / "copied vault"
        shutil.copytree(Path("vaults") / source, root)
        fixture = json.loads(Path(f"tests/schemas/fixtures/{kind}.json").read_text())[
            "base"
        ]
        path = root / "selected.md"
        path.write_text(
            "---\n" + yaml.safe_dump(fixture["frontmatter"]) + "---\n" + fixture["body"]
        )
        before = path.read_bytes()
        result = validate_markdown(path)
        # These schema fixtures are not complete contextual vault fixtures.
        assert not any(
            d.rule.startswith(("schema.", "parse.")) for d in result.diagnostics
        )
        assert (result.checked, result.skipped, result.unsupported) == (1, 0, 0)
        assert path.read_bytes() == before

    @pytest.mark.parametrize("source", ["starter", "example"])
    @pytest.mark.parametrize("folder", ["types", "statuses"])
    def test_shipped_definitions_are_checked(
        self, tmp_path: Path, source: str, folder: str
    ) -> None:
        root = tmp_path / "copied vault"
        shutil.copytree(Path("vaults") / source, root)
        paths = sorted((root / "reference" / folder).glob("*.md"))
        assert paths
        for path in paths:
            before = path.read_bytes()
            result = validate_markdown(path)
            assert result.diagnostics == [], path
            assert (result.checked, result.skipped, result.unsupported) == (1, 0, 0)
            assert path.read_bytes() == before

    @pytest.mark.parametrize("declared_type", ["Type", "Status"])
    def test_definition_schema_errors(self, tmp_path: Path, declared_type: str) -> None:
        root = tmp_path / "copied vault"
        shutil.copytree(Path("vaults/starter"), root)
        folder = "types" if declared_type == "Type" else "statuses"
        path = root / "reference" / folder / "Invalid.md"
        # Both are canonical links, but violate the declared type's schema:
        # Type requires [[Type]], and Status requires applies_to metadata.
        link = "[[types/Type]]" if declared_type == "Type" else "[[Status]]"
        path.write_text(f'---\ntype: "{link}"\n---\n')
        result = validate_markdown(path)
        assert result.failed and result.checked == 1 and result.skipped == 0
        assert result.diagnostics[0].rule == "schema.instance"

    def test_rejects_different_vault(self, tmp_path: Path) -> None:
        from armarium.index import VaultIndex

        root = tmp_path / "vault"
        root.mkdir()
        path = root / "note.md"
        path.write_text("note")
        with pytest.raises(ValueError, match="index must belong"):
            validate_markdown(path, root, index=VaultIndex(tmp_path))

    def test_shared_index(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        from armarium.index import VaultIndex
        from armarium.parse import Note

        (tmp_path / "reference/types").mkdir(parents=True)
        (tmp_path / "reference/schemas").mkdir()
        (tmp_path / "reference/schemas/widget.schema.json").write_text("true")
        for name in ("a", "b", "Widget"):
            (tmp_path / f"{name}.md").write_text('---\ntype: "[[Widget]]"\n---\n')
        with patch("armarium.validate.VaultIndex", wraps=VaultIndex) as build:
            with patch.object(Note, "parse", wraps=Note.parse) as parse:
                validate_directory(tmp_path, tmp_path)
        assert build.call_count == 1
        assert parse.call_count == 3


class TestValidateDirectory:
    @pytest.mark.parametrize("relative", [False, True])
    def test_matches_individual_checks(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, relative: bool
    ) -> None:
        from dataclasses import replace

        records = {
            "content/good.MD": '---\ntype: "[[types/Widget]]"\n---\n',
            "reference/types/Widget.md": '---\ntype: "[[Type]]"\n---\n',
            "reference/types/Type.md": '---\ntype: "[[Type]]"\n---\n',
            "content/nested/bad.md": "---\nx: [\n---\n",
            "content/untyped.md": "No type",
            "content/unknown.md": '---\ntype: "[[Unknown]]"\n---\n',
            "reference/templates/Widget.md": "---\n---\n",
        }
        (vault / "reference/schemas/widget.schema.json").write_text("true")
        (vault / "reference/schemas/type.schema.json").write_text("true")
        for name, text in records.items():
            file = vault / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(text)
        before = {p: p.read_bytes() for p in find_files(vault)}
        monkeypatch.chdir(vault.parent)
        target = Path(vault.name) if relative else vault
        result = validate_directory(target)
        individual = [validate_markdown(vault / name) for name in sorted(records)]
        assert result == Result(
            diagnostics=sorted(d for r in individual for d in r.diagnostics),
            checked=6,
            skipped=1,
            unsupported=1,
        )
        subtree = validate_directory(target / "content")
        assert subtree.checked == 4 and subtree.skipped == 0
        assert subtree.diagnostics == sorted(
            replace(d, path=d.path.removeprefix("content/"))
            for r in individual
            for d in r.diagnostics
            if d.path.startswith("content/")
        )
        assert result.failed_files == 3
        assert all(p.read_bytes() == data for p, data in before.items())

    def test_multiple_vaults_and_unscoped_markdown(self, tmp_path: Path) -> None:
        for name in ("a", "b"):
            root = tmp_path / name
            (root / "reference/types").mkdir(parents=True)
            (root / "campaigns").mkdir()
            (root / "same.md").write_text("Untyped")
        (tmp_path / "README.md").write_text("Repository documentation")
        result = validate_directory(tmp_path)
        assert result.checked == result.failed_files == 2
        assert [(d.path, d.rule) for d in result.diagnostics] == [
            ("a/same.md", "record.type"),
            ("b/same.md", "record.type"),
        ]

    def test_explicit_vault_without_markers(self, tmp_path: Path) -> None:
        (tmp_path / "record.md").write_text("Untyped")
        result = validate_directory(tmp_path, tmp_path)
        assert result.checked == 1
        assert result.diagnostics[0].rule == "record.type"

    def test_empty_directory(self, tmp_path: Path) -> None:
        assert validate_directory(tmp_path) == Result()

    @pytest.mark.parametrize(
        "excluded", [".git", ".obsidian", ".scratch", "__pycache__", "node_modules"]
    )
    def test_exclusions(self, vault: Path, excluded: str) -> None:
        hidden = vault / excluded
        hidden.mkdir()
        (hidden / "bad.md").write_text("Untyped")
        (vault / "image.png").write_bytes(b"not markdown")
        (vault / "view.base").write_text("filters: []")
        (vault / "link.md").symlink_to(hidden / "bad.md")
        assert validate_directory(vault) == Result()

    @pytest.mark.parametrize("kind", ["file", "missing", "symlink", "outside"])
    def test_invalid_target(self, tmp_path: Path, kind: str) -> None:
        target = tmp_path / "target"
        explicit = None
        if kind == "file":
            target.write_text("file")
        elif kind == "symlink":
            target.symlink_to(tmp_path, target_is_directory=True)
        elif kind == "outside":
            target.mkdir()
            explicit = tmp_path / "vault"
            explicit.mkdir()
        with pytest.raises(ValueError):
            validate_directory(target, explicit)

    def test_traversal_error_propagates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from unittest.mock import Mock

        monkeypatch.setattr(
            "armarium.validate.find_children",
            Mock(side_effect=PermissionError("denied")),
        )
        with pytest.raises(PermissionError, match="denied"):
            validate_directory(tmp_path)

    @pytest.mark.parametrize("name", ["starter", "example"])
    def test_shipped_vault_copy(self, tmp_path: Path, name: str) -> None:
        source = Path(__file__).resolve().parents[1] / "vaults" / name
        root = tmp_path / "copied vault"
        shutil.copytree(source, root)
        before = {p: p.read_bytes() for p in find_files(root)}
        result = validate_directory(root)
        assert not result.failed and result.unsupported == 0
        assert result.checked > 0 and result.skipped == 5
        assert all(p.read_bytes() == data for p, data in before.items())

    @pytest.mark.parametrize("explicit", [False, True])
    def test_selected_vault_applies_to_entire_subtree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, explicit: bool
    ) -> None:
        from unittest.mock import Mock

        outer = tmp_path / "outer"
        inner = outer / "nested"
        for root, schema in ((outer, "true"), (inner, "false")):
            (root / "reference/types").mkdir(parents=True)
            (root / "reference/schemas").mkdir()
            (root / "campaigns").mkdir()
            (root / "reference/schemas/widget.schema.json").write_text(schema)
            for name in ("a.md", "b.md"):
                (root / name).write_text('---\ntype: "[[Widget]]"\n---\n')
        for name in ("Widget", "Type"):
            (outer / f"reference/types/{name}.md").write_text(
                '---\ntype: "[[Type]]"\n---\n'
            )
        (outer / "reference/schemas/type.schema.json").write_text("true")
        discover = Mock(wraps=find_vault)
        check = Mock(wraps=check_vault)
        monkeypatch.setattr("armarium.validate.find_vault", discover)
        monkeypatch.setattr("armarium.validate.check_vault", check)
        # Select once for the whole subtree; explicit vaults bypass discovery.
        for _ in range(2):
            discover.reset_mock()
            check.reset_mock()
            result = validate_directory(outer, outer if explicit else None)
            assert result.checked == 6
            assert result.failed_files == 0
            inferred = [call for call in discover.call_args_list if len(call.args) == 1]
            assert len(inferred) == (0 if explicit else 1)
            if not explicit:
                assert inferred[0].args == (outer,)
            # Each file still passes through the explicit containment check.
            contained = [
                call for call in check.call_args_list if call.args[0].suffix == ".md"
            ]
            assert len(contained) == 6

    @pytest.mark.parametrize("found", [False, True])
    def test_discovers_once_per_vault_subtree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, found: bool
    ) -> None:
        from unittest.mock import Mock

        path = tmp_path / "container" / "vault"
        (path / "records/deep").mkdir(parents=True)
        if found:
            (path / "reference/types").mkdir(parents=True)
            (path / "campaigns").mkdir()
        files = [path / "records/first.md", path / "records/deep/second.md"]
        for file in files:
            file.write_text("Untyped")
        discover = Mock(wraps=find_vault)
        monkeypatch.setattr("armarium.validate.find_vault", discover)
        result = validate_directory(tmp_path)
        assert result.checked == (2 if found else 0)
        diagnostics = result.diagnostics
        assert {d.rule for d in diagnostics} == ({"record.type"} if found else set())
        assert {d.path for d in diagnostics} == (
            {
                "container/vault/records/first.md",
                "container/vault/records/deep/second.md",
            }
            if found
            else set()
        )
        inferred = [
            call.args[0] for call in discover.call_args_list if len(call.args) == 1
        ]
        expected = [tmp_path, tmp_path / "container", path]
        if not found:
            expected += [path / "records", path / "records/deep"]
        assert inferred == expected


class TestValidate:
    @pytest.mark.parametrize("directory", [False, True])
    @pytest.mark.parametrize("explicit", [False, True])
    def test_file_or_directory(
        self, vault: Path, directory: bool, explicit: bool
    ) -> None:
        for name in ("first.md", "second.md"):
            (vault / name).write_text("Untyped")
        # An incomplete vault must work when the caller provides its context.
        if explicit:
            (vault / "reference/types").rmdir()
        target = vault if directory else vault / "first.md"
        result = validate(target, vault if explicit else None)
        assert result.checked == result.failed_files == (2 if directory else 1)
        assert {d.path for d in result.diagnostics} == (
            {"first.md", "second.md"} if directory else {"first.md"}
        )
        assert {d.rule for d in result.diagnostics} == {"record.type"}

    @pytest.mark.parametrize("kind", ["missing", "text", "file-link", "directory-link"])
    def test_invalid_target(self, tmp_path: Path, kind: str) -> None:
        target = tmp_path / "target.txt"
        if kind == "text":
            target.write_text("Text")
        elif kind == "file-link":
            original = tmp_path / "note.md"
            original.write_text("Untyped")
            target.symlink_to(original)
        elif kind == "directory-link":
            target.symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(ValueError):
            validate(target, tmp_path)


class TestValidateWikilinks:
    @pytest.mark.parametrize(
        "text, rule",
        [
            ("[[target|Alias]] [[target.md#Heading]] [[#^block]] ![[image.png]]", None),
            ("[[missing]]", "link.missing"),
            ("[[broken", "link.syntax"),
            ("```markdown\n[[missing]]\n```", "link.missing"),
            ("```dataview\n[[missing]]\n```", "link.missing"),
            ("`[[missing]]`", "link.missing"),
            ("`= [[missing]].text`", "link.missing"),
        ],
    )
    def test_body(self, tmp_path: Path, text: str, rule: str | None) -> None:
        for name, body in {
            "selected.md": text,
            "target.md": "plain",
            "image.png": "asset",
        }.items():
            (tmp_path / name).write_text(body)
        note = Note(tmp_path / "selected.md", {}, text, 5)
        result = validate_wikilinks(note, VaultIndex(tmp_path))
        assert [d.rule for d in result] == ([rule] if rule else [])
        if result:
            assert result[0].path == "selected.md"
            assert result[0].line == (6 if text.startswith("```") else 5)

    def test_metadata_and_recovery(self, tmp_path: Path) -> None:
        note = Note(
            tmp_path / "selected.md",
            {"nested": ["[[missing]]"]},
            "[[broken [[other]]",
            8,
        )
        result = validate_wikilinks(note, VaultIndex(tmp_path))
        assert [(d.rule, d.field, d.line) for d in result] == [
            ("link.missing", "nested.0", 0),
            ("link.syntax", "", 8),
            ("link.missing", "", 8),
        ]

    @pytest.mark.parametrize(
        "metadata, expected",
        [
            ({"type": "[[Clue]]", "status": "[[Pending]]"}, []),
            (
                {"type": "[[Type]]", "status": "[[Pending]]"},
                [("status.applicability", "status")],
            ),
            ({"type": "[[Pending]]"}, [("link.type", "type")]),
            ({"type": "[[Clue]]", "status": "[[Clue]]"}, [("link.type", "status")]),
            ({"type": "[[Clue]]", "status": ["[[Clue]]"]}, [("link.type", "status.0")]),
            (
                {"type": "[[Clue]]", "status": "[[missing]]"},
                [("link.missing", "status")],
            ),
            ({"type": "[[Clue]]", "applies_to": "[[Pending]]"}, []),
            ({"status": "[[Clue]]"}, [("link.type", "status")]),
            ({"type": "[[Clue]]", "other": {"type": "[[Pending]]"}}, []),
            (
                {"type": "[[Status]]", "applies_to": "[[Pending]]"},
                [("link.type", "applies_to")],
            ),
        ],
    )
    def test_typed_fields(
        self,
        tmp_path: Path,
        metadata: dict[str, object],
        expected: list[tuple[str, str]],
    ) -> None:
        for name, text in {
            "reference/types/Clue.md": 'type: "[[Type]]"',
            "reference/types/Status.md": 'type: "[[Type]]"',
            "reference/types/Type.md": 'type: "[[Type]]"',
            "reference/statuses/Pending.md": 'type: "[[Status]]"\napplies_to: "[[Clue]]"',
        }.items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"---\n{text}\n---\n")
        note = Note(tmp_path / "selected.md", metadata, "", 1)
        result = validate_wikilinks(note, VaultIndex(tmp_path))
        assert [(d.rule, d.field) for d in result] == expected


class TestTarget:
    def test_defaults(self) -> None:
        assert Target("Content") == Target("Content", frozenset(), None, False)
        with pytest.raises(FrozenInstanceError):
            setattr(Target("Content"), "campaign", "campaign_1")

    @pytest.mark.parametrize(
        "relative, metadata, expected",
        [
            (
                "campaigns/campaign_42/reference/players/P.md",
                {"type": "[[Player]]", "plays": ["[[PC1]]", "[[NPC1]]"]},
                [("link.type", "plays.1")],
            ),
            (
                "campaigns/campaign_42/clues/C-42-0001.md",
                {"type": "[[Clue]]", "subjects": ["[[PC1]]", "[[Shared]]", "[[Far]]"]},
                [("campaign.mismatch", "subjects.2")],
            ),
            (
                "content/Thing.md",
                {
                    "type": "[[Content]]",
                    "custom": {"plays": "[[NPC1]]"},
                    "notes": "[[Far]]",
                },
                [],
            ),
        ],
    )
    def test_relationships(
        self,
        tmp_path: Path,
        relative: str,
        metadata: dict[str, object],
        expected: list[tuple[str, str]],
    ) -> None:
        write_records(
            tmp_path,
            {
                "campaigns/campaign_42/content/PC1.md": 'type: "[[Content]]"\nsubtype: PC',
                "campaigns/campaign_42/content/NPC1.md": 'type: "[[Content]]"\nsubtype: NPC',
                "content/Shared.md": 'type: "[[Content]]"\nsubtype: Lore',
                "campaigns/campaign_7/content/Far.md": 'type: "[[Content]]"\nsubtype: Lore',
            },
        )
        note = Note(tmp_path / relative, metadata, "", 1)
        result = validate_wikilinks(note, VaultIndex(tmp_path))
        assert [(d.rule, d.field) for d in result] == expected


class TestValidateWikilink:
    @pytest.mark.parametrize(
        "target, record_type, rule",
        [
            ("Clue", "Type", None),
            ("Clue", None, None),
            ("Clue", "Status", "link.type"),
            ("Stray", "Type", "link.type"),
            ("Untyped", "Type", "link.type"),
            ("image.png", "Type", "link.type"),
            ("missing", "Type", "link.missing"),
        ],
    )
    def test_record_type(
        self, tmp_path: Path, target: str, record_type: str | None, rule: str | None
    ) -> None:
        for name, body in {
            "reference/types/Clue.md": '---\ntype: "[[Type]]"\n---\n',
            "elsewhere/Stray.md": '---\ntype: "[[Type]]"\n---\n',
            "content/Untyped.md": "plain",
            "image.png": "asset",
        }.items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
        note = Note(tmp_path / "selected.md", {}, "", 1)
        expected = Target(record_type) if record_type else None
        problem = validate_wikilink(target, note, VaultIndex(tmp_path), expected)
        assert (problem[0] if problem else None) == rule

    @pytest.mark.parametrize(
        "metadata, subtypes, rule",
        [
            ('type: "[[Content]]"\nsubtype: PC', {"PC"}, None),
            ('type: "[[Content]]"\nsubtype: PC', set(), None),
            ('type: "[[Content]]"\nsubtype: NPC', {"PC"}, "link.type"),
            ('type: "[[Content]]"\nsubtype: [PC]', {"PC"}, "link.type"),
            ('type: "[[Content]]"', {"PC"}, "link.type"),
        ],
    )
    def test_subtype(
        self, tmp_path: Path, metadata: str, subtypes: set[str], rule: str | None
    ) -> None:
        for name, text in {
            "reference/types/Content.md": 'type: "[[Type]]"',
            "content/Target.md": metadata,
        }.items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"---\n{text}\n---\n")
        note = Note(tmp_path / "selected.md", {}, "", 1)
        expected = Target("Content", frozenset(subtypes))
        problem = validate_wikilink("Target", note, VaultIndex(tmp_path), expected)
        assert (problem[0] if problem else None) == rule

    @pytest.mark.parametrize(
        "source, relative, kind, expected, rule",
        [
            (
                "content/N.md",
                "campaigns/campaign_42/content/Target.md",
                "Content",
                Target("Content", campaign="campaign_42"),
                None,
            ),
            (
                "content/N.md",
                "campaigns/campaign_42/content/Target.md",
                "Content",
                Target("Content"),
                None,
            ),
            (
                "content/N.md",
                "campaigns/campaign_7/content/Target.md",
                "Content",
                Target("Content", campaign="campaign_42"),
                "campaign.mismatch",
            ),
            (
                "content/N.md",
                "content/Target.md",
                "Content",
                Target("Content", campaign="campaign_42"),
                None,
            ),
            (
                "content/N.md",
                "campaigns/campaign_42/sessions/S-42-001.md",
                "Session",
                Target("Session", campaign="campaign_42"),
                None,
            ),
            (
                "content/N.md",
                "campaigns/campaign_7/sessions/S-7-001.md",
                "Session",
                Target("Session", campaign="campaign_42"),
                "campaign.mismatch",
            ),
            (
                "campaigns/campaign_42/clues/C-42-0001.md",
                "campaigns/campaign_42/sessions/S-42-001.md",
                "Session",
                Target("Session", local=True),
                None,
            ),
            (
                "campaigns/campaign_42/clues/C-42-0001.md",
                "campaigns/campaign_7/sessions/S-7-001.md",
                "Session",
                Target("Session", local=True),
                "campaign.mismatch",
            ),
            (
                "campaigns/campaign_42/clues/C-42-0001.md",
                "content/Target.md",
                "Content",
                Target("Content", local=True),
                None,
            ),
            (
                "content/N.md",
                "campaigns/campaign_7/sessions/S-7-001.md",
                "Session",
                Target("Session", local=True),
                None,
            ),
        ],
    )
    def test_campaign(
        self,
        tmp_path: Path,
        source: str,
        relative: str,
        kind: str,
        expected: Target,
        rule: str | None,
    ) -> None:
        for name, text in {
            "reference/types/Content.md": 'type: "[[Type]]"',
            "reference/types/Session.md": 'type: "[[Type]]"',
            relative: f'type: "[[{kind}]]"\nsession_number: 1',
        }.items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"---\n{text}\n---\n")
        note = Note(tmp_path / source, {}, "", 1)
        problem = validate_wikilink(
            Path(relative).stem, note, VaultIndex(tmp_path), expected
        )
        assert (problem[0] if problem else None) == rule

    @pytest.mark.parametrize(
        "target, expected",
        [
            ("target", None),
            ("image.png", None),
            (
                "missing",
                (
                    "link.missing",
                    "cannot uniquely resolve [[missing]]; use a vault-relative path",
                ),
            ),
            (
                "same",
                (
                    "link.ambiguous",
                    "cannot uniquely resolve [[same]]; use a vault-relative path",
                ),
            ),
            ("bad", ("link.malformed", "referenced note bad.md cannot be parsed")),
        ],
    )
    def test_target(
        self, tmp_path: Path, target: str, expected: tuple[str, str] | None
    ) -> None:
        for name, body in {
            "target.md": "plain",
            "image.png": "asset",
            "bad.md": "---\nx: [\n---\n",
            "a/same.md": "",
            "b/same.md": "",
        }.items():
            path = tmp_path / name
            path.parent.mkdir(exist_ok=True)
            path.write_text(body)
        index = VaultIndex(tmp_path)
        note = Note(tmp_path / "selected.md", {}, "", 1)
        assert validate_wikilink(target, note, index) == expected
        parsed = {"target": "target.md", "bad": "bad.md"}.get(target)
        assert set(index.notes) == ({tmp_path / parsed} if parsed else set())


class TestValidatePlacement:
    @pytest.mark.parametrize(
        "kind, relative, valid",
        [
            ("Content", "content/Note.md", True),
            ("Content", "content/nested/Note.md", True),
            ("Content", "campaigns/campaign_42/content/nested/Note.md", True),
            ("Content", "other/Note.md", False),
            ("Session", "campaigns/campaign_42/sessions/nested/S-42-001.md", True),
            (
                "Session",
                "campaigns/campaign_42/sessions/transcripts/S-42-001.md",
                False,
            ),
            ("Clue", "campaigns/campaign_42/clues/C-42-0001.md", True),
            (
                "Transcript",
                "campaigns/campaign_42/sessions/transcripts/S-42-001 Transcript.md",
                True,
            ),
            ("Player", "campaigns/campaign_42/reference/players/Player.md", True),
            ("Player", "reference/players/Player.md", False),
            ("Type", "reference/types/Type.md", True),
            ("Status", "reference/statuses/Pending.md", True),
            ("Status", "campaigns/campaign_42/reference/statuses/Pending.md", False),
            ("Reference", "anywhere.md", True),
            ("Custom", "anywhere.md", True),
        ],
    )
    def test_placement(
        self, tmp_path: Path, kind: str, relative: str, valid: bool
    ) -> None:
        note = Note(tmp_path / relative, {"type": f"[[{kind}]]"}, "", 1)
        result = validate_placement(note, VaultIndex(tmp_path))
        assert [d.rule for d in result] == ([] if valid else ["record.placement"])
        if result:
            assert result[0].path == relative


class TestValidateFilename:
    @pytest.mark.parametrize(
        "kind, relative, ordinal, field",
        [
            ("Session", "campaigns/campaign_42/S-42-002.md", 2, None),
            ("Session", "campaigns/campaign_42/S-42-002.md", 3, "session_number"),
            ("Session", "campaigns/campaign_42/S-42-001.md", True, "session_number"),
            ("Session", "campaigns/campaign_42/S-42-001.md", None, "session_number"),
            ("Session", "campaigns/campaign_42/S-1-002.md", 2, ""),
            ("Session", "campaigns/campaign_42/S-42-02.md", 2, ""),
            ("Clue", "campaigns/campaign_42/C-42-0001.md", None, None),
            ("Clue", "campaigns/campaign_42/C-42-001.md", None, ""),
            ("Transcript", "campaigns/campaign_42/S-42-002 Transcript.md", None, None),
            ("Transcript", "campaigns/campaign_42/S-42-002.md", None, ""),
            ("Content", "campaigns/campaign_42/Anything.md", None, None),
            ("Session", "S-1-002.md", 3, None),
            ("Session", "campaigns/other/S-1-002.md", 3, None),
        ],
    )
    def test_filename(
        self,
        tmp_path: Path,
        kind: str,
        relative: str,
        ordinal: object,
        field: str | None,
    ) -> None:
        note = Note(
            tmp_path / relative,
            {"type": f"[[{kind}]]", "session_number": ordinal},
            "",
            1,
        )
        result = validate_filename(note, VaultIndex(tmp_path))
        assert [(d.rule, d.field) for d in result] == (
            [] if field is None else [("record.identity", field)]
        )


class TestValidateWikilinkStatus:
    @pytest.mark.parametrize(
        "applies_to, record_type, message",
        [
            ('applies_to: "[[types/Clue]]"', "[[Clue]]", None),
            ('applies_to: "[[Clue|Alias]]"', "[[types/Clue.md]]", None),
            (
                'applies_to: "[[Content]]"',
                "[[Clue]]",
                "status does not apply to Clue records",
            ),
            (
                "",
                "[[Clue]]",
                "status reference/statuses/Pending.md: applies_to must hold "
                "exactly one wikilink",
            ),
            (
                'applies_to: ["[[Clue]]"]',
                "[[Clue]]",
                "status reference/statuses/Pending.md: applies_to must hold "
                "exactly one wikilink",
            ),
            (
                'applies_to: "[[broken"',
                "[[Clue]]",
                "status reference/statuses/Pending.md: use [[target]] with "
                "balanced double brackets on one line",
            ),
            (
                'applies_to: "[[missing]]"',
                "[[Clue]]",
                "status reference/statuses/Pending.md: cannot uniquely resolve "
                "[[missing]]",
            ),
            (
                'applies_to: "[[Content]]"',
                "[[missing]]",
                "cannot check applicability: cannot uniquely resolve [[missing]]",
            ),
            (
                'applies_to: "[[Content]]"',
                None,
                "cannot check applicability: type must hold exactly one wikilink",
            ),
        ],
    )
    def test_applicability(
        self,
        tmp_path: Path,
        applies_to: str,
        record_type: str | None,
        message: str | None,
    ) -> None:
        for name, text in {
            "reference/types/Clue.md": 'type: "[[Type]]"',
            "reference/types/Content.md": 'type: "[[Type]]"',
            "reference/statuses/Pending.md": f'type: "[[Status]]"\n{applies_to}',
        }.items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"---\n{text}\n---\n")
        index = VaultIndex(tmp_path)
        status, _ = index.parse(tmp_path / "reference/statuses/Pending.md")
        assert status is not None
        note = Note(tmp_path / "selected.md", {"type": record_type}, "", 1)
        problem = _validate_wikilink_status(status, note, index)
        assert problem == (("status.applicability", message) if message else None)


class TestLinkTargets:
    @pytest.mark.parametrize(
        "metadata, expected",
        [
            (
                {"type": "[[Player]]"},
                {"plays": Target("Content", frozenset({"PC"}), local=True)},
            ),
            (
                {"type": "[[Content]]", "subtype": "PC"},
                {"player": Target("Player", local=True)},
            ),
            ({"type": "[[Content]]", "subtype": ["PC"]}, {}),
            ({"type": "[[Content]]", "subtype": "Lore"}, {}),
            ({"type": "[[Custom]]", "plays": "[[X]]"}, {}),
            ({}, {}),
            (
                {"type": "[[Clue]]"},
                {
                    "subjects": Target("Content", local=True),
                    "first_session": Target("Session", local=True),
                    "last_session": Target("Session", local=True),
                },
            ),
            ({"type": "[[Status]]"}, {"applies_to": Target("Type")}),
            ({"type": "[[Status]]", "subtype": "Odd"}, {"applies_to": Target("Type")}),
        ],
    )
    def test_targets(
        self, tmp_path: Path, metadata: dict[str, object], expected: dict[str, Target]
    ) -> None:
        note = Note(tmp_path / "selected.md", metadata, "", 1)
        assert _link_targets(note) == LINK_TARGETS | expected
