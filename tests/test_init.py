"""Starter lookup, exclusive creation and rollback of a failed initialization."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from armarium.init import _starter, init_vault
from armarium.validate import validate

STARTER = Path(__file__).resolve().parents[1] / "vaults/starter"


class TestStarter:
    @pytest.mark.parametrize("packaged", [False, True])
    def test_resource_precedence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, packaged: bool
    ) -> None:
        package = tmp_path / "package"
        checkout = tmp_path / "checkout"
        source = checkout / "vaults/starter"
        source.mkdir(parents=True)
        if packaged:
            (package / "starter").mkdir(parents=True)
        monkeypatch.setattr("armarium.init.files", Mock(return_value=package))
        monkeypatch.setattr(
            "armarium.init.__file__", str(checkout / "src/armarium/init.py")
        )
        assert _starter() == (package / "starter" if packaged else source)

    def test_missing_resources(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("armarium.init.files", Mock(return_value=tmp_path))
        monkeypatch.setattr(
            "armarium.init.__file__", str(tmp_path / "src/armarium/init.py")
        )
        with pytest.raises(FileNotFoundError, match="reinstall Armarium"):
            _starter()


class TestInitVault:
    @pytest.mark.parametrize("existing", [False, True])
    def test_force_replaces_directory(self, tmp_path: Path, existing: bool) -> None:
        target = tmp_path / "my-vault"
        if existing:
            target.mkdir()
            (target / "obsolete.md").write_text("Old content")
        assert init_vault(target, force=True) == target
        assert not (target / "obsolete.md").exists()
        assert not validate(target).failed
        assert list(tmp_path.iterdir()) == [target]

    @pytest.mark.parametrize("kind", ["file", "symlink", "dangling"])
    def test_force_refuses_non_directories(self, tmp_path: Path, kind: str) -> None:
        target = tmp_path / "target"
        other = tmp_path / "other"
        other.mkdir()
        if kind == "file":
            target.write_text("Unchanged")
        else:
            target.symlink_to(other if kind == "symlink" else tmp_path / "missing")
        with pytest.raises(FileExistsError):
            init_vault(target, force=True)
        if kind == "file":
            assert target.read_text() == "Unchanged"
        else:
            assert target.is_symlink()
        assert list(other.iterdir()) == []

    @pytest.mark.parametrize("stage", ["copy", "rename"])
    @pytest.mark.parametrize("error", [OSError("failed"), KeyboardInterrupt()])
    def test_force_failure_preserves_original(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        stage: str,
        error: BaseException,
    ) -> None:
        target = tmp_path / "my-vault"
        target.mkdir()
        (target / "keep.md").write_text("Unchanged")
        rename = Path.rename

        def fail_install(path: Path, destination: Path) -> Path:
            if path.name == "replacement":
                raise error
            return rename(path, destination)

        if stage == "copy":
            monkeypatch.setattr(
                "armarium.init.shutil.copytree", Mock(side_effect=error)
            )
        else:
            monkeypatch.setattr(Path, "rename", fail_install)
        with pytest.raises(type(error)):
            init_vault(target, force=True)
        assert (target / "keep.md").read_text() == "Unchanged"
        assert list(tmp_path.iterdir()) == [target]

    @pytest.mark.parametrize("relative", [False, True])
    def test_creates_independent_valid_copy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: bool
    ) -> None:
        monkeypatch.chdir(tmp_path)
        target = Path("A new setting") if relative else tmp_path / "A new setting"
        expected = {
            p.relative_to(STARTER): p.read_bytes()
            for p in STARTER.rglob("*")
            if p.is_file()
        }
        created = init_vault(target)
        assert created == tmp_path / "A new setting"
        assert {
            p.relative_to(created): p.read_bytes()
            for p in created.rglob("*")
            if p.is_file()
        } == expected
        assert not validate(created).failed
        (created / "reference/types/Content.md").write_text("Customized")
        assert (STARTER / "reference/types/Content.md").read_bytes() == expected[
            Path("reference/types/Content.md")
        ]

    @pytest.mark.parametrize(
        "kind", ["directory", "populated", "file", "symlink", "dangling"]
    )
    def test_refuses_existing_destinations(self, tmp_path: Path, kind: str) -> None:
        target = tmp_path / "existing"
        other = tmp_path / "other"
        other.mkdir()
        (other / "keep.md").write_text("Unchanged")
        if kind in {"directory", "populated"}:
            target.mkdir()
            if kind == "populated":
                (target / "keep.md").write_text("Unchanged")
        elif kind == "file":
            target.write_text("Unchanged")
        else:
            target.symlink_to(
                other if kind == "symlink" else tmp_path / "missing",
                target_is_directory=True,
            )
        with pytest.raises(FileExistsError):
            init_vault(target)
        assert (other / "keep.md").read_text() == "Unchanged"
        if kind in {"directory", "populated"}:
            assert sorted(p.name for p in target.iterdir()) == (
                ["keep.md"] if kind == "populated" else []
            )
        if kind == "file":
            assert target.read_text() == "Unchanged"
        if kind in {"symlink", "dangling"}:
            assert target.is_symlink()

    def test_missing_parent(self, tmp_path: Path) -> None:
        destination = tmp_path / "missing/nested/my-vault"
        assert init_vault(destination) == destination
        assert not validate(destination).failed

    def test_parent_is_file(self, tmp_path: Path) -> None:
        parent = tmp_path / "file"
        parent.write_text("Unchanged")
        with pytest.raises(OSError):
            init_vault(parent / "my-vault")
        assert parent.read_text() == "Unchanged"

    @pytest.mark.parametrize("error", [OSError("copy failed"), KeyboardInterrupt()])
    def test_copy_failure_cleans_up_and_allows_retry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: BaseException
    ) -> None:
        target = tmp_path / "new-parent/setting"

        def fail_copy(source: Path, destination: Path, **kwargs: object) -> None:
            (destination / "partial.md").write_text("Incomplete")
            raise error

        with monkeypatch.context() as patch:
            patch.setattr("armarium.init.shutil.copytree", fail_copy)
            with pytest.raises(type(error)) as exc:
                init_vault(target)
            assert exc.value is error
        assert not target.exists()
        assert init_vault(target) == target
        assert not (target / "partial.md").exists()

    def test_lookup_failure_leaves_no_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "armarium.init._starter",
            Mock(side_effect=FileNotFoundError("Missing starter")),
        )
        with pytest.raises(FileNotFoundError, match="Missing starter"):
            init_vault(tmp_path / "setting")
        assert list(tmp_path.iterdir()) == []
