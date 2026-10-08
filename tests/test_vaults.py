"""Parity between the shipped starter and example vaults, and their agent files."""

import json
from pathlib import Path

import pytest

from armarium.parse import Frontmatter
from armarium.validate import validate

VAULTS = Path(__file__).resolve().parents[1] / "vaults"
STARTER = VAULTS / "starter"
EXAMPLE = VAULTS / "example"
CONTENT_DIRECTORIES = frozenset({"content", "notes", "campaigns", "assets"})
AGENT_SKILLS = sorted(
    path.parent.name for path in (STARTER / ".agents/skills").glob("*/SKILL.md")
)


def skill_metadata(path: Path) -> tuple[dict[str, object], str]:
    """Read a SKILL.md file's frontmatter and the text after it."""
    text = path.read_text(encoding="utf-8")
    frontmatter, length = Frontmatter.parse(text)
    return dict(frontmatter), "".join(text.splitlines(keepends=True)[length:])


def shared_files(vault: Path) -> dict[Path, Path]:
    """Map each non-content file's vault-relative path to its absolute path."""
    files: dict[Path, Path] = {}
    for path in sorted(vault.rglob("*")):
        relative = path.relative_to(vault)
        if path.is_dir() or relative.parts[0] in CONTENT_DIRECTORIES:
            continue
        files[relative] = path
    return files


class TestSharedFiles:
    def test_excludes_content_directories(self, tmp_path: Path) -> None:
        for name in ("content", "notes", "campaigns", "assets", "reference"):
            (tmp_path / name / "sub").mkdir(parents=True)
            (tmp_path / name / "sub" / "a.md").write_text("a")
        (tmp_path / ".gitignore").write_text("x")
        assert shared_files(tmp_path) == {
            Path(".gitignore"): tmp_path / ".gitignore",
            Path("reference/sub/a.md"): tmp_path / "reference/sub/a.md",
        }

    def test_keeps_hidden_directories(self, tmp_path: Path) -> None:
        (tmp_path / ".obsidian").mkdir()
        (tmp_path / ".obsidian" / "app.json").write_text("{}")
        assert shared_files(tmp_path) == {
            Path(".obsidian/app.json"): tmp_path / ".obsidian/app.json"
        }


class TestVaultParity:
    def test_same_paths(self) -> None:
        starter = shared_files(STARTER).keys()
        example = shared_files(EXAMPLE).keys()
        missing = sorted(starter - example)
        extra = sorted(example - starter)
        assert not missing, f"missing from example: {missing[0]}"
        declarations = json.loads((EXAMPLE / "reference/extensions.json").read_text())
        extension_files = {
            Path("reference/extensions")
            / name
            / path.relative_to(VAULTS.parent / "extensions" / name)
            for name in declarations
            for path in (VAULTS.parent / "extensions" / name).rglob("*")
            if path.is_file()
        }
        assert set(extra) == extension_files | {Path("reference/extensions.json")}

    def test_same_bytes(self) -> None:
        starter = shared_files(STARTER)
        example = shared_files(EXAMPLE)
        for relative in sorted(starter.keys() & example.keys()):
            assert starter[relative].read_bytes() == example[relative].read_bytes(), (
                f"differs: {relative}"
            )


class TestSkillMetadata:
    def test_reads_frontmatter_and_body(self, tmp_path: Path) -> None:
        path = tmp_path / "SKILL.md"
        path.write_text("---\nname: demo\ndescription: Does it.\n---\n\nSteps.\n")
        assert skill_metadata(path) == (
            {"name": "demo", "description": "Does it."},
            "\nSteps.\n",
        )


class TestAgentFiles:
    def test_ships_skills(self) -> None:
        assert AGENT_SKILLS

    @pytest.mark.parametrize("skill", AGENT_SKILLS)
    def test_skill_is_named_and_described(self, skill: str) -> None:
        metadata, body = skill_metadata(STARTER / f".agents/skills/{skill}/SKILL.md")
        assert metadata["name"] == skill
        description = metadata["description"]
        assert isinstance(description, str) and 0 < len(description) <= 1024
        assert body.strip()

    @pytest.mark.parametrize("skill", AGENT_SKILLS)
    def test_stub_matches_its_skill(self, skill: str) -> None:
        metadata, _ = skill_metadata(STARTER / f".agents/skills/{skill}/SKILL.md")
        stub, body = skill_metadata(STARTER / f".claude/skills/{skill}/SKILL.md")
        assert stub == metadata
        assert f"`.agents/skills/{skill}/SKILL.md`" in body

    def test_every_stub_has_a_skill(self) -> None:
        stubs = sorted(p.name for p in (STARTER / ".claude/skills").iterdir())
        assert stubs == AGENT_SKILLS

    def test_agents_file_points_to_the_vault_guide(self) -> None:
        text = (STARTER / "AGENTS.md").read_text(encoding="utf-8")
        assert "(docs/armarium.md)" in text
        assert (STARTER / "docs/armarium.md").is_file()

    @pytest.mark.parametrize("vault", [STARTER, EXAMPLE], ids=["starter", "example"])
    def test_vault_with_agent_files_validates(self, vault: Path) -> None:
        assert not validate(vault).failed
