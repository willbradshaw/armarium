"""Parity between the shipped starter and example vaults outside their content."""

from pathlib import Path

VAULTS = Path(__file__).resolve().parents[1] / "vaults"
STARTER = VAULTS / "starter"
EXAMPLE = VAULTS / "example"
CONTENT_DIRECTORIES = frozenset({"content", "campaigns", "assets"})


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
        for name in ("content", "campaigns", "assets", "reference"):
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
        assert not extra, f"missing from starter: {extra[0]}"

    def test_same_bytes(self) -> None:
        starter = shared_files(STARTER)
        example = shared_files(EXAMPLE)
        for relative in sorted(starter.keys() & example.keys()):
            assert starter[relative].read_bytes() == example[relative].read_bytes(), (
                f"differs: {relative}"
            )
