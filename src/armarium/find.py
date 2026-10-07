"""Find a vault's records by name or alias without validating them."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from armarium.add import select_vault
from armarium.index import name_key, read_names
from armarium.lib import find_campaign
from armarium.parse import Frontmatter

# Match kinds in the order they are listed.
KINDS = ("name", "alias")


@dataclass(frozen=True)
class Match:
    """One record whose name or alias matches a query.

    Attributes:
        path: Absolute path of the record.
        relative: Its vault-relative path, with forward slashes.
        kind: The record's type, followed by ``/`` and its subtype when it has
            one, such as ``Content/NPC``. Empty for an untyped record.
        match: ``name`` when the filename is the query, ``alias`` when one
            of the record's aliases is.
        summary: The record's summary on one line, or empty.
    """

    path: Path
    relative: str
    kind: str
    match: str
    summary: str

    @property
    def line(self) -> str:
        """Return the match as one tab-separated line of output.

        Returns:
            str: Vault-relative path, type, match kind and summary.
        """
        return "\t".join((self.relative, self.kind, self.match, self.summary))


def _read_frontmatter(data: bytes) -> Frontmatter | None:
    """Parse the frontmatter of a record's bytes, leaving its body unread.

    Args:
        data: Contents of a Markdown file.

    Returns:
        Frontmatter | None: The parsed metadata, empty when the record has
            none, or None when the file cannot be decoded or parsed.
    """
    try:
        return Frontmatter.parse(data.decode("utf-8-sig"))[0]
    except UnicodeError, yaml.YAMLError, ValueError, RecursionError:
        return None


def find_records(
    name: str, vault: Path | None = None, *, campaign: int | None = None
) -> list[Match]:
    """List the records whose filename or one of whose aliases is a name.

    Names compare as link targets do: ignoring case and Unicode spelling.

    Args:
        name: Name to look for, without a path or .md.
        vault: Vault root, or None to discover it from the working directory.
        campaign: Only list shared records and those of this campaign. When
            omitted, every campaign's records are listed, wherever the command
            is run.

    Returns:
        list[Match]: Records with that name, then records with that alias,
            each group in path order; a record with both is listed once, by
            name. Templates, hidden entries and the vault's optional root
            entries are not searched. A file that cannot be read or parsed is
            listed by its name, without type or summary, since its aliases
            are unknown.

    Raises:
        ValueError: The name is blank, the vault cannot be identified or the
            campaign does not exist.
        OSError: A directory cannot be read.
    """
    query = name_key(name)
    if not query:
        raise ValueError("name must not be blank")
    root = select_vault(vault)
    scope = None if campaign is None else f"campaign_{campaign}"
    if scope is not None and not (root / "campaigns" / scope).is_dir():
        raise ValueError(f"campaign {campaign} does not exist")
    kinds: dict[Path, str] = {}
    for found in read_names(root).get(query, []):
        if scope is not None and find_campaign(found.path, root) not in (None, scope):
            continue
        if not found.alias or found.path not in kinds:
            kinds[found.path] = "alias" if found.alias else "name"
    matches: list[Match] = []
    for path, match in kinds.items():
        try:
            frontmatter = _read_frontmatter(path.read_bytes()) or Frontmatter()
        except OSError:
            frontmatter = Frontmatter()
        label = frontmatter.type or ""
        subtype = frontmatter.get("subtype")
        if label and isinstance(subtype, str):
            label += f"/{subtype}"
        summary = frontmatter.get("summary")
        matches.append(
            Match(
                path,
                path.relative_to(root).as_posix(),
                label,
                match,
                " ".join(summary.split()) if isinstance(summary, str) else "",
            )
        )
    return sorted(matches, key=lambda m: (KINDS.index(m.match), m.relative))
