"""Making a vault's planned file changes together, and undoing them on failure."""

import logging
import os
from pathlib import Path

import pytest

from armarium.changes import FileChange, FileChanges, report_changes


def snapshot(root: Path) -> dict[str, bytes | None]:
    """Map each entry below root to its contents, or None for a directory."""
    return {
        path.relative_to(root).as_posix(): None if path.is_dir() else path.read_bytes()
        for path in sorted(root.rglob("*"))
    }


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    (root / "content/npcs").mkdir(parents=True)
    (root / "content/npcs/quay.md").write_text("Quay\n")
    (root / "content/Harbor.md").write_text("Harbor\n")
    (root / "sessions").mkdir()
    (root / "sessions/Session 1.md").write_text("Session\n")
    return root


class TestFileChangesResolve:
    @pytest.mark.parametrize(
        ("path", "expected"),
        [("content/a.md", "content/a.md"), ("/abs", None), ("../out.md", None)],
    )
    def test_paths(self, vault: Path, path: str, expected: str | None) -> None:
        changes = FileChanges(vault)
        if expected is None:
            with pytest.raises(ValueError, match="inside the vault"):
                changes._resolve(Path(path))
        else:
            assert changes._resolve(Path(path)) == vault / expected

    def test_absolute_inside(self, vault: Path) -> None:
        assert FileChanges(vault)._resolve(vault / "a.md") == vault / "a.md"


class TestFileChangesCheckMoves:
    @pytest.mark.parametrize(
        ("moves", "error"),
        [
            ({"missing.md": "new.md"}, FileNotFoundError),
            ({"content/Harbor.md": "sessions/Session 1.md"}, FileExistsError),
            (
                {"content/Harbor.md": "new.md", "content/npcs/quay.md": "new.md"},
                FileExistsError,
            ),
        ],
    )
    def test_refuses(
        self, vault: Path, moves: dict[str, str], error: type[Exception]
    ) -> None:
        with pytest.raises(error):
            FileChanges(vault)._check_moves(
                {vault / old: vault / new for old, new in moves.items()}
            )

    def test_allows_same_file(self, vault: Path) -> None:
        path = vault / "content/Harbor.md"
        FileChanges(vault)._check_moves({path: path})


class TestFileChangesPlan:
    def test_resolves(self, vault: Path) -> None:
        writes, moves, deletes = FileChanges(
            vault,
            writes={Path("a.md"): b"A\n", Path("sessions/Session 1.md"): b"S\n"},
            moves={Path("content/Harbor.md"): Path("Port.md")},
            deletes={Path("sessions/Session 1.md")},
        )._plan()
        assert writes == {vault / "a.md": b"A\n"}
        assert moves == {vault / "content/Harbor.md": vault / "Port.md"}
        assert deletes == {vault / "sessions/Session 1.md"}


class TestFileChangesDescribe:
    def test_lists_by_path(self, vault: Path) -> None:
        changes = FileChanges(vault)
        assert changes._describe(
            {vault / "content/Harbor.md": b"", vault / "new.md": b""},
            {vault / "content/Harbor.md": vault / "Port.md"},
            {vault / "sessions/Session 1.md"},
        ) == [
            FileChange("replace", "content/Harbor.md"),
            FileChange("move", "content/Harbor.md", "Port.md"),
            FileChange("create", "new.md"),
            FileChange("delete", "sessions/Session 1.md"),
        ]


class TestReportChanges:
    @pytest.mark.parametrize(
        ("dry_run", "lines"),
        [
            (
                False,
                [
                    "content/Harbor.md: replaced",
                    "content/Harbor.md: moved to Port.md",
                    "new.md: created",
                    "2 files changed",
                ],
            ),
            (
                True,
                [
                    "content/Harbor.md: would be replaced",
                    "content/Harbor.md: would be moved to Port.md",
                    "new.md: would be created",
                    "2 files would change",
                ],
            ),
        ],
    )
    def test_reports(
        self, caplog: pytest.LogCaptureFixture, dry_run: bool, lines: list[str]
    ) -> None:
        with caplog.at_level(logging.INFO, logger="armarium"):
            report_changes(
                [
                    FileChange("replace", "content/Harbor.md"),
                    FileChange("move", "content/Harbor.md", "Port.md"),
                    FileChange("create", "new.md"),
                ],
                dry_run=dry_run,
            )
        assert caplog.messages == lines

    def test_one_file(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="armarium"):
            report_changes([FileChange("delete", "a.md")], dry_run=False)
        assert caplog.messages[-1] == "1 file changed"


class TestFileChangesApply:
    @pytest.mark.parametrize("dry_run", [False, True])
    def test_returns_changes(self, vault: Path, dry_run: bool) -> None:
        before = snapshot(vault)
        changes = FileChanges(
            vault,
            writes={Path("new.md"): b"New\n"},
            moves={Path("content/Harbor.md"): Path("Port.md")},
        ).apply(dry_run=dry_run)
        assert changes == [
            FileChange("move", "content/Harbor.md", "Port.md"),
            FileChange("create", "new.md"),
        ]
        assert (snapshot(vault) == before) is dry_run

    def test_writes_moves_and_deletes(self, vault: Path) -> None:
        FileChanges(
            vault,
            writes={
                Path("content/Harbor.md"): b"Renamed\n",
                Path("notes/new/Plan.md"): b"\xff\x00",
                Path("sessions/Session 1.md"): b"Skipped\n",
            },
            moves={Path("content/Harbor.md"): Path("content/Port.md")},
            deletes={Path("sessions/Session 1.md")},
        ).apply()
        assert snapshot(vault) == {
            "content": None,
            "content/Port.md": b"Renamed\n",
            "content/npcs": None,
            "content/npcs/quay.md": b"Quay\n",
            "notes": None,
            "notes/new": None,
            "notes/new/Plan.md": b"\xff\x00",
            "sessions": None,
        }

    def test_case_only_rename(self, vault: Path) -> None:
        old = vault / "content/npcs/quay.md"
        FileChanges(vault, moves={old: vault / "content/npcs/Quay.md"}).apply()
        assert os.listdir(vault / "content/npcs") == ["Quay.md"]

    @pytest.mark.parametrize("prune", [False, True])
    def test_prune(self, vault: Path, prune: bool) -> None:
        FileChanges(
            vault,
            moves={Path("content/npcs/quay.md"): Path("Quay.md")},
            deletes={Path("sessions/Session 1.md")},
        ).apply(prune=prune)
        assert (vault / "sessions").exists() is not prune
        assert (vault / "content/npcs").exists() is not prune
        assert (vault / "content/Harbor.md").exists()

    @pytest.mark.parametrize(
        ("changes", "error"),
        [
            ({"deletes": {Path("missing.md")}}, FileNotFoundError),
            ({"moves": {Path("missing.md"): Path("x.md")}}, FileNotFoundError),
            ({"writes": {Path("../out.md"): b""}}, ValueError),
        ],
    )
    @pytest.mark.parametrize("dry_run", [False, True])
    def test_refuses_before_changing(
        self,
        vault: Path,
        changes: dict[str, object],
        error: type[Exception],
        dry_run: bool,
    ) -> None:
        before = snapshot(vault)
        with pytest.raises(error):
            FileChanges(vault, **changes).apply(dry_run=dry_run)  # type: ignore[arg-type]
        assert snapshot(vault) == before

    @pytest.mark.parametrize("stage", ["write", "create", "move", "delete", "prune"])
    @pytest.mark.parametrize("error", [OSError("failed"), KeyboardInterrupt()])
    def test_failure_restores(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        stage: str,
        error: BaseException,
    ) -> None:
        before = snapshot(vault)
        changes = FileChanges(
            vault,
            writes={
                Path("content/Harbor.md"): b"Renamed\n",
                Path("notes/new/Plan.md"): b"New\n",
            },
            moves={Path("content/npcs/quay.md"): Path("archive/Quay.md")},
            deletes={Path("sessions/Session 1.md")},
        )
        if stage in ("write", "create"):
            replace = os.replace
            name = "Harbor.md" if stage == "write" else "Plan.md"

            def fail_replace(source: str, target: Path) -> None:
                if Path(target).name == name:
                    raise error
                replace(source, target)

            monkeypatch.setattr("armarium.changes.os.replace", fail_replace)
        elif stage == "move":
            monkeypatch.setattr(Path, "rename", _raise(error, Path.rename))
        elif stage == "delete":
            monkeypatch.setattr(Path, "unlink", _raise(error, Path.unlink))
        else:
            rmdir = Path.rmdir

            def fail_rmdir(path: Path) -> None:
                if path.name == "sessions":
                    raise error
                rmdir(path)

            monkeypatch.setattr(Path, "rmdir", fail_rmdir)
        with pytest.raises(type(error)):
            changes.apply(prune=True)
        monkeypatch.undo()
        assert snapshot(vault) == before

    def test_failed_restore_keeps_backup(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.setattr(Path, "unlink", _raise(OSError("failed"), Path.unlink))
        monkeypatch.setattr("armarium.changes.shutil.copy2", _raise_after_backup())
        with caplog.at_level(logging.ERROR, logger="armarium"):
            with pytest.raises(OSError):
                FileChanges(
                    vault,
                    writes={Path("content/Harbor.md"): b"Changed\n"},
                    deletes={Path("sessions/Session 1.md")},
                ).apply()
        monkeypatch.undo()
        [workspace] = vault.glob(".armarium-changes-*")
        assert (workspace / "backup/content/Harbor.md").read_text() == "Harbor\n"
        assert str(workspace / "backup") in caplog.text


def _raise(error: BaseException, original: object) -> object:
    """Wrap a Path method to raise on its first call for the vault's files."""
    raised: list[bool] = []

    def method(path: Path, *args: object, **kwargs: object) -> object:
        if not raised and ".armarium-changes-" not in str(path):
            raised.append(True)
            raise error
        return original(path, *args, **kwargs)  # type: ignore[operator]

    return method


def _raise_after_backup() -> object:
    """Copy files into the backup, then fail every copy back out of it."""
    import shutil

    copy = shutil.copy2

    def copy2(source: Path, target: Path) -> object:
        if ".armarium-changes-" in str(source):
            raise OSError("cannot restore")
        return copy(source, target)

    return copy2
