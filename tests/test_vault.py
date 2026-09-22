"""Infrastructure applies only to root scans and keeps empty starters valid."""

import shutil
from pathlib import Path

import pytest

from armarium.discovery import find_vault
from armarium.infrastructure import shipped_vaults
from armarium.validation import validate


@pytest.mark.parametrize("name", ["starter", "example"])
def test_shipped_and_fresh_copies(name: str, tmp_path: Path) -> None:
    source = Path("vaults") / name
    before = {
        p.relative_to(source): p.read_bytes() for p in source.rglob("*") if p.is_file()
    }
    assert not validate(source).failed
    copy = tmp_path / f"{name} with spaces"
    shutil.copytree(source, copy)
    assert not validate(copy).failed
    assert before == {
        p.relative_to(copy): p.read_bytes() for p in copy.rglob("*") if p.is_file()
    }


def test_structure_multiple_campaigns_and_extra_folders(vault: Path) -> None:
    shutil.copytree(vault / "campaigns/campaign_1", vault / "campaigns/campaign_123")
    for number in (1, 123):
        index = vault / f"campaigns/campaign_{number}/reference/indexes/Clues.md"
        index.write_text(
            index.read_text().replace(
                "[[Campaign]]", f"[[campaign_{number}/reference/Campaign]]"
            )
        )
    (vault / "extra").mkdir()
    assert not validate(vault).failed
    shutil.rmtree(vault / "campaigns/campaign_123/sessions")
    result = validate(vault)
    assert any(
        d.rule == "vault.required" and "campaign_123/sessions" in d.path
        for d in result.diagnostics
    )
    assert not validate(vault / "content").failed


def test_missing_invalid_infrastructure(vault: Path) -> None:
    (vault / "reference/types/Content.md").unlink()
    (vault / "reference/schemas/broken.json").write_text('{"type": 12}')
    rules = {d.rule for d in validate(vault).diagnostics}
    assert {"vault.required", "schema.invalid"} <= rules


def test_discovery_does_not_use_repository_git(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    with pytest.raises(ValueError, match="cannot infer"):
        find_vault(tmp_path)
    shutil.copytree("vaults/starter", tmp_path / "vaults/a")
    shutil.copytree("vaults/starter", tmp_path / "vaults/b")
    assert len(shipped_vaults(tmp_path)) == 2
    assert find_vault(tmp_path / "vaults/a/content") == tmp_path / "vaults/a"
