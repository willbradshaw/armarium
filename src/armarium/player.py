"""Create Player records using vault-local templates and directory declarations."""

import unicodedata
from pathlib import Path

import yaml

from armarium.lib import CAMPAIGN_NAME, find_vault, parse_directories
from armarium.logging import logger
from armarium.parse import Record
from armarium.validate import validate


def add_player(
    name: str, vault: Path | None = None, *, campaign: int | None = None
) -> Path:
    """Create and validate a Player without changing PCs or other records.

    Args:
        name: Plain record name without .md; spaces are permitted.
        vault: Vault root, or None to discover it from the working directory.
        campaign: Existing campaign number, or None to infer the current campaign.

    Returns:
        Path: Absolute destination after schema and contextual validation.
            Initial values and body are preserved from the local Player template.

    Raises:
        ValueError: The name, scope, scaffolding or generated record is invalid.
        OSError: The destination exists or a filesystem operation fails.
        KeyboardInterrupt: The partial record is removed before propagating.
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
    selected = vault.expanduser().resolve() if vault is not None else Path.cwd()
    root = find_vault(selected)
    if vault is not None and selected != root:
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
    if campaign is None:
        raise ValueError("specify --campaign or run inside a campaign directory")
    if campaign < 1:
        raise ValueError("campaign number must be positive")
    definition, failures = Record.parse(root / "reference/types/Player.md", root)
    if definition is None:
        raise ValueError(f"cannot read Player Type: {failures[0].message}")
    declarations = parse_directories(definition.frontmatter.get("directories"))
    if "campaign" not in declarations:
        raise ValueError("Player Type declares no campaign directory")
    directory = root / "campaigns" / f"campaign_{campaign}" / declarations["campaign"]
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
    template_path = root / "reference/templates/Player.md"
    if template_path.is_symlink() or template_path.parent.is_symlink():
        raise ValueError("Player template must be a regular file in the vault")
    template, failures = Record.parse(template_path, root)
    if template is None:
        raise ValueError(f"cannot read Player template: {failures[0].message}")
    if template.frontmatter.type != "Player":
        raise ValueError("Player template must declare the Player type")
    metadata = dict(template.frontmatter)
    text = (
        "---\n"
        + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
        + "---\n"
        + template.body.text
    )
    logger.info("Adding new Player record at %s", destination)
    stream = destination.open("x", encoding="utf-8")
    try:
        with stream:
            stream.write(text)
        result = validate(destination, root)
        if result.failed:
            for diagnostic in result.diagnostics:
                diagnostic.report()
            raise ValueError(
                "generated Player record failed validation; no record created"
            )
    except BaseException:
        destination.unlink()
        raise
    return destination
