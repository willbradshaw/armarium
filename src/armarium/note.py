"""Create shared or campaign Notes from the selected vault's local template."""

import unicodedata
from pathlib import Path

from armarium.lib import CAMPAIGN_NAME, find_vault, parse_directories
from armarium.logging import logger
from armarium.parse import Record
from armarium.validate import validate


def add_note(
    name: str, vault: Path | None = None, *, campaign: int | None = None
) -> Path:
    """Create and validate a Note without changing existing records.

    Args:
        name: Plain record name without .md; spaces are permitted.
        vault: Vault root, or None to discover it from the working directory.
        campaign: Existing campaign number; infer from the working directory
            within the selected vault when omitted, otherwise use shared scope.

    Returns:
        Path: Absolute destination after local schema and contextual validation.
            The caller can then validate the whole vault.

    Raises:
        ValueError: Invalid name, scope, local scaffolding or generated record.
        OSError: Destination collision or filesystem failure.
        KeyboardInterrupt: Partial creation is removed before propagating.
    """
    if (
        not name
        or name != " ".join(name.split())
        or name.startswith(".")
        or name.endswith(".")
        or name.lower().endswith(".md")
        or any(c in name for c in '/\\\x00[]#|:*?"<>')
        or any(ord(c) < 32 for c in name)
    ):
        raise ValueError(
            "name must be a plain record name without .md, path separators, or reserved characters"
        )
    if campaign is not None and campaign < 1:
        raise ValueError("campaign number must be positive")
    selected = vault.expanduser().resolve() if vault is not None else Path.cwd()
    root = find_vault(selected)
    if vault is not None and root != selected:
        raise ValueError("--vault must name the vault root")
    working_directory = Path.cwd().resolve()
    if campaign is None and working_directory.is_relative_to(root):
        parts = working_directory.relative_to(root).parts
        if (
            len(parts) >= 2
            and parts[0] == "campaigns"
            and CAMPAIGN_NAME.fullmatch(parts[1])
        ):
            campaign = int(parts[1].removeprefix("campaign_"))
    definition, failures = Record.parse(root / "reference/types/Note.md", root)
    if definition is None:
        raise ValueError(f"cannot read Note Type: {failures[0].message}")
    declarations = parse_directories(definition.frontmatter.get("directories"))
    scope = "shared" if campaign is None else "campaign"
    if scope not in declarations:
        raise ValueError(f"Note Type declares no {scope} directory")
    base = root if campaign is None else root / "campaigns" / f"campaign_{campaign}"
    directory = base / declarations[scope]
    # Refuse missing directories and symlinks in every component of the write path.
    for path in (directory, *directory.parents):
        if path == root:
            break
        if not path.is_dir() or path.is_symlink():
            raise ValueError(f"{path} must be an existing real directory")
    destination = directory / f"{name}.md"
    key = unicodedata.normalize("NFC", destination.name).casefold()
    if any(
        unicodedata.normalize("NFC", p.name).casefold() == key
        for p in directory.iterdir()
    ):
        raise FileExistsError(f"record already exists: {destination}")
    template_path = root / "reference/templates/Note.md"
    if any(
        path.is_symlink()
        for path in (template_path, template_path.parent, template_path.parent.parent)
    ):
        raise ValueError("Note template must be a regular file in the vault")
    template, failures = Record.parse(template_path, root)
    if template is None:
        raise ValueError(f"cannot read Note template: {failures[0].message}")
    if template.frontmatter.type != "Note":
        raise ValueError("Note template must declare the Note type")
    text = template_path.read_text(encoding="utf-8")
    logger.info("Adding new Note record at %s", destination)
    stream = destination.open("x", encoding="utf-8")
    try:
        with stream:
            stream.write(text)
        result = validate(destination, root)
        if result.failed:
            for diagnostic in result.diagnostics:
                diagnostic.report()
            raise ValueError(
                "generated Note record failed validation; no record created"
            )
    except BaseException:
        destination.unlink()
        raise
    return destination
