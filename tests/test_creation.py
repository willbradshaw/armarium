"""Shared creation contracts: scope, local conventions and failure recovery."""

import shutil
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from armarium.creation import (
    check_destination,
    check_name,
    infer_campaign,
    read_template,
    record_directory,
    record_number,
    record_text,
    require_campaign,
    select_vault,
    write_record,
)


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    shutil.copytree(Path(__file__).resolve().parents[1] / "vaults/starter", root)
    return root


class TestSelectVault:
    @pytest.mark.parametrize("explicit", [False, True])
    def test_selection(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, explicit: bool
    ) -> None:
        monkeypatch.chdir(vault / "content")
        assert select_vault(vault if explicit else None) == vault

    def test_explicit_subdirectory(self, vault: Path) -> None:
        with pytest.raises(ValueError, match="must name the vault root"):
            select_vault(vault / "content")


class TestInferCampaign:
    @pytest.mark.parametrize(
        ("relative", "explicit", "expected"),
        [
            ("", None, None),
            ("content", None, None),
            ("campaigns/campaign_1", None, 1),
            ("campaigns/campaign_1/content", None, 1),
            ("campaigns/campaign_1", 2, 2),
        ],
    )
    def test_scope(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        relative: str,
        explicit: int | None,
        expected: int | None,
    ) -> None:
        monkeypatch.chdir(vault / relative)
        assert infer_campaign(vault, explicit) == expected

    def test_other_vault(
        self, vault: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        other = tmp_path / "other"
        shutil.copytree(vault, other)
        monkeypatch.chdir(other / "campaigns/campaign_1")
        assert infer_campaign(vault, None) is None


class TestRequireCampaign:
    @pytest.mark.parametrize("number", [None, 0, -1])
    def test_missing_or_invalid(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, number: int | None
    ) -> None:
        monkeypatch.chdir(vault)
        with pytest.raises(ValueError):
            require_campaign(vault, number)

    def test_inferred(self, vault: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(vault / "campaigns/campaign_1")
        assert require_campaign(vault, None) == 1
        assert require_campaign(vault, 2) == 2


class TestCheckName:
    @pytest.mark.parametrize(
        "name",
        [
            "",
            " spaced",
            "two  spaces",
            ".hidden",
            "end.",
            "entry.MD",
            "a/b",
            "a\\b",
            "a#b",
            "a\x00b",
            "a\nb",
        ],
    )
    def test_invalid(self, name: str) -> None:
        with pytest.raises(ValueError, match="plain record name"):
            check_name(name)

    @pytest.mark.parametrize("name", ["Alex", "Port Briselle", "Café"])
    def test_valid(self, name: str) -> None:
        check_name(name)


class TestRecordDirectory:
    @pytest.mark.parametrize(
        ("campaign", "relative"),
        [
            (None, "notes"),
            (1, "campaigns/campaign_1/notes"),
            ("campaign_1", "campaigns/campaign_1/notes"),
        ],
    )
    def test_scope(
        self, vault: Path, campaign: int | str | None, relative: str
    ) -> None:
        assert record_directory(vault, "Note", campaign) == vault / relative

    def test_local_declaration(self, vault: Path) -> None:
        definition = vault / "reference/types/Note.md"
        definition.write_text(
            definition.read_text().replace("shared: notes", "shared: custom")
        )
        (vault / "custom").mkdir()
        assert record_directory(vault, "Note", None) == vault / "custom"

    @pytest.mark.parametrize(
        "scenario", ["missing_type", "missing_scope", "missing_directory", "symlink"]
    )
    def test_invalid(self, vault: Path, scenario: str) -> None:
        if scenario == "missing_type":
            (vault / "reference/types/Note.md").unlink()
        elif scenario == "missing_scope":
            with pytest.raises(ValueError, match="no shared directory"):
                record_directory(vault, "Player", None)
            return
        else:
            directory = vault / "notes"
            directory.rename(vault / "old-notes")
            if scenario == "symlink":
                directory.symlink_to(vault / "old-notes")
        with pytest.raises(ValueError):
            record_directory(vault, "Note", None)


class TestCheckDestination:
    @pytest.mark.parametrize("kind", ["file", "directory", "dangling"])
    def test_collision(self, tmp_path: Path, kind: str) -> None:
        existing = tmp_path / "ENTRY.md"
        if kind == "file":
            existing.touch()
        elif kind == "directory":
            existing.mkdir()
        else:
            existing.symlink_to(tmp_path / "missing")
        with pytest.raises(FileExistsError):
            check_destination(tmp_path / "entry.md")

    def test_unicode(self, tmp_path: Path) -> None:
        (tmp_path / "Café.md").touch()
        with pytest.raises(FileExistsError):
            check_destination(tmp_path / "Cafe\u0301.md", normalize=True)

    def test_available(self, tmp_path: Path) -> None:
        check_destination(tmp_path / "new.md")


class TestReadTemplate:
    def test_valid(self, vault: Path) -> None:
        template = read_template(vault, "Note")
        assert template.frontmatter.type == "Note"
        assert template.path == vault / "reference/templates/Note.md"

    @pytest.mark.parametrize(
        "scenario",
        ["missing", "wrong_type", "symlink", "parent_symlink", "reference_symlink"],
    )
    def test_invalid(self, vault: Path, scenario: str) -> None:
        path = vault / "reference/templates/Note.md"
        if scenario == "missing":
            path.unlink()
        elif scenario == "wrong_type":
            path.write_text(path.read_text().replace("types/Note", "types/Player"))
        else:
            path = (
                path
                if scenario == "symlink"
                else path.parent
                if scenario == "parent_symlink"
                else path.parent.parent
            )
            moved = vault / "moved"
            path.rename(moved)
            path.symlink_to(moved)
        with pytest.raises(ValueError):
            read_template(vault, "Note", check_reference=True)


class TestRecordText:
    def test_round_trip(self) -> None:
        metadata = {"type": "[[types/Note]]", "custom": "Café", "empty": None}
        body = "\n## Notes\n\nUnchanged body.\n"
        text = record_text(metadata, body)
        assert text.endswith(body)
        assert yaml.safe_load(text.split("---\n")[1]) == metadata
        assert text.index("type:") < text.index("custom:") < text.index("empty:")
        assert "Café" in text


class TestWriteRecord:
    def test_valid(self, vault: Path) -> None:
        destination = vault / "notes/New.md"
        text = (vault / "reference/templates/Note.md").read_text()
        assert write_record(destination, text, vault, "Note") == destination
        assert destination.read_text() == text

    def test_invalid_cleanup(self, vault: Path) -> None:
        destination = vault / "notes/New.md"
        with pytest.raises(ValueError, match="generated Note record failed validation"):
            write_record(destination, "Invalid", vault, "Note")
        assert not destination.exists()

    @pytest.mark.parametrize("error", [OSError("failed"), KeyboardInterrupt()])
    def test_interruption(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, error: BaseException
    ) -> None:
        destination = vault / "notes/New.md"
        monkeypatch.setattr("armarium.creation.validate", Mock(side_effect=error))
        with pytest.raises(type(error)):
            write_record(destination, "text", vault, "Note")
        assert not destination.exists()

    def test_exclusive_open(self, vault: Path) -> None:
        destination = vault / "notes/New.md"
        destination.write_text("Existing")
        with pytest.raises(FileExistsError):
            write_record(destination, "Replacement", vault, "Note")
        assert destination.read_text() == "Existing"


@pytest.mark.parametrize(
    ("kind", "prefix", "digits"), [("session", "S", 3), ("clue", "C", 4)]
)
class TestRecordNumber:
    @pytest.mark.parametrize("requested", [None, 1, "maximum"])
    def test_numbering(
        self,
        tmp_path: Path,
        kind: str,
        prefix: str,
        digits: int,
        requested: int | str | None,
    ) -> None:
        (tmp_path / "archive").mkdir()
        for name in (
            f"{prefix}-1-{3:0{digits}}.md",
            f"archive/{prefix}-1-{12:0{digits}}.md",
            f"{prefix}-2-{900:0{digits}}.md",
            f"{prefix}-1-{50:0{digits}} Transcript.md",
            "notes.md",
        ):
            (tmp_path / name).touch()
        number = 10**digits - 1 if isinstance(requested, str) else requested
        assert record_number(
            tmp_path, 1, number, kind=kind, prefix=prefix, digits=digits
        ) == (13 if number is None else number)

    def test_empty(self, tmp_path: Path, kind: str, prefix: str, digits: int) -> None:
        assert (
            record_number(tmp_path, 1, None, kind=kind, prefix=prefix, digits=digits)
            == 1
        )

    @pytest.mark.parametrize("requested", [0, -1, "overflow", 5])
    def test_invalid(
        self, tmp_path: Path, kind: str, prefix: str, digits: int, requested: int | str
    ) -> None:
        (tmp_path / f"{prefix.lower()}-1-{5:0{digits}}.MD").touch()
        number = 10**digits if isinstance(requested, str) else requested
        with pytest.raises(ValueError):
            record_number(tmp_path, 1, number, kind=kind, prefix=prefix, digits=digits)

    def test_exhausted(
        self, tmp_path: Path, kind: str, prefix: str, digits: int
    ) -> None:
        maximum = 10**digits - 1
        (tmp_path / f"{prefix}-1-{maximum}.md").touch()
        with pytest.raises(ValueError, match=f"1 and {maximum}"):
            record_number(tmp_path, 1, None, kind=kind, prefix=prefix, digits=digits)
