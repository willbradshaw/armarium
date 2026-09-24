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
from armarium.lib import Findings, Result, check_vault, find_files, find_vault
from armarium.parse import Body, Frontmatter, Note
from armarium.validate import (
    CAMPAIGN_DIRECTORIES,
    CAMPAIGN_FILES,
    LINK_TARGETS,
    VAULT_DIRECTORIES,
    VAULT_STATUSES,
    VAULT_TEMPLATES,
    VAULT_TYPES,
    Target,
    _check_campaign_history,
    _link_targets,
    _read_appearances,
    _validate_wikilink_status,
    linked_note,
    validate,
    validate_appearances,
    validate_campaigns,
    validate_clue,
    validate_directory,
    validate_filename,
    validate_identity_links,
    validate_markdown,
    validate_placement,
    validate_vault,
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


def make_vault(root: Path) -> None:
    """Create the smallest vault that validate_vault accepts."""
    for relative in VAULT_DIRECTORIES + tuple(
        f"campaigns/campaign_1/{d}" for d in CAMPAIGN_DIRECTORIES
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    for relative in (
        *(f"reference/types/{name}.md" for name in VAULT_TYPES),
        *(f"reference/statuses/{name}.md" for name in VAULT_STATUSES),
        *(f"reference/templates/{name}.md" for name in VAULT_TEMPLATES),
        *(f"campaigns/campaign_1/{name}" for name in CAMPAIGN_FILES),
    ):
        (root / relative).write_text("")
    for name in VAULT_TYPES:
        (root / f"reference/schemas/{name.lower()}.schema.json").write_text("true")


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
        # The vault root is the target, so its infrastructure is checked too;
        # the content/ subtree below is not a root and gets record checks only.
        assert result == Result(
            diagnostics=sorted(
                [d for r in individual for d in r.diagnostics]
                + [replace(d, path=".") for d in validate_vault(vault)]
            ),
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
        # Three records fail, plus the vault root for its missing infrastructure.
        assert result.failed_files == 4
        assert all(p.read_bytes() == data for p, data in before.items())

    def test_multiple_vaults_and_unscoped_markdown(self, tmp_path: Path) -> None:
        for name in ("a", "b"):
            root = tmp_path / name
            (root / "reference/types").mkdir(parents=True)
            (root / "campaigns").mkdir()
            (root / "same.md").write_text("Untyped")
        (tmp_path / "README.md").write_text("Repository documentation")
        result = validate_directory(tmp_path)
        assert result.checked == 2
        records = [d for d in result.diagnostics if d.rule == "record.type"]
        assert [(d.path, d.rule) for d in records] == [
            ("a/same.md", "record.type"),
            ("b/same.md", "record.type"),
        ]
        # Each discovered vault root also gets infrastructure checks, attributed
        # to that root, so two records and two roots fail.
        assert result.failed_files == 4
        assert {d.path for d in result.diagnostics if d.rule == "vault.required"} == {
            "a",
            "b",
        }

    def test_explicit_vault_without_markers(self, tmp_path: Path) -> None:
        from dataclasses import replace

        (tmp_path / "record.md").write_text("Untyped")
        result = validate_directory(tmp_path, tmp_path)
        assert result.checked == 1
        assert [(d.path, d.rule) for d in result.diagnostics if d.path != "."] == [
            ("record.md", "record.type")
        ]
        assert [d for d in result.diagnostics if d.path == "."] == sorted(
            replace(d, path=".") for d in validate_vault(tmp_path)
        )

    def test_empty_directory(self, tmp_path: Path) -> None:
        assert validate_directory(tmp_path) == Result()

    @pytest.mark.parametrize(
        "excluded", [".git", ".obsidian", ".scratch", "__pycache__", "node_modules"]
    )
    def test_exclusions(self, vault: Path, excluded: str) -> None:
        from dataclasses import replace

        hidden = vault / excluded
        hidden.mkdir()
        (hidden / "bad.md").write_text("Untyped")
        (vault / "image.png").write_bytes(b"not markdown")
        (vault / "view.base").write_text("filters: []")
        (vault / "link.md").symlink_to(hidden / "bad.md")
        assert validate_directory(vault) == Result(
            diagnostics=sorted(replace(d, path=".") for d in validate_vault(vault))
        )

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
            # Only the outer root fails, for its minimal infrastructure.
            assert {d.path for d in result.diagnostics} == {"."}
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
        diagnostics = [d for d in result.diagnostics if d.path != "container/vault"]
        assert {d.rule for d in diagnostics} == ({"record.type"} if found else set())
        assert (
            bool([d for d in result.diagnostics if d.path == "container/vault"])
            is found
        )
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
        assert result.checked == (2 if directory else 1)
        # A directory target is the vault root, so the root's missing
        # infrastructure is reported against "." as well; a file target is not.
        records = [d for d in result.diagnostics if d.path != "."]
        assert result.failed_files == len(records) + (1 if directory else 0)
        assert {d.path for d in records} == (
            {"first.md", "second.md"} if directory else {"first.md"}
        )
        assert {d.rule for d in records} == {"record.type"}
        assert any(d.path == "." for d in result.diagnostics) is directory

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
        note = Note(tmp_path / "selected.md", Frontmatter({}), Body(text, 5))
        result = validate_wikilinks(note, VaultIndex(tmp_path))
        assert [d.rule for d in result] == ([rule] if rule else [])
        if result:
            assert result[0].path == "selected.md"
            assert result[0].line == (6 if text.startswith("```") else 5)

    def test_metadata_and_recovery(self, tmp_path: Path) -> None:
        note = Note(
            tmp_path / "selected.md",
            Frontmatter({"nested": ["[[missing]]"]}),
            Body("[[broken [[other]]", 8),
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
        note = Note(tmp_path / "selected.md", Frontmatter(metadata), Body("", 1))
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
                    "subtype": "Object",
                    "campaign_42": {"held_by": "[[NPC1]]", "first_session": "[[PC1]]"},
                },
                [("link.type", "campaign_42.first_session")],
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
        note = Note(tmp_path / relative, Frontmatter(metadata), Body("", 1))
        result = validate_wikilinks(note, VaultIndex(tmp_path))
        assert [(d.rule, d.field) for d in result] == expected


class TestLinkedNote:
    @pytest.mark.parametrize(
        "target, expected, result",
        [
            ("Clue", None, "note"),
            ("Clue", Target("Type"), "note"),
            ("image.png", None, None),
            ("", None, "self"),
            ("image.png", Target("Type"), "link.type"),
            ("Clue", Target("Status"), "link.type"),
            ("missing", None, "link.missing"),
            ("missing", Target("Type"), "link.missing"),
        ],
    )
    def test_result(
        self, tmp_path: Path, target: str, expected: Target | None, result: str | None
    ) -> None:
        write_records(tmp_path, {})
        (tmp_path / "image.png").write_text("asset")
        note = Note(
            tmp_path / "reference/types/Clue.md",
            Frontmatter({"type": "[[Type]]"}),
            Body(""),
        )
        index = VaultIndex(tmp_path)
        outcome = linked_note(target, note, index, expected)
        if result in {"note", "self"}:
            assert isinstance(outcome, Note)
            assert outcome.path == tmp_path / "reference/types/Clue.md"
        elif result is None:
            assert outcome is None
        else:
            assert isinstance(outcome, tuple) and outcome[0] == result


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
        note = Note(tmp_path / "selected.md", Frontmatter({}), Body("", 1))
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
        note = Note(tmp_path / "selected.md", Frontmatter({}), Body("", 1))
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
        note = Note(tmp_path / source, Frontmatter({}), Body("", 1))
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
        note = Note(tmp_path / "selected.md", Frontmatter({}), Body("", 1))
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
        note = Note(
            tmp_path / relative, Frontmatter({"type": f"[[{kind}]]"}), Body("", 1)
        )
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
            ("Content", "Anything.md", None, None),
            ("Session", "S-1-002.md", 2, ""),
            ("Session", "campaigns/other/S-1-002.md", 2, ""),
            ("Clue", "clues/C-1-0001.md", None, ""),
            ("Transcript", "S-1-002 Transcript.md", None, ""),
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
            Frontmatter({"type": f"[[{kind}]]", "session_number": ordinal}),
            Body("", 1),
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
        note = Note(
            tmp_path / "selected.md", Frontmatter({"type": record_type}), Body("", 1)
        )
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
                    "text": Target("Content", local=True),
                    "subjects": Target("Content", local=True),
                    "first_session": Target("Session", local=True),
                    "last_session": Target("Session", local=True),
                },
            ),
            ({"type": "[[Status]]"}, {"applies_to": Target("Type")}),
            ({"type": "[[Status]]", "subtype": "Odd"}, {"applies_to": Target("Type")}),
            (
                {"type": "[[Clue]]", "status": "[[Superseded]]"},
                {
                    "text": Target("Content", local=True),
                    "subjects": Target("Content", local=True),
                    "first_session": Target("Session", local=True),
                    "last_session": Target("Session", local=True),
                    "superseded_by": Target("Clue", local=True),
                },
            ),
            (
                {
                    "type": "[[Content]]",
                    "subtype": "Object",
                    "campaign_42": {},
                    "campaign_7": None,
                    "campaign_extra": {},
                },
                {
                    "campaign_42.first_session": Target(
                        "Session", campaign="campaign_42"
                    ),
                    "campaign_42.last_session": Target(
                        "Session", campaign="campaign_42"
                    ),
                    "campaign_42.held_by": Target(
                        "Content", frozenset({"PC", "NPC", "Faction"}), "campaign_42"
                    ),
                },
            ),
            (
                {"type": "[[Content]]", "subtype": "Lore", "campaign_42": {}},
                {
                    "campaign_42.first_session": Target(
                        "Session", campaign="campaign_42"
                    ),
                    "campaign_42.last_session": Target(
                        "Session", campaign="campaign_42"
                    ),
                },
            ),
        ],
    )
    def test_targets(
        self, tmp_path: Path, metadata: dict[str, object], expected: dict[str, Target]
    ) -> None:
        write_records(
            tmp_path, {"reference/statuses/Superseded.md": 'type: "[[Status]]"'}
        )
        note = Note(tmp_path / "selected.md", Frontmatter(metadata), Body("", 1))
        assert _link_targets(note, VaultIndex(tmp_path)) == LINK_TARGETS | expected


class TestValidateCampaigns:
    @pytest.mark.parametrize(
        "relative, metadata, expected",
        [
            ("content/N.md", {"type": "[[Content]]", "campaign_42": {}}, []),
            (
                "campaigns/campaign_42/content/N.md",
                {"type": "[[Content]]", "campaign_42": {}},
                [],
            ),
            (
                "campaigns/campaign_7/content/N.md",
                {"type": "[[Content]]", "campaign_42": {}},
                [("campaign.mismatch", "campaign_42")],
            ),
            (
                "content/N.md",
                {"type": "[[Content]]", "campaign_9": {}},
                [("campaign.mismatch", "campaign_9")],
            ),
            (
                "content/N.md",
                {"type": "[[Content]]", "campaign_9": None, "campaign_extra": {}},
                [("campaign.block", "campaign_9")],
            ),
            (
                "campaigns/campaign_42/content/N.md",
                {"type": "[[Content]]", "campaign_42": "[[Session]]"},
                [("campaign.block", "campaign_42")],
            ),
            (
                "campaigns/campaign_7/clues/C.md",
                {"type": "[[Clue]]", "campaign_9": {}},
                [],
            ),
            (
                "campaigns/seven/clues/C.md",
                {"type": "[[Clue]]"},
                [("campaign.name", "")],
            ),
            (
                "campaigns/campaign_7.md",
                {"type": "[[Reference]]"},
                [("campaign.name", "")],
            ),
            (
                "campaigns/campaign_x/content/N.md",
                {"type": "[[Content]]", "campaign_9": {}},
                [("campaign.name", ""), ("campaign.mismatch", "campaign_9")],
            ),
            (
                "campaigns/campaign_7/reference/Campaign.md",
                {"type": "[[Reference]]"},
                [],
            ),
        ],
    )
    def test_campaigns(
        self,
        tmp_path: Path,
        relative: str,
        metadata: dict[str, object],
        expected: list[tuple[str, str]],
    ) -> None:
        (tmp_path / "campaigns/campaign_42").mkdir(parents=True)
        (tmp_path / "campaigns/campaign_7").mkdir(parents=True)
        note = Note(tmp_path / relative, Frontmatter(metadata), Body("", 1))
        result = validate_campaigns(note, VaultIndex(tmp_path))
        assert [(d.rule, d.field) for d in result] == expected


class TestValidateIdentityLinks:
    @pytest.mark.parametrize(
        "kind, name, target, expected",
        [
            ("Session", "S-42-002", "[[reference/Campaign]]", None),
            (
                "Session",
                "S-42-002",
                "[[reference/Other]]",
                (
                    "campaign.mismatch",
                    "campaign must link to the containing campaign overview",
                ),
            ),
            (
                "Session",
                "S-42-002",
                "[[missing]]",
                (
                    "campaign.mismatch",
                    "cannot check Session identity: cannot uniquely resolve [[missing]]",
                ),
            ),
            (
                "Session",
                "S-42-002",
                None,
                (
                    "campaign.mismatch",
                    "cannot check Session identity: campaign must hold exactly one wikilink",
                ),
            ),
            ("Transcript", "S-42-002 Transcript", "[[S-42-002]]", None),
            (
                "Transcript",
                "S-42-003 Transcript",
                "[[S-42-002]]",
                (
                    "record.identity",
                    "Transcript filename must match its linked Session plus ' Transcript'",
                ),
            ),
            (
                "Transcript",
                "S-42-003 Transcript",
                "[[broken",
                (
                    "record.identity",
                    "cannot check Transcript identity: use [[target]] with balanced "
                    "double brackets on one line",
                ),
            ),
        ],
    )
    def test_links(
        self,
        tmp_path: Path,
        kind: str,
        name: str,
        target: str | None,
        expected: tuple[str, str] | None,
    ) -> None:
        write_records(
            tmp_path,
            {
                "campaigns/campaign_42/reference/Campaign.md": 'type: "[[Reference]]"',
                "campaigns/campaign_42/reference/Other.md": 'type: "[[Reference]]"',
                "campaigns/campaign_42/sessions/S-42-002.md": 'type: "[[Session]]"',
            },
        )
        field = "campaign" if kind == "Session" else "session"
        note = Note(
            tmp_path / f"campaigns/campaign_42/sessions/{name}.md",
            Frontmatter({"type": f"[[{kind}]]", field: target}),
            Body("", 1),
        )
        result = validate_identity_links(note, VaultIndex(tmp_path))
        assert [(d.rule, d.message, d.field) for d in result] == (
            [(*expected, field)] if expected else []
        )

    @pytest.mark.parametrize(
        "kind, relative, expected",
        [
            ("Content", "content/N.md", None),
            ("Clue", "campaigns/campaign_42/clues/C-42-0001.md", None),
            (
                "Session",
                "sessions/S-1-001.md",
                (
                    "campaign.mismatch",
                    "cannot check Session identity: record is outside every campaign",
                    "campaign",
                ),
            ),
            (
                "Transcript",
                "campaigns/other/S-1-001 Transcript.md",
                (
                    "record.identity",
                    "cannot check Transcript identity: record is outside every campaign",
                    "session",
                ),
            ),
        ],
    )
    def test_outside_campaign_or_other_type(
        self,
        tmp_path: Path,
        kind: str,
        relative: str,
        expected: tuple[str, str, str] | None,
    ) -> None:
        note = Note(
            tmp_path / relative, Frontmatter({"type": f"[[{kind}]]"}), Body("", 1)
        )
        result = validate_identity_links(note, VaultIndex(tmp_path))
        assert [(d.rule, d.message, d.field) for d in result] == (
            [expected] if expected else []
        )


class TestValidateVault:
    def test_minimal_vault_passes(self, tmp_path: Path) -> None:
        make_vault(tmp_path)
        (tmp_path / "notes/extra").mkdir(parents=True)
        (tmp_path / "campaigns/campaign_1/extra.md").write_text("")
        (tmp_path / "reference/schemas/README.md").write_text("")
        assert validate_vault(tmp_path) == []

    @pytest.mark.parametrize(
        "relative, kind",
        [
            ("assets", "directory"),
            ("reference/views", "directory"),
            ("reference/types/Type.md", "file"),
            ("reference/statuses/Superseded.md", "file"),
            ("reference/templates/Clue.md", "file"),
            ("campaigns/campaign_1/sessions/transcripts", "directory"),
            ("campaigns/campaign_1/reference/Campaign.md", "file"),
            ("campaigns/campaign_1/reference/indexes/Clues.md", "file"),
        ],
    )
    @pytest.mark.parametrize("symlink", [False, True])
    def test_required(
        self, tmp_path: Path, relative: str, kind: str, symlink: bool
    ) -> None:
        make_vault(tmp_path)
        path = tmp_path / relative
        directory = path.is_dir()
        if directory:
            path.rmdir()
        else:
            path.unlink()
        if symlink:
            path.symlink_to(tmp_path / "content", target_is_directory=directory)
        result = validate_vault(tmp_path)
        assert ("", "vault.required", f"required {kind} {relative} is missing") in [
            (d.path, d.rule, d.message) for d in result
        ]

    @pytest.mark.parametrize(
        "relative, message",
        [
            ("campaigns", "cannot check campaigns: campaigns/ is missing"),
            (
                "reference/types",
                "cannot check schema coverage: reference/types is missing",
            ),
            (
                "reference/schemas",
                "cannot check schema coverage: reference/schemas is missing",
            ),
        ],
    )
    def test_missing_directory_stops_dependent_checks(
        self, tmp_path: Path, relative: str, message: str
    ) -> None:
        make_vault(tmp_path)
        shutil.rmtree(tmp_path / relative)
        messages = [d.message for d in validate_vault(tmp_path)]
        assert f"required directory {relative} is missing" in messages
        assert message in messages
        # The dependent checks say they cannot run rather than reporting every
        # entry as absent or every schema as unused.
        assert not any(m.endswith("is not a campaign_N directory") for m in messages)
        assert not any("matches no Type definition" in m for m in messages)

    @pytest.mark.parametrize(
        "layout, expected",
        [
            ({}, ["campaigns/ has no campaign_N directory"]),
            (
                {"seven": True, "campaign_x": True, "notes.md": False},
                [
                    "campaigns/ has no campaign_N directory",
                    "campaigns/campaign_x is not a campaign_N directory",
                    "campaigns/notes.md is not a campaign_N directory",
                    "campaigns/seven is not a campaign_N directory",
                ],
            ),
            ({"campaign_1": True, "campaign_42": True}, []),
        ],
    )
    def test_campaign_entries(
        self, tmp_path: Path, layout: dict[str, bool], expected: list[str]
    ) -> None:
        make_vault(tmp_path)
        shutil.rmtree(tmp_path / "campaigns/campaign_1")
        for name, directory in layout.items():
            path = tmp_path / "campaigns" / name
            if directory:
                for relative in CAMPAIGN_DIRECTORIES:
                    (path / relative).mkdir(parents=True)
                for relative in CAMPAIGN_FILES:
                    (path / relative).write_text("")
            else:
                path.write_text("")
        result = validate_vault(tmp_path)
        assert (
            sorted(d.message for d in result if d.rule == "vault.campaign") == expected
        )
        assert not any(d.rule == "vault.required" for d in result)

    def test_incomplete_campaign(self, tmp_path: Path) -> None:
        make_vault(tmp_path)
        shutil.rmtree(tmp_path / "campaigns/campaign_1/reference")
        assert sorted(d.message for d in validate_vault(tmp_path)) == [
            "required directory campaigns/campaign_1/reference/indexes is missing",
            "required directory campaigns/campaign_1/reference/players is missing",
            "required file campaigns/campaign_1/reference/Campaign.md is missing",
            "required file campaigns/campaign_1/reference/indexes/Clues.md is missing",
        ]

    @pytest.mark.parametrize(
        "change, expected",
        [
            (
                {"reference/schemas/clue.schema.json": "{"},
                [("schema.invalid", "reference/schemas/clue.schema.json: ")],
            ),
            (
                {"reference/schemas/clue.schema.json": '{"type": 12}'},
                [("schema.invalid", "reference/schemas/clue.schema.json: ")],
            ),
            (
                {"reference/schemas/widget.schema.json": "true"},
                [
                    (
                        "schema.unused",
                        "reference/schemas/widget.schema.json matches no Type definition",
                    )
                ],
            ),
            (
                {"reference/schemas/settings.json": "{}"},
                [
                    (
                        "schema.unused",
                        "reference/schemas/settings.json is not named <type>.schema.json",
                    )
                ],
            ),
            (
                {"reference/types/Widget.md": ""},
                [("schema.missing", "no vault-local schema for Widget")],
            ),
            (
                {
                    "reference/types/nested/Widget.md": "",
                    "reference/schemas/widget.schema.json": "true",
                },
                [],
            ),
        ],
    )
    def test_schema_correspondence(
        self, tmp_path: Path, change: dict[str, str], expected: list[tuple[str, str]]
    ) -> None:
        make_vault(tmp_path)
        for relative, text in change.items():
            path = tmp_path / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        result = validate_vault(tmp_path)
        assert len(result) == len(expected)
        for diagnostic, (rule, message) in zip(result, expected, strict=True):
            assert (diagnostic.rule, diagnostic.message[: len(message)]) == (
                rule,
                message,
            )

    @pytest.mark.parametrize("name", ["example", "starter"])
    def test_shipped_vaults(self, name: str) -> None:
        root = Path(__file__).resolve().parents[1] / "vaults" / name
        assert validate_vault(root) == []


class TestValidateAppearances:
    BODY = "## Notes\n- N/A\n## Active Clues\n![[reference/views/content-clues.base]]\n## Appearances\n"

    def sessions(self, tmp_path: Path) -> None:
        write_records(
            tmp_path,
            {
                "campaigns/campaign_42/sessions/S-42-001.md": 'type: "[[Session]]"\nsession_number: 1',
                "campaigns/campaign_42/sessions/S-42-002.md": 'type: "[[Session]]"\nsession_number: 2',
                "campaigns/campaign_7/sessions/S-7-001.md": 'type: "[[Session]]"\nsession_number: 1',
                "campaigns/campaign_7/sessions/S-7-009.md": 'type: "[[Session]]"\nsession_number: nine',
                "campaigns/campaign_42/content/Thing.md": 'type: "[[Content]]"\nsubtype: Lore',
            },
        )

    @pytest.mark.parametrize(
        "relative, blocks, entries, expected",
        [
            (
                "content/N.md",
                {
                    "campaign_42": {
                        "first_session": "[[S-42-001]]",
                        "last_session": "[[S-42-002]]",
                    }
                },
                ["- [[S-42-001]]: Met.", "- [[S-42-002]]: Left."],
                [],
            ),
            (
                "content/N.md",
                {
                    "campaign_42": {
                        "first_session": "[[S-42-001]]",
                        "last_session": "[[S-42-001]]",
                    },
                    "campaign_7": {
                        "first_session": "[[S-7-001]]",
                        "last_session": "[[S-7-001]]",
                    },
                },
                ["- [[S-7-001]]: Elsewhere.", "- [[S-42-001]]: Met."],
                [],
            ),
            (
                "content/N.md",
                {
                    "campaign_42": {
                        "first_session": "[[S-42-001]]",
                        "last_session": "[[S-42-001]]",
                    },
                    "campaign_7": {
                        "first_session": "[[S-7-001]]",
                        "last_session": "[[S-7-001]]",
                    },
                },
                ["- [[S-42-001]]: Met.", "- [[S-7-001]]: Elsewhere."],
                [("history.order", "", 0)],
            ),
            (
                "content/N.md",
                {
                    "campaign_42": {
                        "first_session": "[[S-42-001]]",
                        "last_session": "[[S-42-001]]",
                    },
                    "campaign_7": {
                        "first_session": "[[S-7-001]]",
                        "last_session": "[[S-7-001]]",
                    },
                },
                [
                    "- [[S-7-001]]: Away.",
                    "- [[S-42-001]]: Met.",
                    "- [[S-7-001]]: Back.",
                ],
                [("history.order", "", 0), ("history.duplicate", "", 0)],
            ),
            (
                "content/N.md",
                {"campaign_42": {"first_session": None, "last_session": None}},
                ["- N/A"],
                [],
            ),
            ("content/N.md", {}, [], [("history.format", "", 5)]),
            (
                "content/N.md",
                {
                    "campaign_42": {
                        "first_session": "[[S-42-001]]",
                        "last_session": "[[S-42-001]]",
                    }
                },
                ["- N/A", "- [[S-42-001]]: Met."],
                [
                    ("history.format", "", 6),
                    ("history.range", "campaign_42.first_session", 0),
                    ("history.range", "campaign_42.last_session", 0),
                ],
            ),
            (
                "content/N.md",
                {"campaign_42": {"first_session": None, "last_session": None}},
                ["Met them.", "- [[S-42-001]]: Met."],
                [("history.format", "", 5)],
            ),
            (
                "content/N.md",
                {"campaign_42": {"first_session": None, "last_session": None}},
                ["- [[S-42-001|alias]]: Met.", "- [[S-42-001]]", "- Met [[S-42-001]]."],
                [
                    ("history.format", "", 6),
                    ("history.format", "", 7),
                    ("history.format", "", 8),
                ],
            ),
            (
                "content/N.md",
                {},
                ["- [[missing]]: Met.", "- [[Thing]]: Met."],
                [("history.entry", "", 6), ("history.entry", "", 7)],
            ),
            (
                "content/N.md",
                {"campaign_7": {"first_session": None, "last_session": None}},
                ["- [[S-7-009]]: Met."],
                [("history.entry", "", 6)],
            ),
            (
                "content/N.md",
                {
                    "campaign_42": {
                        "first_session": "[[S-42-001]]",
                        "last_session": "[[S-42-002]]",
                    }
                },
                ["- [[S-42-002]]: Left.", "- [[S-42-001]]: Met."],
                [("history.order", "", 0)],
            ),
            (
                "content/N.md",
                {
                    "campaign_42": {
                        "first_session": "[[S-42-001]]",
                        "last_session": "[[S-42-001]]",
                    }
                },
                ["- [[S-42-001]]: Met.", "- [[S-42-001]]: Met again."],
                [("history.duplicate", "", 0)],
            ),
            (
                "campaigns/campaign_7/content/N.md",
                {
                    "campaign_42": {
                        "first_session": "[[S-42-001]]",
                        "last_session": "[[S-42-001]]",
                    }
                },
                ["- [[S-42-001]]: Met."],
                [
                    ("history.campaign", "", 6),
                    ("history.range", "campaign_42.first_session", 0),
                    ("history.range", "campaign_42.last_session", 0),
                ],
            ),
            (
                "content/N.md",
                {},
                ["- [[S-42-001]]: Met."],
                [("history.block", "campaign_42", 0)],
            ),
            (
                "content/N.md",
                {
                    "campaign_42": {
                        "first_session": "[[S-42-002]]",
                        "last_session": "[[S-42-001]]",
                    }
                },
                ["- [[S-42-001]]: Met.", "- [[S-42-002]]: Left."],
                [
                    ("history.range", "campaign_42.first_session", 0),
                    ("history.range", "campaign_42.last_session", 0),
                ],
            ),
            (
                "content/N.md",
                {
                    "campaign_42": {
                        "first_session": "[[S-42-001]]",
                        "last_session": "[[S-42-001]]",
                    }
                },
                [],
                [
                    ("history.format", "", 5),
                    ("history.range", "campaign_42.first_session", 0),
                    ("history.range", "campaign_42.last_session", 0),
                ],
            ),
            (
                "content/N.md",
                {
                    "campaign_42": {
                        "first_session": "[[missing]]",
                        "last_session": ["[[S-42-001]]"],
                    }
                },
                ["- [[S-42-001]]: Met."],
                [
                    ("history.range", "campaign_42.first_session", 0),
                    ("history.range", "campaign_42.last_session", 0),
                ],
            ),
        ],
    )
    def test_history(
        self,
        tmp_path: Path,
        relative: str,
        blocks: dict[str, object],
        entries: list[str],
        expected: list[tuple[str, str, int]],
    ) -> None:
        self.sessions(tmp_path)
        metadata = {"type": "[[Content]]", "subtype": "Lore", **blocks}
        note = Note(
            tmp_path / relative,
            Frontmatter(metadata),
            Body(self.BODY + "\n".join(entries), 1),
        )
        result = validate_appearances(note, VaultIndex(tmp_path))
        assert [(d.rule, d.field, d.line) for d in result] == expected

    def test_messages(self, tmp_path: Path) -> None:
        self.sessions(tmp_path)
        note = Note(
            tmp_path / "content/N.md",
            Frontmatter(
                {
                    "type": "[[Content]]",
                    "campaign_42": {
                        "first_session": "[[S-42-002]]",
                        "last_session": None,
                    },
                }
            ),
            Body(self.BODY + "- [[S-42-001]]: Met.\n- [[nope]]: Gone.", 1),
        )
        assert [
            d.message for d in validate_appearances(note, VaultIndex(tmp_path))
        ] == [
            "cannot check appearance: cannot uniquely resolve [[nope]]; use a "
            "vault-relative path",
            "campaign_42.first_session must be [[S-42-001]]",
            "cannot check campaign_42.last_session: campaign_42.last_session must "
            "hold exactly one wikilink",
        ]

    @pytest.mark.parametrize(
        "body, expected",
        [
            ("## Notes\n- [[S-42-001]]: not appearances\n", [("history.format", 0)]),
            ("## Appearances\n- [[S-42-001]]: Met.\n## Later\n- junk\n", []),
            ("## Appearances\n\n  \n- [[S-42-001]]: Met.\n", []),
            ("## Appearances\n\n- [[S-42-001]]: Met the\n  crew at\n  the quay.\n", []),
            ("## Appearances\n* [[S-42-001]]: Met.\n", []),
            ("## Appearances\n- [[S-42-001]]: Met.\n  - nested note\n", []),
            (
                "## Appearances\n- [[S-42-001]]: Met.\n### campaign_42\n- [[S-42-002]]: Sub.\n",
                [("history.format", 3), ("history.range", 0), ("history.range", 0)],
            ),
            (
                "## Appearances\n- [[S-42-001]]: Met.\n## Appearances\n- [[S-42-002]]: Again.\n",
                [("history.format", 3), ("history.range", 0), ("history.range", 0)],
            ),
            (
                "## Appearances\n> - [[S-42-001]]: quoted\n",
                [("history.format", 3), ("history.range", 0), ("history.range", 0)],
            ),
            (
                "## Appearances\n- [[S-42-001]]: Met.\n\nStray.\n",
                [("history.format", 3), ("history.range", 0), ("history.range", 0)],
            ),
            (
                "## Appearances\n- [[S-42-001]]: Met.\n* [[S-42-001]]: Again.\n",
                [("history.format", 3), ("history.range", 0), ("history.range", 0)],
            ),
            (
                "```\n## Appearances\n- [[S-42-001]]: Met.\n```\n",
                [("history.format", 0)],
            ),
        ],
    )
    def test_sections(
        self, tmp_path: Path, body: str, expected: list[tuple[str, int]]
    ) -> None:
        self.sessions(tmp_path)
        metadata = {
            "type": "[[Content]]",
            "campaign_42": {
                "first_session": "[[S-42-001]]",
                "last_session": "[[S-42-001]]",
            },
        }
        note = Note(tmp_path / "content/N.md", Frontmatter(metadata), Body(body, 3))
        result = validate_appearances(note, VaultIndex(tmp_path))
        assert [(d.rule, d.line) for d in result] == (
            expected
            if body.startswith("## Appearances")
            else expected
            + [
                ("history.range", 0),
                ("history.range", 0),
            ]
        )

    def test_lines_follow_body_start(self, tmp_path: Path) -> None:
        self.sessions(tmp_path)
        note = Note(
            tmp_path / "content/N.md",
            Frontmatter({"type": "[[Content]]"}),
            Body("## Appearances\n- bad\n", 9),
        )
        assert [d.line for d in validate_appearances(note, VaultIndex(tmp_path))] == [
            10
        ]

    @pytest.mark.parametrize("kind", ["Clue", "Session", "Player"])
    def test_other_types(self, tmp_path: Path, kind: str) -> None:
        note = Note(
            tmp_path / "x.md",
            Frontmatter({"type": f"[[{kind}]]"}),
            Body("## Appearances\n- bad\n", 1),
        )
        assert validate_appearances(note, VaultIndex(tmp_path)) == []


class TestReadAppearances:
    def test_history_and_reports(self, tmp_path: Path) -> None:
        write_records(
            tmp_path,
            {
                "campaigns/campaign_42/sessions/S-42-001.md": 'type: "[[Session]]"\nsession_number: 1',
                "campaigns/campaign_7/sessions/S-7-003.md": 'type: "[[Session]]"\nsession_number: 3',
            },
        )
        body = "## Appearances\n- [[S-7-003]]: Away.\n- bad\n- [[S-42-001]]: Met.\n"
        note = Note(
            tmp_path / "campaigns/campaign_42/content/N.md",
            Frontmatter({"type": "[[Content]]"}),
            Body(body, 1),
        )
        index = VaultIndex(tmp_path)
        findings = Findings(note.path.relative_to(index.root).as_posix())
        assert _read_appearances(note, index, findings) == [
            ("campaign_42", 1, tmp_path / "campaigns/campaign_42/sessions/S-42-001.md")
        ]
        assert [(d.rule, d.line) for d in findings.diagnostics] == [
            ("history.format", 3),
            ("history.campaign", 2),
        ]


class TestCheckCampaignHistory:
    @pytest.mark.parametrize(
        "entries, block, expected",
        [
            (
                [(1, "S-42-001"), (2, "S-42-002")],
                {"first_session": "[[S-42-001]]", "last_session": "[[S-42-002]]"},
                [],
            ),
            ([], {"first_session": None, "last_session": None}, []),
            (
                [(2, "S-42-002"), (1, "S-42-001")],
                {"first_session": "[[S-42-001]]", "last_session": "[[S-42-002]]"},
                ["history.order"],
            ),
            (
                [(1, "S-42-001"), (1, "S-42-001")],
                {"first_session": "[[S-42-001]]", "last_session": "[[S-42-001]]"},
                ["history.duplicate"],
            ),
            ([(1, "S-42-001")], None, ["history.block"]),
            (
                [(1, "S-42-001")],
                {"first_session": "[[S-42-002]]", "last_session": "[[S-42-001]]"},
                ["history.range"],
            ),
            (
                [],
                {"first_session": "[[S-42-001]]", "last_session": None},
                ["history.range"],
            ),
        ],
    )
    def test_campaign(
        self,
        tmp_path: Path,
        entries: list[tuple[int, str]],
        block: dict[str, object] | None,
        expected: list[str],
    ) -> None:
        write_records(
            tmp_path,
            {
                "campaigns/campaign_42/sessions/S-42-001.md": 'type: "[[Session]]"\nsession_number: 1',
                "campaigns/campaign_42/sessions/S-42-002.md": 'type: "[[Session]]"\nsession_number: 2',
            },
        )
        metadata = {"type": "[[Content]]", "campaign_42": block}
        note = Note(tmp_path / "content/N.md", Frontmatter(metadata), Body("", 1))
        index = VaultIndex(tmp_path)
        findings = Findings(note.path.relative_to(index.root).as_posix())
        history = [
            (ordinal, tmp_path / f"campaigns/campaign_42/sessions/{stem}.md")
            for ordinal, stem in entries
        ]
        _check_campaign_history(note, index, "campaign_42", history, findings)
        assert [d.rule for d in findings.diagnostics] == expected


class TestValidateClue:
    def records(self, tmp_path: Path) -> None:
        write_records(
            tmp_path,
            {
                "campaigns/campaign_42/content/A.md": 'type: "[[Content]]"\nsubtype: Lore',
                "content/B.md": 'type: "[[Content]]"\nsubtype: Lore',
                "campaigns/campaign_42/sessions/S-42-001.md": 'type: "[[Session]]"\nsession_number: 1',
                "campaigns/campaign_42/sessions/S-42-002.md": 'type: "[[Session]]"\nsession_number: 2',
                "campaigns/campaign_42/sessions/S-42-009.md": 'type: "[[Session]]"\nsession_number: nine',
            },
        )

    def clue(self, tmp_path: Path, **fields: object) -> Note:
        metadata = {
            "type": "[[Clue]]",
            "text": "plain",
            "subjects": [],
            "first_session": None,
            "last_session": None,
            **fields,
        }
        return Note(
            tmp_path / "campaigns/campaign_42/clues/C-42-0001.md",
            Frontmatter(metadata),
            Body("", 1),
        )

    @pytest.mark.parametrize(
        "text, subjects, expected",
        [
            ("[[A]] met [[B]].", ["[[B]]", "[[A]]"], []),
            ("[[A|the thing]] and [[content/B]].", ["[[A]]", "[[B]]"], []),
            ("plain", [], []),
            ("plain", None, []),
            ("[[A]]", None, [("subjects", "missing [[A]]")]),
            ("[[A]] and [[B]]", ["[[A]]"], [("subjects", "missing [[B]]")]),
            ("[[A]]", ["[[A]]", "[[B]]"], [("subjects", "extra [[B]]")]),
            ("plain", ["[[B]]", "[[A]]"], [("subjects", "extra [[A]], [[B]]")]),
            (
                "[[A]] and [[nope]]",
                ["[[A]]"],
                [("text", "cannot check subjects: cannot uniquely resolve [[nope]]")],
            ),
            (
                "[[A]]",
                ["[[A]]", "[[broken"],
                [
                    (
                        "subjects.1",
                        "cannot check subjects: use [[target]] with balanced double "
                        "brackets on one line",
                    )
                ],
            ),
        ],
    )
    def test_subjects(
        self,
        tmp_path: Path,
        text: str,
        subjects: object,
        expected: list[tuple[str, str]],
    ) -> None:
        self.records(tmp_path)
        note = self.clue(tmp_path, text=text, subjects=subjects)
        result = validate_clue(note, VaultIndex(tmp_path))
        assert [(d.rule, d.field) for d in result] == [
            ("clue.subjects", field) for field, _ in expected
        ]
        for diagnostic, (_, fragment) in zip(result, expected, strict=True):
            assert fragment in diagnostic.message

    @pytest.mark.parametrize(
        "first, last, expected",
        [
            (None, None, []),
            ("[[S-42-001]]", None, []),
            ("[[S-42-001]]", "[[S-42-001]]", []),
            ("[[S-42-001]]", "[[S-42-002]]", []),
            ("[[S-42-002]]", "[[S-42-001]]", [("history.order", "last_session")]),
            (None, "[[S-42-001]]", [("history.range", "last_session")]),
            ("[[S-42-009]]", "[[S-42-001]]", [("history.order", "first_session")]),
            ("[[missing]]", "[[S-42-001]]", [("history.order", "first_session")]),
            ("[[S-42-001]]", ["[[S-42-002]]"], [("history.order", "last_session")]),
            ("[[S-42-001]]", "[[A]]", [("history.order", "last_session")]),
        ],
    )
    def test_session_order(
        self,
        tmp_path: Path,
        first: object,
        last: object,
        expected: list[tuple[str, str]],
    ) -> None:
        self.records(tmp_path)
        note = self.clue(tmp_path, first_session=first, last_session=last)
        result = validate_clue(note, VaultIndex(tmp_path))
        assert [(d.rule, d.field) for d in result] == expected
        assert all(
            d.message.startswith("cannot order") or d.rule == "history.range"
            for d in result
            if d.field == "first_session" or first is None
        )

    @pytest.mark.parametrize("kind", ["Content", "Session", "Player"])
    def test_other_types(self, tmp_path: Path, kind: str) -> None:
        note = Note(
            tmp_path / "x.md",
            Frontmatter({"type": f"[[{kind}]]", "text": "[[A]]"}),
            Body("", 1),
        )
        assert validate_clue(note, VaultIndex(tmp_path)) == []

    def test_text_links_are_typed(self, tmp_path: Path) -> None:
        self.records(tmp_path)
        write_records(
            tmp_path,
            {
                "campaigns/campaign_7/content/Far.md": 'type: "[[Content]]"\nsubtype: Lore',
                "campaigns/campaign_42/reference/players/P.md": 'type: "[[Player]]"',
            },
        )
        note = self.clue(
            tmp_path,
            text="[[A]] told [[P]] about [[Far]] in [[S-42-001]].",
            subjects=["[[A]]", "[[P]]", "[[Far]]", "[[S-42-001]]"],
        )
        result = validate_wikilinks(note, VaultIndex(tmp_path))
        assert [(d.rule, d.field) for d in result] == [
            ("link.type", "text"),
            ("campaign.mismatch", "text"),
            ("link.type", "text"),
            ("link.type", "subjects.1"),
            ("campaign.mismatch", "subjects.2"),
            ("link.type", "subjects.3"),
        ]
