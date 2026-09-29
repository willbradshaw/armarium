"""Player names, local templates and creation failure recovery."""

import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest

from armarium.add import add_campaign
from armarium.content import add_content
from armarium.parse import Record
from armarium.player import add_player
from armarium.validate import validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "my-vault"
    shutil.copytree(ROOT / "vaults/starter", root)
    return root


class TestAddPlayer:
    @pytest.mark.parametrize("name", ["starter", "example"])
    def test_valid_addition(self, tmp_path: Path, name: str) -> None:
        root = tmp_path / "vault with spaces"
        shutil.copytree(ROOT / "vaults" / name, root)
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        destination = add_player("New Player", root, campaign=1)
        assert destination.parent == root / "campaigns/campaign_1/reference/players"
        record, _ = Record.parse(destination, root)
        assert record is not None
        assert record.frontmatter["plays"] == []
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
        destination = add_player("New Player", vault if explicit_vault else None)
        assert destination.parent == vault / "campaigns/campaign_2/reference/players"
        assert not validate(destination).failed

    def test_explicit_override(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        add_campaign(vault)
        monkeypatch.chdir(vault / "campaigns/campaign_1")
        assert add_player("New Player", campaign=2).parent == (
            vault / "campaigns/campaign_2/reference/players"
        )

    def test_local_customizations(self, vault: Path) -> None:
        definition = vault / "reference/types/Player.md"
        definition.write_text(
            definition.read_text().replace(
                "campaign: reference/players", "campaign: reference/people"
            )
        )
        (vault / "campaigns/campaign_1/reference/people").mkdir()
        template = vault / "reference/templates/Player.md"
        template.write_text(
            template.read_text().replace("plays: []", "plays: []\ncustom: Local value")
            + "\n## Notes\nLocal guidance.\n"
        )
        destination = add_player("New Player", vault, campaign=1)
        record, _ = Record.parse(destination, vault)
        original, _ = Record.parse(template, vault)
        assert record is not None and original is not None
        assert destination.parent.name == "people"
        assert record.frontmatter["custom"] == "Local value"
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
            add_player(
                "New Player",
                selected,
                campaign=0
                if scenario == "zero"
                else 8
                if scenario == "nonexistent"
                else None,
            )
        assert not list(vault.rglob("New Player.md"))

    @pytest.mark.parametrize(
        "kind", ["file", "directory", "symlink", "dangling", "case"]
    )
    def test_existing_destination(self, vault: Path, kind: str) -> None:
        directory = vault / "campaigns/campaign_1/reference/players"
        target = directory / ("new player.MD" if kind == "case" else "New Player.md")
        if kind in {"file", "case"}:
            target.write_text("Unchanged")
        elif kind == "directory":
            target.mkdir()
        else:
            target.symlink_to(
                vault
                / ("reference/templates/Player.md" if kind == "symlink" else "missing")
            )
        with pytest.raises((FileExistsError, ValueError)):
            add_player("New Player", vault, campaign=1)
        if kind in {"file", "case"}:
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
            "symlink_parent",
            "traversal_directory",
            "symlink_template",
            "schema",
        ],
    )
    def test_invalid_scaffolding(self, vault: Path, scenario: str) -> None:
        template = vault / "reference/templates/Player.md"
        definition = vault / "reference/types/Player.md"
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
                '---\ntype: "[[Type]]"\ndirectories: {shared: reference/players}\n---\n'
            )
        elif scenario == "traversal_directory":
            definition.write_text(
                definition.read_text().replace(
                    "campaign: reference/players", "campaign: ../escape"
                )
            )
        elif scenario in {"symlink_directory", "symlink_parent"}:
            directory = vault / "campaigns/campaign_1/reference/players"
            if scenario == "symlink_parent":
                directory = directory.parent
            moved = directory.rename(vault / "other-players")
            directory.symlink_to(moved)
        elif scenario == "symlink_template":
            template.unlink()
            template.symlink_to(definition)
        else:
            schema = vault / "reference/schemas/player.schema.json"
            data = json.loads(schema.read_text())
            data["properties"]["frontmatter"]["required"].append("custom_required")
            schema.write_text(json.dumps(data))
        with pytest.raises(ValueError):
            add_player("New Player", vault, campaign=1)
        assert not list(vault.rglob("New Player.md"))

    @pytest.mark.parametrize("error", [OSError("failed"), KeyboardInterrupt()])
    def test_validation_interruption(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, error: BaseException
    ) -> None:
        with monkeypatch.context() as patch:
            patch.setattr("armarium.add.validate", Mock(side_effect=error))
            with pytest.raises(type(error)):
                add_player("New Player", vault, campaign=1)
        assert not (
            vault / "campaigns/campaign_1/reference/players/New Player.md"
        ).exists()
        assert add_player("New Player", vault, campaign=1).name == "New Player.md"

    def test_write_failure(self, vault: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        destination = vault / "campaigns/campaign_1/reference/players/New Player.md"
        original_open = Path.open

        def failing_open(path: Path, *args: Any, **kwargs: Any) -> object:
            if path == destination and args == ("x",):
                original_open(path, "x", encoding="utf-8").close()
                stream = MagicMock()
                stream.write.side_effect = OSError("write failed")
                return stream
            return original_open(path, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(Path, "open", failing_open)
            with pytest.raises(OSError, match="write failed"):
                add_player("New Player", vault, campaign=1)
        assert not destination.exists()
        assert add_player("New Player", vault, campaign=1) == destination

    @pytest.mark.parametrize(
        "name",
        [
            "",
            " ",
            "../escape",
            "name.md",
            ".hidden",
            "a/b",
            "a\\b",
            "a|b",
            "a:b",
            "a?",
            " trailing",
            "two  spaces",
            "end.",
            "line\nbreak",
        ],
    )
    def test_invalid_name(self, vault: Path, name: str) -> None:
        with pytest.raises(ValueError, match="plain record name"):
            add_player(name, vault, campaign=1)

    @pytest.mark.parametrize(
        "plays",
        [
            "null",
            "PC",
            "[42]",
            '["[[Missing]]"]',
            '["[[types/Player]]"]',
            '["[[Not a PC]]"]',
            '["[[Other PC]]"]',
            '["[[Duplicate]]"]',
        ],
    )
    def test_invalid_plays(self, vault: Path, plays: str) -> None:
        add_player("Existing", vault, campaign=1)
        add_content("Not a PC", "NPC", vault, campaign=1)
        add_campaign(vault)
        add_player("Other", vault, campaign=2)
        add_content("Other PC", "PC", vault, campaign=2, player="Other")
        for campaign, player in [(1, "Existing"), (2, "Other")]:
            add_content("Duplicate", "PC", vault, campaign=campaign, player=player)
        template = vault / "reference/templates/Player.md"
        original = template.read_text()
        template.write_text(original.replace("plays: []", f"plays: {plays}"))
        before = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
        with pytest.raises(ValueError, match="failed validation"):
            add_player("New Player", vault, campaign=1)
        assert not (
            vault / "campaigns/campaign_1/reference/players/New Player.md"
        ).exists()
        assert all(p.read_bytes() == data for p, data in before.items())
        template.write_text(original)
        assert add_player("New Player", vault, campaign=1).exists()

    @pytest.mark.parametrize("shared", [False, True])
    def test_pc_interoperability(self, vault: Path, shared: bool) -> None:
        player = add_player("New Player", vault, campaign=1)
        before = player.read_bytes()
        pc = add_content(
            "New PC", "PC", vault, campaign=None if shared else 1, player="New Player"
        )
        assert player.read_bytes() == before
        template = vault / "reference/templates/Player.md"
        template.write_text(
            template.read_text().replace("plays: []", 'plays: ["[[New PC]]"]')
        )
        before_pc = pc.read_bytes()
        second = add_player("Second Player", vault, campaign=1)
        record, _ = Record.parse(second, vault)
        assert record is not None and record.frontmatter["plays"] == ["[[New PC]]"]
        assert pc.read_bytes() == before_pc
        assert player.read_bytes() == before
        assert not validate(vault).failed

    def test_late_collision(self, vault: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        destination = vault / "campaigns/campaign_1/reference/players/New Player.md"
        original_open = Path.open

        def racing_open(path: Path, *args: Any, **kwargs: Any) -> object:
            if path == destination and args == ("x",):
                with original_open(path, "w") as stream:
                    stream.write("Concurrent record")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(Path, "open", racing_open)
        with pytest.raises(FileExistsError):
            add_player("New Player", vault, campaign=1)
        assert destination.read_text() == "Concurrent record"
