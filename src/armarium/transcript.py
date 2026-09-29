"""Create Transcript records from existing Sessions and supplied Markdown."""

from pathlib import Path

from armarium.creation import (
    check_destination,
    read_template,
    record_directory,
    record_text,
    select_vault,
    write_record,
)
from armarium.index import VaultIndex
from armarium.lib import find_campaign, parse_wikilink
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
    root = select_vault(vault)
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
    directory = record_directory(root, "Transcript", scope)
    destination = directory / f"{resolved.stem} Transcript.md"
    check_destination(destination)
    template = read_template(root, "Transcript", check_reference=True)
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
    text = record_text(metadata, body)
    return write_record(destination, text, root, "Transcript")
