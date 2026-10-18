"""Rename a record and rewrite every link to it."""

from pathlib import Path

from armarium.edit import add_alias
from armarium.index import STRUCTURAL_TYPES, VaultIndex, name_key, read_record
from armarium.lib import check_destination, check_name, relative_posix
from armarium.parse import PARSE_ERRORS
from armarium.relink import RelinkChange, Relinker, RelinkPlan, check_movable


def rename(
    path: Path, name: str, vault: Path | None = None, *, alias: bool = False
) -> RelinkPlan:
    """Plan renaming a record in its folder and rewriting every link to it.

    Args:
        path: The record. With a vault, a relative path is taken from the
            vault root; without one, from the working directory.
        name: Its new name, without a path or .md.
        vault: Vault root, or None to discover the vault from the record's
            location.
        alias: Keep the old name as an alias, and as the display text of
            body links that have none, so prose keeps its wording.

    Returns:
        RelinkPlan: The rename and the link changes, not yet made.

    Raises:
        ValueError: The record cannot be renamed, the name is unusable or
            already a record's name, or a record that may link to it cannot
            be rewritten.
        FileExistsError: An entry in the record's folder has the name,
            ignoring case and Unicode normalization.
        OSError: A file or directory cannot be read.
    """
    root, located, record = read_record(path, vault)
    frontmatter = record.frontmatter
    check_movable(relative_posix(located, root), frontmatter)
    check_name(name)
    if name == located.stem:
        raise ValueError(f"{located.name} already has that name")
    new = located.with_name(f"{name}.md")
    check_destination(new, normalize=True, replacing=located)
    taken: list[str] = []
    if frontmatter.type not in STRUCTURAL_TYPES:
        others = VaultIndex(root).sharing_name(located, name)
        taken = list(dict.fromkeys(relative_posix(o.path, root) for o in others))
    if taken:
        raise ValueError(f"{name} is already a name of {', '.join(taken)}")
    plan = Relinker(root, {located: new}, keep_text=alias).plan()
    plan.files.moves[located] = new
    relative = relative_posix(located, root)
    if alias and name_key(name) != name_key(located.stem):
        text = plan.files.read_text(located)
        try:
            added = add_alias(text, located.stem)
        except PARSE_ERRORS as exc:
            raise ValueError(f"cannot add an alias to {relative}: {exc}") from exc
        if added is not None:
            plan.files.write_text(located, added)
            plan.changes.insert(
                0, RelinkChange(relative, "aliases", 0, f"added {located.stem}")
            )
    plan.changes.insert(
        0, RelinkChange(relative, "", 0, f"renamed to {relative_posix(new, root)}")
    )
    return plan
