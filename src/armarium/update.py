"""Bring a vault's managed copies of starter files up to date."""

import hashlib
import json
from dataclasses import dataclass, field, replace
from difflib import SequenceMatcher
from importlib.resources import as_file
from pathlib import Path

from packaging.version import Version

from armarium.changes import FileChange, FileChanges
from armarium.extensions import (
    armarium_version,
    installed_extensions,
    installed_files,
    supplied_files,
    update_extension,
)
from armarium.init import starter
from armarium.lib import RECORD, managed_files, read_settings, select_vault

# Lines that set off the vault's and Armarium's sides of a conflict.
CONFLICT_MARKERS = ("<<<<<<< vault\n", "=======\n", ">>>>>>> armarium\n")
# Where an update leaves conflicting merges for the vault to resolve, in the
# vault's scratch directory, which is never committed.
PENDING = Path(".scratch/armarium-update")
# The digests of the vault's and Armarium's files each pending merge combines.
INPUTS = PENDING / "conflicts.json"
# Actions that write or delete the vault's file.
WRITES = frozenset({"added", "updated", "merged", "resolved", "removed"})
# What each action does, for reports, where its file change does not say.
DESCRIPTIONS = {
    "merged": "merged with the vault's changes",
    "conflict": (
        f"conflicts with the vault's changes; resolve it in {PENDING.as_posix()}/"
    ),
    "resolved": f"merged with its resolution from {PENDING.as_posix()}/",
    "released": "kept as the vault's own, as Armarium no longer supplies it",
    "omitted": "left out, as the vault deleted it",
    "local": "left as the vault's own",
    "kept": "kept with the vault's changes",
}


@dataclass(frozen=True)
class Change:
    """What an update does, or would do, to one managed file.

    content is the file's new contents for an action that writes it, or for a
    conflict the merge with both sides marked; otherwise None.
    """

    path: str
    action: str
    content: bytes | None = None

    @property
    def writes(self) -> bool:
        """Return whether the change writes or deletes the vault's file."""
        return self.action in WRITES


@dataclass(frozen=True)
class Update:
    """A vault's update to the running Armarium's managed files.

    previous is the version the vault's record names, or None for a vault
    without a record. files are the file changes that make the update,
    including the record's, once planned in full. extensions maps each
    installed extension the update replaces to its file changes.
    """

    root: Path
    previous: str | None
    version: str
    changes: list[Change]
    files: list[FileChange] = field(default_factory=list)
    extensions: dict[str, list[FileChange]] = field(default_factory=dict)

    @property
    def conflicts(self) -> list[str]:
        """Return the paths whose merge conflicts and has no resolution."""
        return [c.path for c in self.changes if c.action == "conflict"]

    @property
    def vault_files(self) -> list[FileChange]:
        """Return the file changes outside the record and pending merges."""
        hidden = (RECORD.as_posix() + "/", PENDING.as_posix() + "/")
        return [f for f in self.files if not f.path.startswith(hidden)]


def _lines(content: bytes) -> list[str]:
    """Split contents into lines, round-tripping bytes that are not UTF-8."""
    return content.decode("utf-8", "surrogateescape").splitlines(keepends=True)


def _terminated(lines: list[str]) -> list[str]:
    """Return lines whose last one ends with a newline, for a conflict marker."""
    if lines and not lines[-1].endswith("\n"):
        return [*lines[:-1], lines[-1] + "\n"]
    return lines


def _sync_regions(
    base: list[str], vault: list[str], new: list[str]
) -> list[tuple[int, int, int, int]]:
    """Find the base lines that neither the vault nor Armarium changed.

    Args:
        base: Lines of the recorded copy.
        vault: Lines of the vault's file.
        new: Lines of the running Armarium's file.

    Returns:
        list[tuple[int, int, int, int]]: Each unchanged region's start and end
            in base, then its start in vault and in new, in order, ending
            with an empty region at the end of all three.
    """
    ours = SequenceMatcher(None, base, vault, autojunk=False).get_matching_blocks()
    theirs = SequenceMatcher(None, base, new, autojunk=False).get_matching_blocks()
    regions: list[tuple[int, int, int, int]] = []
    i = j = 0
    while i < len(ours) and j < len(theirs):
        (a_base, a_vault, a_length), (b_base, b_new, b_length) = ours[i], theirs[j]
        start = max(a_base, b_base)
        end = min(a_base + a_length, b_base + b_length)
        if start < end:
            regions.append(
                (start, end, a_vault + start - a_base, b_new + start - b_base)
            )
        if a_base + a_length < b_base + b_length:
            i += 1
        else:
            j += 1
    regions.append((len(base), len(base), len(vault), len(new)))
    return regions


def merge3(base: bytes, vault: bytes, new: bytes) -> tuple[bytes, bool]:
    """Combine the vault's and Armarium's changes to a recorded copy, by line.

    Args:
        base: The recorded copy.
        vault: The vault's file.
        new: The running Armarium's file.

    Returns:
        tuple[bytes, bool]: The merged contents, and whether both sides changed
            the same lines. Each such place holds both versions between
            CONFLICT_MARKERS, the vault's first.
    """
    old, ours, theirs = _lines(base), _lines(vault), _lines(new)
    merged: list[str] = []
    conflicted = False
    o = v = n = 0
    for start, end, v_start, n_start in _sync_regions(old, ours, theirs):
        before, mine, upstream = old[o:start], ours[v:v_start], theirs[n:n_start]
        if mine == upstream or upstream == before:
            merged += mine
        elif mine == before:
            merged += upstream
        else:
            conflicted = True
            first, between, last = CONFLICT_MARKERS
            merged += [first, *_terminated(mine), between, *_terminated(upstream), last]
        merged += old[start:end]
        o, v, n = end, v_start + end - start, n_start + end - start
    return "".join(merged).encode("utf-8", "surrogateescape"), conflicted


def _classify(
    path: str,
    base: bytes | None,
    vault: bytes | None,
    new: bytes | None,
    *,
    adopting: bool,
) -> Change | None:
    """Decide what an update does to one managed file.

    Args:
        path: The file's vault-relative path.
        base: Its recorded copy, or None when the record has none.
        vault: The vault's file, or None when it is missing.
        new: The running Armarium's file, or None when Armarium dropped it.
        adopting: The vault had no record, so base is the running Armarium's
            file; every way the vault differs is reported.

    Returns:
        Change | None: The change, or None when there is nothing to do or report.
    """
    if new is None:
        if vault is None:
            return None
        return Change(path, "removed") if vault == base else Change(path, "released")
    if vault is None:
        if base is None:
            return Change(path, "added", new)
        return Change(path, "omitted") if adopting or new != base else None
    if vault == new:
        return None
    if vault == base:
        return Change(path, "updated", new)
    if new == base:
        return Change(path, "kept") if adopting else None
    merged, conflicted = merge3(base or b"", vault, new)
    return Change(path, "conflict" if conflicted else "merged", merged)


def _vault_file(root: Path, relative: str) -> bytes | None:
    """Read a vault's copy of a managed file, or None when it is missing.

    Raises:
        ValueError: The path is reached through a symlink or is not a file.
    """
    path = root / relative
    if any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(root)):
        raise ValueError(f"managed file must not use symlinks: {relative}")
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError(f"managed file is not a file: {relative}")
    return path.read_bytes()


def _marked(content: bytes) -> bool:
    """Return whether contents hold a conflict between the vault and Armarium."""
    lines = _lines(content)
    return CONFLICT_MARKERS[0] in lines and CONFLICT_MARKERS[2] in lines


def _inputs(vault: bytes | None, new: bytes | None) -> dict[str, str]:
    """Identify the vault's and Armarium's files that a merge combines."""
    return {
        side: hashlib.sha256(content or b"").hexdigest()
        for side, content in (("vault", vault), ("new", new))
    }


def _pending_inputs(root: Path) -> dict[str, dict[str, str]]:
    """Read which files each pending merge combines, by managed path.

    Returns:
        dict[str, dict[str, str]]: The inputs recorded for each pending merge;
            empty when there are none or the record of them is unreadable,
            so that every conflict is merged afresh.
    """
    path = root / INPUTS
    try:
        inputs = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return {}
    return inputs if isinstance(inputs, dict) else {}


def plan_update(
    root: Path, new: dict[str, bytes], *, allow_downgrade: bool = False
) -> Update:
    """Decide how to bring a vault's managed files to the given copies.

    Args:
        root: Vault root.
        new: The running Armarium's managed files, as managed_files reads them.
        allow_downgrade: Allow a vault recorded with a newer Armarium.

    Returns:
        Update: The changes, ordered by path.

    Raises:
        ValueError: The record is invalid or newer than the running Armarium
            without allow_downgrade, or a managed path is unusable.
        OSError: The record or a managed file cannot be read.
    """
    record = root / RECORD
    version = armarium_version()
    if record.is_symlink():
        raise ValueError(f"{RECORD} must not be a symlink")
    if record.exists():
        settings = read_settings(record)
        previous: str | None = settings["armarium_version"]
        local = set(settings["local"])
        base = managed_files(record / "base")
        if Version(settings["armarium_version"]) > Version(version) and not (
            allow_downgrade
        ):
            raise ValueError(
                f"vault was updated with newer Armarium {previous}; current "
                f"version is {version}. Use --allow-downgrade to update it."
            )
    else:
        previous, local, base = None, set(), new
    inputs = _pending_inputs(root)
    changes = []
    for path in sorted(base.keys() | new.keys()):
        if path in local:
            if base.get(path) != new.get(path):
                changes.append(Change(path, "local"))
            continue
        vault = _vault_file(root, path)
        change = _classify(
            path, base.get(path), vault, new.get(path), adopting=previous is None
        )
        if change is not None and change.action == "conflict":
            resolution = root / PENDING / path
            if (
                inputs.get(path) == _inputs(vault, new.get(path))
                and resolution.is_file()
                and not resolution.is_symlink()
                and not _marked(resolution.read_bytes())
            ):
                change = Change(path, "resolved", resolution.read_bytes())
        if change is not None:
            changes.append(change)
    return Update(root, previous, version, changes)


def _file_changes(
    update: Update, new: dict[str, bytes], local: list[str]
) -> FileChanges:
    """Plan the file changes that make an update without conflicts.

    Besides the managed files, the record is brought to the running
    Armarium's files and version, and resolved pending merges are deleted.

    Args:
        update: The planned update.
        new: The running Armarium's managed files, recorded as the new base.
        local: Managed paths the vault keeps as its own.

    Returns:
        FileChanges: The changes, to apply with pruning.
    """
    root = update.root
    changes = FileChanges(root)
    for change in update.changes:
        if change.action == "removed":
            changes.deletes.add(root / change.path)
        elif change.writes and change.content is not None:
            changes.writes[root / change.path] = change.content
    base = root / RECORD / "base"
    recorded = managed_files(base) if base.is_dir() else {}
    for relative, content in new.items():
        if recorded.get(relative) != content:
            changes.writes[base / relative] = content
    changes.deletes |= {base / relative for relative in recorded.keys() - new.keys()}
    settings = {"armarium_version": update.version, "local": sorted(local)}
    changes.writes[root / RECORD / "vault.json"] = (
        json.dumps(settings, indent=2) + "\n"
    ).encode()
    pending = root / PENDING
    if pending.is_dir() and not pending.is_symlink():
        changes.deletes |= {p for p in pending.rglob("*") if p.is_file()}
    return changes


def _write_pending(update: Update, new: dict[str, bytes]) -> None:
    """Leave each unresolved conflict's merge for the vault to resolve.

    A merge already pending from the same files is kept, so that work on its
    resolution is not lost; any other is written afresh.

    Args:
        update: The planned update, with conflicts.
        new: The running Armarium's managed files.
    """
    root = update.root
    inputs = _pending_inputs(root)
    changes = FileChanges(root)
    for change in update.changes:
        if change.action != "conflict" or change.content is None:
            continue
        current = _inputs(_vault_file(root, change.path), new.get(change.path))
        pending = root / PENDING / change.path
        if inputs.get(change.path) != current or not pending.is_file():
            changes.writes[pending] = change.content
            inputs[change.path] = current
    changes.writes[root / INPUTS] = (json.dumps(inputs, indent=2) + "\n").encode()
    changes.apply()


def outdated_extensions(root: Path) -> dict[str, list[FileChange]]:
    """Find the installed extensions whose files differ from those Armarium supplies.

    Args:
        root: Vault root.

    Returns:
        dict[str, list[FileChange]]: The file changes, by path, that an update
            of each such extension makes, by extension name.

    Raises:
        ValueError: The extension configuration is invalid, or Armarium no
            longer supplies an installed extension.
        OSError: An extension's files cannot be read.
    """
    outdated: dict[str, list[FileChange]] = {}
    for name in installed_extensions(root):
        installed, supplied = installed_files(root, name), supplied_files(root, name)
        changes = [
            FileChange(
                "create"
                if path not in installed
                else "delete"
                if path not in supplied
                else "replace",
                path,
            )
            for path in sorted(installed.keys() | supplied.keys())
            if installed.get(path) != supplied.get(path)
        ]
        if changes:
            outdated[name] = changes
    return outdated


def update_vault(
    vault: Path | None = None,
    *,
    dry_run: bool = False,
    allow_downgrade: bool = False,
    extensions: bool = False,
) -> Update:
    """Bring a vault's managed files up to date with the running Armarium.

    A file the vault has not changed is replaced; one both have changed is
    merged by line. Files the vault deleted or keeps as its own are left
    alone. A vault without a record is taken to have been copied from the
    running Armarium. The record is rewritten even when no file changes. With
    extensions, each out-of-date installed extension is then replaced, as
    update_extension does, after the managed files.

    Where the vault and Armarium changed the same lines, nothing is changed:
    each such merge, both sides marked, is left in PENDING for the vault to
    resolve. Once every pending merge is resolved and its markers removed, the
    next update applies the resolutions with everything else, and deletes
    them. Callers validate the vault after an update that changes it.

    Args:
        vault: Vault root, or None to find the vault containing the current
            directory.
        dry_run: Plan and check the update without changing the vault or
            PENDING.
        allow_downgrade: Allow a vault or extension recorded with a newer
            Armarium.
        extensions: Also update installed extensions.

    Returns:
        Update: The changes planned, with their file changes. They were made
            unless this is a dry run or the update has conflicts.

    Raises:
        ValueError: The vault, its record, a managed path or an extension is
            invalid, or the record is newer than the running Armarium without
            allow_downgrade.
        OSError: Reading or writing fails; the managed files, or the
            extension being updated, are restored. Extensions updated before
            a failure stay updated.
    """
    root = select_vault(vault)
    with as_file(starter()) as source:
        new = managed_files(source)
    update = plan_update(root, new, allow_downgrade=allow_downgrade)
    if extensions:
        update = replace(update, extensions=outdated_extensions(root))
    record = root / RECORD
    local = read_settings(record)["local"] if record.exists() else []
    files = _file_changes(update, new, local).apply(
        prune=True, dry_run=dry_run or bool(update.conflicts)
    )
    if update.conflicts and not dry_run:
        _write_pending(update, new)
    elif not dry_run:
        for name in update.extensions:
            update_extension(name, root, allow_downgrade=allow_downgrade)
    return replace(update, files=files)
