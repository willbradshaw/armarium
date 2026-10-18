"""Make a planned set of changes to a vault's files, all of them or none."""

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from armarium.logging import logger

# The kinds of change, in the order apply makes them, with their past tense.
ACTIONS = {
    "create": "created",
    "replace": "replaced",
    "move": "moved",
    "delete": "deleted",
}


@dataclass(frozen=True)
class FileChange:
    """One file's planned change.

    Attributes:
        action: One of ACTIONS.
        path: The file's vault-relative POSIX path.
        destination: For a move, the file's new vault-relative path.
    """

    action: str
    path: str
    destination: str | None = None


def report_changes(changes: list[FileChange], *, dry_run: bool) -> None:
    """Log each file change, then how many files changed.

    Args:
        changes: The changes, as apply returns them.
        dry_run: Whether the changes were only planned.
    """
    for change in changes:
        verb = ACTIONS[change.action]
        if dry_run:
            verb = f"would be {verb}"
        if change.destination is None:
            logger.info("%s: %s", change.path, verb)
        else:
            logger.info("%s: %s to %s", change.path, verb, change.destination)
    count = len({change.path for change in changes})
    logger.info(
        "%s %s %s",
        count,
        "file" if count == 1 else "files",
        "would change" if dry_run else "changed",
    )


@dataclass
class FileChanges:
    """Writes, moves and deletes planned for one vault, made together by apply.

    A command plans its changes here and calls apply, which checks and makes
    them, or on a dry run only checks them; either way it returns them for
    report_changes. Paths are absolute or relative to root, and must lie
    inside it.

    Attributes:
        root: Vault directory.
        writes: New contents of each file to create or replace, by its path
            before any move. A write to a path also being deleted is skipped.
        moves: Each file to move, to its new path.
        deletes: Files to delete.
    """

    root: Path
    writes: dict[Path, bytes] = field(default_factory=dict)
    moves: dict[Path, Path] = field(default_factory=dict)
    deletes: set[Path] = field(default_factory=set)

    def _resolve(self, path: Path) -> Path:
        """Place a path in the vault, refusing one outside it.

        Raises:
            ValueError: The path lies outside root.
        """
        resolved = self.root / path
        if ".." in resolved.parts or not resolved.is_relative_to(self.root):
            raise ValueError(f"change must stay inside the vault: {path}")
        return resolved

    def _check_moves(self, moves: dict[Path, Path]) -> None:
        """Refuse moves that would lose or overwrite a file.

        A destination may exist only as the moving file itself, as in a
        rename that changes only case on a case-insensitive filesystem.

        Raises:
            FileNotFoundError: A file to move is missing.
            FileExistsError: A destination is another existing file, or the
                destination of more than one move.
        """
        destinations: set[Path] = set()
        for old, new in moves.items():
            if not old.is_file():
                raise FileNotFoundError(f"cannot move missing file {old}")
            if new in destinations:
                raise FileExistsError(f"two files would move to {new}")
            destinations.add(new)
            if new.exists() and not os.path.samefile(old, new):
                raise FileExistsError(f"cannot move {old} onto existing {new}")

    def _plan(self) -> tuple[dict[Path, bytes], dict[Path, Path], set[Path]]:
        """Resolve the changes and refuse any that cannot be made.

        Returns:
            tuple: The writes, less those to deleted paths, the moves and the
                deletes, by resolved path.

        Raises:
            ValueError: A path lies outside the vault.
            FileNotFoundError: A file to move or delete is missing.
            FileExistsError: A move would overwrite another file.
        """
        deletes = {self._resolve(path) for path in self.deletes}
        writes = {
            resolved: content
            for path, content in self.writes.items()
            if (resolved := self._resolve(path)) not in deletes
        }
        moves = {self._resolve(o): self._resolve(n) for o, n in self.moves.items()}
        self._check_moves(moves)
        for path in deletes:
            if not path.is_file():
                raise FileNotFoundError(f"cannot delete missing file {path}")
        return writes, moves, deletes

    def _describe(
        self, writes: dict[Path, bytes], moves: dict[Path, Path], deletes: set[Path]
    ) -> list[FileChange]:
        """List resolved changes by path, each path's in the order apply makes them.

        Returns:
            list[FileChange]: The changes, with vault-relative paths.
        """

        def relative(path: Path) -> str:
            return path.relative_to(self.root).as_posix()

        changes = [
            FileChange("replace" if path.exists() else "create", relative(path))
            for path in writes
        ]
        changes += [
            FileChange("move", relative(o), relative(n)) for o, n in moves.items()
        ]
        changes += [FileChange("delete", relative(path)) for path in deletes]
        order = list(ACTIONS)
        return sorted(changes, key=lambda c: (c.path, order.index(c.action)))

    def apply(self, *, prune: bool = False, dry_run: bool = False) -> list[FileChange]:
        """Make the writes, then the moves, then the deletes.

        Each write replaces its file whole. Every touched file is first copied
        into a hidden ``.armarium-changes-`` directory at the vault root,
        which vault traversal never reads; a failure or interruption at any
        point restores the vault from it, and success removes it. If restoring
        fails, the directory is kept, and its location logged, for recovery.

        Args:
            prune: Also remove the directories that moves and deletes leave
                empty, up to the vault root.
            dry_run: Check the changes, refusing them as a real run would,
                without making any.

        Returns:
            list[FileChange]: The changes made, or on a dry run that would be.

        Raises:
            ValueError: A path lies outside the vault.
            FileNotFoundError: A file to move or delete is missing.
            FileExistsError: A move would overwrite another file.
            OSError: A change fails; the vault is restored.
        """
        root = self.root
        writes, moves, deletes = self._plan()
        planned = self._describe(writes, moves, deletes)
        if dry_run:
            return planned
        workspace = Path(tempfile.mkdtemp(prefix=".armarium-changes-", dir=root))
        backup = workspace / "backup"
        for path in {*writes, *moves, *deletes}:
            if path.is_file():
                saved = backup / path.relative_to(root)
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, saved)
        # Changes made so far, undone in reverse order on failure.
        done: list[tuple[str, Path, Path | None]] = []

        def make_parents(directory: Path) -> None:
            missing = [d for d in (directory, *directory.parents) if not d.exists()]
            for created in reversed(missing):
                created.mkdir()
                done.append(("mkdir", created, None))

        committed = restored = False
        try:
            for path, content in writes.items():
                make_parents(path.parent)
                existed = path.exists()
                temporary = path.with_name(f".{path.name}.armarium-tmp")
                done.append(("tmp", temporary, None))
                temporary.write_bytes(content)
                os.replace(temporary, path)
                done.append(("write" if existed else "create", path, None))
            for old, new in moves.items():
                make_parents(new.parent)
                old.rename(new)
                done.append(("move", old, new))
            for path in sorted(deletes):
                path.unlink()
                done.append(("delete", path, None))
            if prune:
                for directory in sorted(
                    {p.parent for p in (*moves, *deletes)}, key=lambda d: -len(d.parts)
                ):
                    while (
                        directory != root
                        and directory.is_dir()
                        and not any(directory.iterdir())
                    ):
                        directory.rmdir()
                        done.append(("rmdir", directory, None))
                        directory = directory.parent
            committed = True
        except BaseException:
            for action, path, other in reversed(done):
                saved = backup / path.relative_to(root)
                if action == "rmdir":
                    path.mkdir(exist_ok=True)
                elif action == "mkdir":
                    if path.is_dir() and not any(path.iterdir()):
                        path.rmdir()
                elif action == "move" and other is not None:
                    other.rename(path)
                elif action in ("write", "delete"):
                    shutil.copy2(saved, path)
                elif action in ("create", "tmp"):
                    path.unlink(missing_ok=True)
            restored = True
            raise
        finally:
            if committed or restored:
                shutil.rmtree(workspace)
            else:
                logger.error("Could not restore the vault; its files are in %s", backup)
        return planned
