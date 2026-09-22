"""Single-file validation outcomes and composition of parser/schema checks."""

import json
import shutil
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from armarium.validate import validate_markdown


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
            (None, "schema.unsupported", 1, False),
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
    def test_invalid_type(
        self, vault: Path, write_note: Callable[..., Path], kind: Any
    ) -> None:
        path = write_note({"type": kind})
        result = validate_markdown(path)
        assert result.failed
        assert (result.checked, result.skipped, result.unsupported) == (1, 0, 0)
        assert [(d.rule, d.field) for d in result.diagnostics] == [
            ("record.type", "type")
        ]

    @pytest.mark.parametrize(
        ("name", "metadata", "rule"),
        [
            (
                "reference/templates/Widget.md",
                {"type": "[[Widget]]"},
                "record.template",
            ),
            ("reference/templates/nested/Widget.md", {"type": None}, "record.template"),
            ("reference/types/Widget.md", {}, "record.untyped"),
            ("reference/statuses/Active.md", {}, "record.untyped"),
            ("content/Untyped.md", {"summary": "No type"}, "record.untyped"),
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
        ["content/Bad.md", "reference/templates/Bad.md", "reference/types/Bad.md"],
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
        assert result.unsupported == 1 and not result.failed

    @pytest.mark.parametrize(
        "kind", ["content", "clue", "session", "transcript", "player", "reference"]
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
        assert result.diagnostics == []
        assert (result.checked, result.skipped, result.unsupported) == (1, 0, 0)
        assert path.read_bytes() == before
