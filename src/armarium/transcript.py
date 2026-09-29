"""Create Transcript records from existing Sessions and supplied Markdown."""

from pathlib import Path

import yaml

from armarium.index import VaultIndex
from armarium.lib import find_campaign, find_vault, parse_directories, parse_wikilink
from armarium.logging import logger
from armarium.parse import Body, Frontmatter, Record
from armarium.schemas import select_schema
from armarium.validate import validate, validate_transcript


def add_transcript(
    session: str,
    body_file: Path,
    vault: Path | None = None,
) -> Path:
    """Create and validate a Transcript without changing its Session or source.

    Args:
        session: Unambiguous Session name, qualified vault path or canonical link.
        body_file: UTF-8 Markdown body with titled level-two sections containing
            bullet-list utterances of the form ``- [Speaker] Speech.``. Replaces
            the local template body; frontmatter comes only from the template.
        vault: Vault root, or None to discover it from the working directory.

    Returns:
        Path: Absolute path of the validated S-N-NNN Transcript.md record.

    Raises:
        ValueError: Selection, scaffolding, input or generated record is invalid.
        OSError: Reading or writing fails, or the destination already exists.
        KeyboardInterrupt: Partial creation is removed before propagating.
    """
    selected = vault.expanduser().resolve() if vault is not None else Path.cwd()
    root = find_vault(selected)
    if vault is not None and selected != root:
        raise ValueError("--vault must name the vault root")
    target = parse_wikilink(
        session if session.startswith("[[") else f"[[{session}]]", canonical=True
    )
    index = VaultIndex(root)
    resolved, problem = index.resolve(target, root)
    if problem or resolved is None:
        raise ValueError(
            "session must uniquely identify an existing Session; use a vault-relative path"
        )
    record, _ = index.parse(resolved)
    scope = find_campaign(resolved, root)
    if record is None or record.frontmatter.type != "Session" or scope is None:
        raise ValueError("session must identify a Session in an existing campaign")
    result = validate(resolved, root)
    if result.failed:
        for diagnostic in result.diagnostics:
            diagnostic.report()
        raise ValueError("selected Session failed validation; no record created")
    definition, failures = Record.parse(root / "reference/types/Transcript.md", root)
    if definition is None:
        raise ValueError(f"cannot read Transcript Type: {failures[0].message}")
    declarations = parse_directories(definition.frontmatter.get("directories"))
    if "campaign" not in declarations:
        raise ValueError("Transcript Type declares no campaign directory")
    directory = root / "campaigns" / scope / declarations["campaign"]
    for path in (directory, *directory.parents):
        if path == root:
            break
        if not path.is_dir() or path.is_symlink():
            raise ValueError(f"{path} must be an existing real directory")
    destination = directory / f"{resolved.stem} Transcript.md"
    if any(
        path.name.casefold() == destination.name.casefold()
        for path in directory.iterdir()
    ):
        raise FileExistsError(f"record already exists: {destination}")
    template_path = root / "reference/templates/Transcript.md"
    if any(
        path.is_symlink()
        for path in (template_path, template_path.parent, root / "reference")
    ):
        raise ValueError("Transcript template must be a regular file in the vault")
    template, failures = Record.parse(template_path, root)
    if template is None:
        raise ValueError(f"cannot read Transcript template: {failures[0].message}")
    if template.frontmatter.type != "Transcript":
        raise ValueError("Transcript template must declare the Transcript type")
    try:
        body = body_file.expanduser().read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise ValueError(f"body file must contain UTF-8 Markdown: {body_file}") from exc
    metadata = dict(template.frontmatter)
    metadata["session"] = f"[[{resolved.relative_to(root).with_suffix('').as_posix()}]]"
    candidate = Record(destination, Frontmatter(metadata), Body(body, 1))
    schema, diagnostics = select_schema(candidate, root)
    if schema is not None:
        diagnostics.extend(schema.validate(candidate))
    diagnostics.extend(validate_transcript(candidate, index).diagnostics)
    if any(diagnostic.severity == "error" for diagnostic in diagnostics):
        for diagnostic in diagnostics:
            diagnostic.report()
        raise ValueError(
            "generated Transcript failed input validation; no record created"
        )
    text = (
        "---\n"
        + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
        + "---\n"
        + body
    )
    logger.info("Adding new Transcript record at %s", destination)
    stream = destination.open("x", encoding="utf-8")
    try:
        with stream:
            stream.write(text)
        result = validate(destination, root)
        if result.failed:
            for diagnostic in result.diagnostics:
                diagnostic.report()
            raise ValueError(
                "generated Transcript record failed validation; no record created"
            )
    except BaseException:
        destination.unlink()
        raise
    return destination
