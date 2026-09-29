"""Session numbering, local templates and creation failure recovery."""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from armarium.add import add_campaign
from armarium.parse import Record
from armarium.session import _session_number, add_session
from armarium.validate import validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "my-vault"
    shutil.copytree(ROOT / "vaults/starter", root)
    return root


class TestSessionNumber:
    @pytest.mark.parametrize(
        ("requested", "expected"), [(None, 13), (1, 1), (999, 999)]
    )
    def test_numbering(
        self, tmp_path: Path, requested: int | None, expected: int
    ) -> None:
        (tmp_path / "archive").mkdir()
        for name in (
            "S-1-003.md",
            "archive/S-1-012.md",
            "S-2-900.md",
            "S-1-050 Transcript.md",
            "notes.md",
        ):
            (tmp_path / name).write_text("")
        assert _session_number(tmp_path, 1, requested) == expected

    def test_empty_campaign(self, tmp_path: Path) -> None:
        assert _session_number(tmp_path, 1, None) == 1

    @pytest.mark.parametrize("number", [0, -1, 1000, 5])
    def test_invalid_number(self, tmp_path: Path, number: int) -> None:
        (tmp_path / "s-1-005.MD").write_text("")
        with pytest.raises(ValueError):
            _session_number(tmp_path, 1, number)

    def test_exhausted_numbers(self, tmp_path: Path) -> None:
        (tmp_path / "S-1-999.md").write_text("")
        with pytest.raises(ValueError, match="1 and 999"):
            _session_number(tmp_path, 1, None)


class TestAddSession:
    @pytest.mark.parametrize("name", ["starter", "example"])
    def test_valid_addition(self, tmp_path: Path, name: str) -> None:
        root = tmp_path / "vault with spaces"
        shutil.copytree(ROOT / "vaults" / name, root)
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        destination = add_session(root, campaign=1)
        assert destination.parent == root / "campaigns/campaign_1/sessions"
        record, _ = Record.parse(destination, root)
        assert record is not None
        assert record.frontmatter["session_number"] == int(
            destination.stem.rsplit("-", 1)[1]
        )
        assert record.frontmatter["campaign"] == "[[campaign_1/reference/Campaign]]"
        assert record.frontmatter["date"] is None
        result = validate(root)
        assert not result.failed, result.diagnostics
        assert all(p.read_bytes() == contents for p, contents in before.items())

    @pytest.mark.parametrize("nested", [False, True])
    @pytest.mark.parametrize("explicit_vault", [False, True])
    def test_campaign_inference(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        nested: bool,
        explicit_vault: bool,
    ) -> None:
        add_campaign(vault)
        monkeypatch.chdir(
            vault / "campaigns/campaign_2" / ("sessions/transcripts" if nested else "")
        )
        destination = add_session(vault if explicit_vault else None)
        assert destination.name == "S-2-001.md"
        assert not validate(destination).failed

    def test_override_and_numbering_gaps(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        add_campaign(vault)
        monkeypatch.chdir(vault / "campaigns/campaign_1")
        assert add_session(campaign=2, number=12).name == "S-2-012.md"
        assert add_session(campaign=2).name == "S-2-013.md"
        assert add_session(campaign=2, number=3).name == "S-2-003.md"
        assert add_session().name == "S-1-001.md"
        assert not validate(vault).failed

    def test_local_customizations(self, vault: Path) -> None:
        definition = vault / "reference/types/Session.md"
        definition.write_text(
            definition.read_text().replace(
                "campaign: sessions", "campaign: sessions/play"
            )
        )
        (vault / "campaigns/campaign_1/sessions/play").mkdir()
        template = vault / "reference/templates/Session.md"
        template.write_text(
            template.read_text()
            .replace("date:\n", "date: 2026-09-29\ncustom: Local value\n", 1)
            .replace(
                "## Starting scene\n- N/A",
                "## Starting scene\nLocal prep instructions.",
            )
        )
        destination = add_session(vault, campaign=1)
        assert destination.parent.name == "play"
        record, _ = Record.parse(destination, vault)
        original, _ = Record.parse(template, vault)
        assert record is not None and original is not None
        assert record.frontmatter["custom"] == "Local value"
        assert record.frontmatter["date"] == "2026-09-29"
        assert record.body.text == original.body.text
        assert not validate(vault).failed

    @pytest.mark.parametrize(
        "scenario",
        [
            "missing_campaign",
            "other_vault",
            "nested_vault",
            "outside",
            "zero",
            "nonexistent",
        ],
    )
    def test_invalid_scope(
        self,
        vault: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        scenario: str,
    ) -> None:
        monkeypatch.chdir(vault)
        if scenario == "other_vault":
            other = tmp_path / "other"
            shutil.copytree(vault, other)
            monkeypatch.chdir(other / "campaigns/campaign_1")
        selected = (
            vault / "content"
            if scenario == "nested_vault"
            else tmp_path
            if scenario == "outside"
            else vault
        )
        with pytest.raises(ValueError):
            add_session(
                selected,
                campaign=0
                if scenario == "zero"
                else 8
                if scenario == "nonexistent"
                else None,
            )
        assert not list(vault.glob("campaigns/*/sessions/S-*.md"))

    @pytest.mark.parametrize(
        "kind", ["file", "directory", "symlink", "dangling", "case", "archived"]
    )
    def test_existing_destination(self, vault: Path, kind: str) -> None:
        directory = vault / "campaigns/campaign_1/sessions"
        if kind == "archived":
            directory = directory / "archive"
            directory.mkdir()
        target = directory / ("s-1-001.MD" if kind == "case" else "S-1-001.md")
        if kind in {"file", "case", "archived"}:
            target.write_text("Unchanged")
        elif kind == "directory":
            target.mkdir()
        else:
            target.symlink_to(
                vault
                / ("reference/templates/Session.md" if kind == "symlink" else "missing")
            )
        with pytest.raises((FileExistsError, ValueError)):
            add_session(vault, campaign=1, number=1)
        if kind in {"file", "case", "archived"}:
            assert target.read_text() == "Unchanged"
        elif kind == "directory":
            assert list(target.iterdir()) == []
        else:
            assert target.is_symlink()

    @pytest.mark.parametrize(
        "scenario",
        [
            "missing_template",
            "bad_template",
            "wrong_type",
            "missing_type",
            "no_campaign_directory",
            "symlink_directory",
            "symlink_template",
            "schema",
            "missing_overview",
        ],
    )
    def test_invalid_scaffolding(self, vault: Path, scenario: str) -> None:
        template = vault / "reference/templates/Session.md"
        definition = vault / "reference/types/Session.md"
        if scenario == "missing_template":
            template.unlink()
        elif scenario == "bad_template":
            template.write_text("---\nbad: [\n---\n")
        elif scenario == "wrong_type":
            template.write_text("Missing type")
        elif scenario == "missing_type":
            definition.unlink()
        elif scenario == "no_campaign_directory":
            definition.write_text(
                '---\ntype: "[[Type]]"\ndirectories: {shared: sessions}\n---\n'
            )
        elif scenario == "symlink_directory":
            directory = vault / "campaigns/campaign_1/sessions"
            moved = directory.rename(vault / "other-sessions")
            directory.symlink_to(moved)
        elif scenario == "symlink_template":
            template.unlink()
            template.symlink_to(definition)
        elif scenario == "missing_overview":
            (vault / "campaigns/campaign_1/reference/Campaign.md").unlink()
        else:
            schema = vault / "reference/schemas/session.schema.json"
            data = json.loads(schema.read_text())
            data["properties"]["frontmatter"]["required"].append("custom_required")
            schema.write_text(json.dumps(data))
        with pytest.raises(ValueError):
            add_session(vault, campaign=1)
        assert not list(vault.rglob("S-1-001.md"))

    @pytest.mark.parametrize("error", [OSError("failed"), KeyboardInterrupt()])
    def test_validation_interruption(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, error: BaseException
    ) -> None:
        with monkeypatch.context() as patch:
            patch.setattr("armarium.session.validate", Mock(side_effect=error))
            with pytest.raises(type(error)):
                add_session(vault, campaign=1)
        assert not (vault / "campaigns/campaign_1/sessions/S-1-001.md").exists()
        assert add_session(vault, campaign=1).name == "S-1-001.md"

    def test_write_failure(self, vault: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        destination = vault / "campaigns/campaign_1/sessions/S-1-001.md"
        original_open = Path.open

        def failing_open(path: Path, *args: object, **kwargs: object) -> object:
            if path == destination and args == ("x",):
                original_open(path, "x", encoding="utf-8").close()
                stream = MagicMock()
                stream.write.side_effect = OSError("write failed")
                return stream
            return original_open(path, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(Path, "open", failing_open)
            with pytest.raises(OSError, match="write failed"):
                add_session(vault, campaign=1)
        assert not destination.exists()
        assert add_session(vault, campaign=1) == destination
