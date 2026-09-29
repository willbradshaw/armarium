"""Campaign scaffolding, local customizations and failure recovery."""

import shutil
from pathlib import Path

import pytest

from armarium.add import _campaign_directories, _render_campaign, add_campaign
from armarium.validate import CAMPAIGN_DIRECTORIES, validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "my-vault"
    shutil.copytree(ROOT / "vaults/starter", root)
    return root


class TestCampaignDirectories:
    def test_local_declarations(self, vault: Path) -> None:
        note = vault / "reference/types/Note.md"
        note.write_text(
            note.read_text().replace("campaign: notes", "campaign: notes/local")
        )
        assert _campaign_directories(vault) == {
            *CAMPAIGN_DIRECTORIES,
            "reference",
            "notes/local",
        }

    @pytest.mark.parametrize(
        "text",
        [
            "---\nbad: [\n---\n",
            '---\ntype: "[[Type]]"\ndirectories: {campaign: ../outside}\n---\n',
        ],
    )
    def test_invalid_type(self, vault: Path, text: str) -> None:
        (vault / "reference/types/Note.md").write_text(text)
        with pytest.raises(ValueError):
            _campaign_directories(vault)


class TestRenderCampaign:
    @pytest.mark.parametrize("number", [1, 2, 12])
    def test_tokens(self, number: int) -> None:
        text = "[[campaign_1/reference/Campaign|Overview]] campaign_10 campaign_2 C-1-XXXX C-1-0042 C-10-0001 C-1-other"
        assert _render_campaign(text, number) == (
            f"[[campaign_{number}/reference/Campaign|Overview]] campaign_10 campaign_2 "
            f"C-{number}-XXXX C-{number}-0042 C-10-0001 C-1-other"
        )


class TestAddCampaign:
    @pytest.mark.parametrize(("name", "number"), [("starter", 2), ("example", 3)])
    def test_valid_addition(self, tmp_path: Path, name: str, number: int) -> None:
        root = tmp_path / "vault with spaces"
        shutil.copytree(ROOT / "vaults" / name, root)
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        destination = add_campaign(root)
        assert destination == root / "campaigns" / f"campaign_{number}"
        assert sorted(
            p.relative_to(destination).as_posix() for p in destination.rglob("*.md")
        ) == ["reference/Campaign.md", "reference/indexes/Clues.md"]
        clue_index = (destination / "reference/indexes/Clues.md").read_text()
        assert f"[[campaign_{number}/reference/Campaign]]" in clue_index
        assert f"C-{number}-XXXX" in clue_index
        assert all(
            any(path.iterdir()) for path in destination.rglob("*") if path.is_dir()
        )
        result = validate(root)
        assert not result.failed, result.diagnostics
        assert all(p.read_bytes() == contents for p, contents in before.items())

    def test_numbering_and_discovery(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(vault / "campaigns/campaign_1/content")
        assert add_campaign(number=10).name == "campaign_10"
        assert add_campaign().name == "campaign_11"
        assert add_campaign(number=4).name == "campaign_4"
        assert not validate(vault).failed

    def test_no_existing_campaigns(self, vault: Path) -> None:
        shutil.rmtree(vault / "campaigns/campaign_1")
        assert add_campaign(vault).name == "campaign_1"
        assert not validate(vault).failed

    def test_customized_scaffolding(self, vault: Path) -> None:
        template = vault / "reference/templates/Campaign.md"
        template.write_text(
            '---\ntype: "[[Reference]]"\ncustom: true\n---\nLocal guidance.\n'
        )
        note = vault / "reference/types/Note.md"
        note.write_text(
            note.read_text().replace("campaign: notes", "campaign: notes/local")
        )
        (vault / "campaigns/campaign_1/notes/local").mkdir()
        destination = add_campaign(vault)
        assert (destination / "notes/local").is_dir()
        assert (
            destination / "reference/Campaign.md"
        ).read_bytes() == template.read_bytes()
        assert not validate(vault).failed

    @pytest.mark.parametrize("number", [0, -1, 1])
    def test_invalid_or_used_number(self, vault: Path, number: int) -> None:
        with pytest.raises(ValueError):
            add_campaign(vault, number=number)
        assert [p.name for p in (vault / "campaigns").iterdir()] == ["campaign_1"]

    @pytest.mark.parametrize(
        "kind", ["file", "directory", "symlink", "dangling", "leading_zero"]
    )
    def test_existing_destination(self, vault: Path, kind: str) -> None:
        target = (
            vault
            / "campaigns"
            / ("campaign_02" if kind == "leading_zero" else "campaign_2")
        )
        if kind == "file":
            target.write_text("Keep me")
        elif kind in {"directory", "leading_zero"}:
            target.mkdir()
        else:
            target.symlink_to(vault / ("content" if kind == "symlink" else "missing"))
        with pytest.raises((ValueError, FileExistsError)):
            add_campaign(vault, number=2)
        if kind == "file":
            assert target.read_text() == "Keep me"
        elif kind in {"directory", "leading_zero"}:
            assert list(target.iterdir()) == []
        else:
            assert target.is_symlink()

    @pytest.mark.parametrize("kind", ["missing", "symlink"])
    def test_unavailable_template(self, vault: Path, kind: str) -> None:
        template = vault / "reference/templates/Campaign.md"
        template.unlink()
        if kind == "symlink":
            template.symlink_to(vault / "campaigns/campaign_1/reference/Campaign.md")
        with pytest.raises((OSError, ValueError)):
            add_campaign(vault)
        assert not (vault / "campaigns/campaign_2").exists()

    @pytest.mark.parametrize("error", [OSError("write failed"), KeyboardInterrupt()])
    def test_write_failure(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch, error: BaseException
    ) -> None:
        write_text = Path.write_text

        def fail_write(path: Path, text: str, **kwargs: object) -> int:
            raise error

        monkeypatch.setattr(Path, "write_text", fail_write)
        with pytest.raises(type(error)):
            add_campaign(vault)
        assert not (vault / "campaigns/campaign_2").exists()
        monkeypatch.setattr(Path, "write_text", write_text)
        assert add_campaign(vault).name == "campaign_2"

    @pytest.mark.parametrize("nested", [False, True])
    def test_invalid_vault(self, vault: Path, tmp_path: Path, nested: bool) -> None:
        with pytest.raises(ValueError):
            add_campaign(vault / "content" if nested else tmp_path)

    def test_symlinked_infrastructure(self, vault: Path) -> None:
        templates = vault / "reference/templates"
        moved = templates.rename(vault / "templates-backup")
        templates.symlink_to(moved)
        with pytest.raises(ValueError, match="real directory"):
            add_campaign(vault)
        assert not (vault / "campaigns/campaign_2").exists()
