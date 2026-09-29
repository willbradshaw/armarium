"""Clue numbering, local templates and creation failure recovery."""

import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest

from armarium.add import add_campaign
from armarium.clue import _clue_number, add_clue
from armarium.parse import Record
from armarium.validate import validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault with spaces"
    shutil.copytree(ROOT / "vaults/starter", root)
    return root


class TestClueNumber:
    @pytest.mark.parametrize(
        ("requested", "expected"), [(None, 13), (1, 1), (9999, 9999)]
    )
    def test_numbering(
        self, tmp_path: Path, requested: int | None, expected: int
    ) -> None:
        (tmp_path / "archive").mkdir()
        for name in (
            "C-1-0003.md",
            "archive/C-1-0012.md",
            "C-2-0900.md",
            "C-1-0050 notes.md",
            "notes.md",
        ):
            (tmp_path / name).write_text("")
        assert _clue_number(tmp_path, 1, requested) == expected

    def test_empty_campaign(self, tmp_path: Path) -> None:
        assert _clue_number(tmp_path, 1, None) == 1

    @pytest.mark.parametrize("number", [0, -1, 10000, 5])
    def test_invalid_number(self, tmp_path: Path, number: int) -> None:
        (tmp_path / "c-1-0005.MD").write_text("")
        with pytest.raises(ValueError):
            _clue_number(tmp_path, 1, number)

    def test_exhausted_numbers(self, tmp_path: Path) -> None:
        (tmp_path / "C-1-9999.md").write_text("")
        with pytest.raises(ValueError, match="1 and 9999"):
            _clue_number(tmp_path, 1, None)


class TestAddClue:
    @pytest.mark.parametrize("name", ["starter", "example"])
    def test_valid_addition(self, tmp_path: Path, name: str) -> None:
        root = tmp_path / "vault with spaces"
        shutil.copytree(ROOT / "vaults" / name, root)
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        destination = add_clue(text="A fact.", vault=root, campaign=1)
        assert destination.parent == root / "campaigns/campaign_1/clues"
        record, _ = Record.parse(destination, root)
        assert record is not None
        assert record.frontmatter["text"] == "A fact."
        assert record.frontmatter["subjects"] == []
        assert record.frontmatter["first_session"] is None
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
        monkeypatch.chdir(vault / "campaigns/campaign_2" / ("clues" if nested else ""))
        destination = add_clue(text="A fact.", vault=vault if explicit_vault else None)
        assert destination.name == "C-2-0001.md"
        assert not validate(destination).failed

    def test_override_and_numbering_gaps(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        add_campaign(vault)
        monkeypatch.chdir(vault / "campaigns/campaign_1")
        assert add_clue(text="A fact.", campaign=2, number=12).name == "C-2-0012.md"
        assert add_clue(text="A fact.", campaign=2).name == "C-2-0013.md"
        assert add_clue(text="A fact.", campaign=2, number=3).name == "C-2-0003.md"
        assert add_clue(text="A fact.").name == "C-1-0001.md"
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
            add_clue(
                text="A fact.",
                vault=selected,
                campaign=0
                if scenario == "zero"
                else 8
                if scenario == "nonexistent"
                else None,
            )
        assert not list(vault.glob("campaigns/*/clues/C-*.md"))

    @pytest.mark.parametrize(
        "kind", ["file", "directory", "symlink", "dangling", "case", "archived"]
    )
    def test_existing_destination(self, vault: Path, kind: str) -> None:
        directory = vault / "campaigns/campaign_1/clues"
        if kind == "archived":
            directory = directory / "archive"
            directory.mkdir()
        target = directory / ("c-1-0001.MD" if kind == "case" else "C-1-0001.md")
        if kind in {"file", "case", "archived"}:
            target.write_text("Unchanged")
        elif kind == "directory":
            target.mkdir()
        else:
            target.symlink_to(
                vault
                / ("reference/templates/Clue.md" if kind == "symlink" else "missing")
            )
        with pytest.raises((FileExistsError, ValueError)):
            add_clue(text="A fact.", vault=vault, campaign=1, number=1)
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
        ],
    )
    def test_invalid_scaffolding(self, vault: Path, scenario: str) -> None:
        template = vault / "reference/templates/Clue.md"
        definition = vault / "reference/types/Clue.md"
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
                '---\ntype: "[[Type]]"\ndirectories: {shared: clues}\n---\n'
            )
        elif scenario == "symlink_directory":
            directory = vault / "campaigns/campaign_1/clues"
            moved = directory.rename(vault / "other-clues")
            directory.symlink_to(moved)
        elif scenario == "symlink_template":
            template.unlink()
            template.symlink_to(definition)
        else:
            schema = vault / "reference/schemas/clue.schema.json"
            data = json.loads(schema.read_text())
            data["properties"]["frontmatter"]["required"].append("custom_required")
            schema.write_text(json.dumps(data))
        with pytest.raises(ValueError):
            add_clue(text="A fact.", vault=vault, campaign=1)
        assert not list(vault.rglob("C-1-0001.md"))

    @pytest.mark.parametrize("error", [OSError("failed"), KeyboardInterrupt()])
    def test_validation_interruption(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, error: BaseException
    ) -> None:
        with monkeypatch.context() as patch:
            patch.setattr("armarium.clue.validate", Mock(side_effect=error))
            with pytest.raises(type(error)):
                add_clue(text="A fact.", vault=vault, campaign=1)
        assert not (vault / "campaigns/campaign_1/clues/C-1-0001.md").exists()
        assert add_clue(text="A fact.", vault=vault, campaign=1).name == "C-1-0001.md"

    def test_write_failure(self, vault: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        destination = vault / "campaigns/campaign_1/clues/C-1-0001.md"
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
                add_clue(text="A fact.", vault=vault, campaign=1)
        assert not destination.exists()
        assert add_clue(text="A fact.", vault=vault, campaign=1) == destination

    @pytest.mark.parametrize("text", [None, "", " \n\t"])
    def test_missing_text(self, vault: Path, text: str | None) -> None:
        with pytest.raises(ValueError, match="nonblank"):
            add_clue(vault, campaign=1, text=text)
        assert not list(vault.rglob("C-1-0001.md"))

    def test_local_customizations(self, vault: Path) -> None:
        from armarium.session import add_session

        session = add_session(vault, campaign=1)
        definition = vault / "reference/types/Clue.md"
        definition.write_text(
            definition.read_text().replace("campaign: clues", "campaign: clues/local")
        )
        (vault / "campaigns/campaign_1/clues/local").mkdir()
        template = vault / "reference/templates/Clue.md"
        template.write_text(
            template.read_text()
            .replace('text: ""', 'text: "Local fact."\ncustom: local')
            .replace("[[Pending]]", "[[Hinted]]")
            .replace("first_session:", f'first_session: "[[{session.stem}]]"')
            .replace("last_session:", f'last_session: "[[{session.stem}]]"')
        )
        original, _ = Record.parse(template, vault)
        created = add_clue(vault, campaign=1)
        record, _ = Record.parse(created, vault)
        assert record is not None and original is not None
        assert created.parent.name == "local"
        assert record.body.text == original.body.text
        for field in ("text", "status", "first_session", "last_session", "custom"):
            assert record.frontmatter[field] == original.frontmatter[field]
        assert not validate(vault).failed

    @pytest.mark.parametrize("change", ["session", "body", "anchor", "placement"])
    def test_context_failure_retry(self, vault: Path, change: str) -> None:
        from armarium.content import add_content

        add_content("Harbour", "Location", vault)
        template = vault / "reference/templates/Clue.md"
        original = template.read_text()
        if change == "placement":
            (vault / "content/Harbour.md").rename(vault / "assets/Harbour.md")
        template.write_text(
            original.replace("first_session:", 'first_session: "[[Pending]]"')
            if change == "session"
            else original + "Extra prose"
            if change == "body"
            else original
        )
        with pytest.raises(ValueError, match="failed validation"):
            add_clue(
                vault,
                campaign=1,
                text="[[Harbour#Missing]]" if change == "anchor" else "[[Harbour]]",
            )
        assert not list(vault.rglob("C-1-0001.md"))
        template.write_text(original)
        assert add_clue(vault, campaign=1, text="A fact.").name == "C-1-0001.md"

    def test_late_collision(self, vault: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        destination = vault / "campaigns/campaign_1/clues/C-1-0001.md"
        original_open = Path.open

        def racing_open(path: Path, *args: Any, **kwargs: Any) -> object:
            if path == destination and args == ("x",):
                with original_open(path, "w") as stream:
                    stream.write("Concurrent record")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(Path, "open", racing_open)
        with pytest.raises(FileExistsError):
            add_clue(vault, campaign=1, text="A fact.")
        assert destination.read_text() == "Concurrent record"


class TestClueSubjects:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("No links", []),
            ("[[Harbour]] and [[content/Harbour|port]]", ["[[content/Harbour]]"]),
            (
                "[[Mira]] knows [[Harbour]]",
                ["[[campaigns/campaign_1/content/Mira]]", "[[content/Harbour]]"],
            ),
        ],
    )
    def test_resolved(self, vault: Path, text: str, expected: list[str]) -> None:
        from armarium.clue import _clue_subjects
        from armarium.content import add_content
        from armarium.index import VaultIndex

        add_content("Harbour", "Location", vault)
        add_content("Mira", "NPC", vault, campaign=1)
        destination = vault / "campaigns/campaign_1/clues/C-1-0001.md"
        assert _clue_subjects(text, destination, VaultIndex(vault)) == expected
        created = add_clue(vault, campaign=1, text=text)
        record, _ = Record.parse(created, vault)
        assert record is not None and record.frontmatter["subjects"] == expected
        assert not validate(vault).failed

    @pytest.mark.parametrize(
        "scenario",
        [
            "missing",
            "ambiguous",
            "wrong_type",
            "other_campaign",
            "malformed",
            "asset",
            "untyped",
        ],
    )
    def test_invalid(self, vault: Path, scenario: str) -> None:
        from armarium.clue import _clue_subjects
        from armarium.content import add_content
        from armarium.index import VaultIndex

        text = "[[Missing]]"
        if scenario == "ambiguous":
            add_content("Mira", "NPC", vault)
            add_content("Mira", "NPC", vault, campaign=1)
            text = "[[Mira]]"
        elif scenario == "wrong_type":
            text = "[[types/Clue]]"
        elif scenario == "other_campaign":
            add_campaign(vault)
            add_content("Mira", "NPC", vault, campaign=2)
            text = "[[Mira]]"
        elif scenario == "malformed":
            text = "[[broken"
        elif scenario in {"asset", "untyped"}:
            name = "asset.png" if scenario == "asset" else "Untyped.md"
            (vault / "assets" / name).write_text("not a record")
            text = f"[[{name}]]"
        destination = vault / "campaigns/campaign_1/clues/C-1-0001.md"
        with pytest.raises(ValueError):
            _clue_subjects(text, destination, VaultIndex(vault))
        with pytest.raises(ValueError):
            add_clue(vault, campaign=1, text=text)
        assert not destination.exists()
