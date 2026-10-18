"""Rename a record and rewrite every link to it."""

from pathlib import Path

from armarium.index import STRUCTURAL_TYPES, VaultIndex
from armarium.lib import check_name, relative_posix
from armarium.relink import RelinkChange, Relinker, RelinkPlan, read_record
from armarium.trace import locate


def rename(path: Path, name: str, vault: Path | None = None) -> RelinkPlan:
    """Plan renaming a record in its folder and rewriting every link to it.

    Args:
        path: The record. With a vault, a relative path is taken from the
            vault root; without one, from the working directory.
        name: Its new name, without a path or .md.
        vault: Vault root, or None to discover the vault from the record's
            location.

    Returns:
        RelinkPlan: The rename and the link changes, not yet made.

    Raises:
        ValueError: The record cannot be renamed, the name is unusable or
            already taken, or a record that may link to it cannot be
            rewritten.
        OSError: A file or directory cannot be read.
    """
    root, located = locate(path, vault)
    frontmatter = read_record(root, located)
    check_name(name)
    if name == located.stem:
        raise ValueError(f"{located.name} already has that name")
    new = located.with_name(f"{name}.md")
    if new.exists() and not new.samefile(located):
        raise ValueError(f"{relative_posix(new, root)} already exists")
    taken: list[str] = []
    if frontmatter.type not in STRUCTURAL_TYPES:
        others = VaultIndex(root).sharing_name(located, name)
        taken = list(dict.fromkeys(relative_posix(o.path, root) for o in others))
    if taken:
        raise ValueError(f"{name} is already a name of {', '.join(taken)}")
    plan = Relinker(root, {located: new}).plan()
    plan.files.moves[located] = new
    relative = relative_posix(located, root)
    plan.changes.insert(
        0, RelinkChange(relative, "", 0, f"renamed to {relative_posix(new, root)}")
    )
    return plan
