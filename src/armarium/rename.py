"""Rename a record and rewrite every link to it."""

import re
from pathlib import Path

from armarium.extensions import is_template
from armarium.index import name_key, read_names
from armarium.lib import find_campaign, record_files, relative_posix
from armarium.parse import Frontmatter
from armarium.relink import PARSE_ERRORS, Change, Plan, Relinker
from armarium.trace import locate
from armarium.validate import CAMPAIGN_FILES, STRUCTURAL_TYPES

# Types whose records have names the vault gives them, or that define the vault.
FIXED_TYPES = ("Clue", "Session", "Status", "Transcript", "Type")

# Characters a name may not hold: Obsidian's link syntax and path separators.
FORBIDDEN = re.compile(r"[#^\[\]|\\/:]")

# A campaign's required files, such as campaigns/campaign_1/reference/Campaign.md.
REQUIRED = re.compile(
    r"campaigns/campaign_[1-9][0-9]*/("
    + "|".join(re.escape(path) for path in CAMPAIGN_FILES)
    + ")"
)


def read_record(root: Path, path: Path) -> Frontmatter:
    """Read the frontmatter of a record that a command may rename or remove.

    Args:
        root: Resolved vault directory.
        path: The record, inside the vault.

    Returns:
        Frontmatter: The record's frontmatter.

    Raises:
        ValueError: The file is not a record of the vault, cannot be parsed,
            is of a type whose names the vault fixes or that defines the
            vault, or is a file a campaign requires.
    """
    relative = relative_posix(path, root)
    if (
        path.suffix.lower() != ".md"
        or path not in record_files(path.parent, root)
        or is_template(path, root)
    ):
        raise ValueError(f"{relative} is not a record")
    try:
        frontmatter = Frontmatter.parse(path.read_text(encoding="utf-8-sig"))[0]
    except PARSE_ERRORS as exc:
        raise ValueError(f"cannot parse {relative}: {exc}") from exc
    if frontmatter.type in FIXED_TYPES:
        raise ValueError(
            f"{relative} is a {frontmatter.type} record, whose name the vault fixes"
        )
    if REQUIRED.fullmatch(relative):
        raise ValueError(f"{relative} is a file every campaign requires")
    return frontmatter


def check_name(name: str) -> None:
    """Require a name that a record's filename can take.

    Args:
        name: The name, without a path or .md.

    Raises:
        ValueError: The name is blank, has surrounding whitespace, starts with
            a dot, ends with .md or holds a character of link syntax or a
            path separator.
    """
    if not name.strip():
        raise ValueError("the new name must not be blank")
    if name != name.strip():
        raise ValueError("the new name must not start or end with whitespace")
    if name.startswith("."):
        raise ValueError("the new name must not start with a dot")
    if name.lower().endswith(".md"):
        raise ValueError("give the new name without .md")
    if FORBIDDEN.search(name):
        raise ValueError("the new name must not contain any of # ^ [ ] | \\ / :")


def clashes(root: Path, path: Path, name: str, frontmatter: Frontmatter) -> list[str]:
    """List the other records that go by a name where a record is visible.

    Args:
        root: Resolved vault directory.
        path: The record.
        name: A name for it.
        frontmatter: Its frontmatter.

    Returns:
        list[str]: The vault-relative paths of the records, other than this
            one, with the name as filename or alias, among the shared records
            and those of any campaign this record is visible in. Structural
            records take no part, as in validation.
    """
    if frontmatter.type in STRUCTURAL_TYPES:
        return []
    scope = find_campaign(path, root)
    found: list[str] = []
    for other in read_names(root).get(name_key(name), []):
        if other.path == path:
            continue
        visible = find_campaign(other.path, root)
        if scope is not None and visible is not None and scope != visible:
            continue
        try:
            kind = Frontmatter.parse(other.path.read_text(encoding="utf-8-sig"))[0].type
        except (OSError, *PARSE_ERRORS):
            kind = None
        relative = relative_posix(other.path, root)
        if kind not in STRUCTURAL_TYPES and relative not in found:
            found.append(relative)
    return found


def rename(path: Path, name: str, vault: Path | None = None) -> Plan:
    """Plan renaming a record in its folder and rewriting every link to it.

    Args:
        path: The record. With a vault, a relative path is taken from the
            vault root; without one, from the working directory.
        name: Its new name, without a path or .md.
        vault: Vault root, or None to discover the vault from the record's
            location.

    Returns:
        Plan: The rename and the link changes, not yet made.

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
    taken = clashes(root, located, name, frontmatter)
    if taken:
        raise ValueError(f"{name} is already a name of {', '.join(taken)}")
    plan = Relinker(root, {located: new}).plan()
    plan.renamed[located] = new
    relative = relative_posix(located, root)
    plan.changes.insert(
        0, Change(relative, "", 0, f"renamed to {relative_posix(new, root)}")
    )
    return plan
