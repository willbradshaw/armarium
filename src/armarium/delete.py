"""Delete a record, refusing while links to it remain unless asked to unlink them."""

from pathlib import Path

from armarium.changes import FileChanges
from armarium.index import read_record
from armarium.lib import relative_posix
from armarium.relink import (
    Refused,
    RelinkChange,
    Relinker,
    RelinkPlan,
    check_movable,
)
from armarium.trace import Reference, trace_record
from armarium.validate import IMAGE_URL

# Types whose records define the vault.
DEFINING_TYPES = ("Status", "Type")


class StillLinked(Refused):
    """A record to delete still has links to it.

    Attributes:
        references: The links, as armarium trace lists them.
    """

    def __init__(self, relative: str, references: list[Reference]) -> None:
        """Describe the links that keep a record.

        Args:
            relative: The record's vault-relative path.
            references: The links to it.
        """
        count = len(references)
        super().__init__(
            f"{count} {'link' if count == 1 else 'links'} to {relative} "
            f"{'remains' if count == 1 else 'remain'}; "
            "change them, or pass --unlink to make them plain text",
            [reference.text for reference in references],
        )
        self.references = references


def delete(
    path: Path, vault: Path | None = None, *, unlink: bool = False
) -> RelinkPlan:
    """Plan deleting a record.

    Args:
        path: The record. With a vault, a relative path is taken from the
            vault root; without one, from the working directory.
        vault: Vault root, or None to discover the vault from the record's
            location.
        unlink: Remove the links to the record: a body link becomes its
            display text, an Appearances item naming it is removed, a link
            in a frontmatter list leaves the list and any other frontmatter
            link becomes null.

    Returns:
        RelinkPlan: The deletion and any link changes, not yet made.

    Raises:
        StillLinked: Links to the record remain and unlink is False.
        ValueError: The record cannot be deleted, or a record that may link
            to it cannot be rewritten.
        OSError: A file or directory cannot be read.
    """
    root, located, record = read_record(path, vault)
    relative = relative_posix(located, root)
    check_movable(relative, record.frontmatter, DEFINING_TYPES)
    if unlink:
        plan = Relinker(root, {located: None}).plan()
    else:
        _, references = trace_record(located, root)
        if references:
            raise StillLinked(relative, references)
        plan = RelinkPlan(FileChanges(root))
    plan.files.deletes.add(located)
    plan.changes.insert(0, RelinkChange(relative, "", 0, "deleted"))
    image = record.frontmatter.get("image")
    if isinstance(image, str) and image.strip() and not IMAGE_URL.match(image):
        plan.notes.append(f"{relative}: its image {image} is left in place")
    return plan
