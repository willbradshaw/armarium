"""Read-only entry points coordinating parsing and record validation."""

import re
from collections.abc import Callable
from pathlib import Path

from armarium.index import VaultIndex
from armarium.lib import (
    Diagnostic,
    Result,
    VaultNotFoundError,
    check_vault,
    find_campaign,
    find_children,
    find_files,
    find_vault,
)
from armarium.parse import Note
from armarium.schemas import select_schema

# Top-level frontmatter fields whose links must target a record of a given type,
# on every record and on records of particular types.
LINK_TYPES = {"type": "Type", "status": "Status"}
RECORD_LINK_TYPES = {"Status": {"applies_to": "Type"}}


def validate(path: Path, vault: Path | None = None) -> Result:
    """Validate a Markdown file or directory using the appropriate checks.

    Args:
        path: File or directory to validate.
        vault: Optional explicit vault boundary, passed to the selected validator.

    Returns:
        Result: Findings and counts from file or recursive directory validation.

    Raises:
        ValueError: The target or explicit vault is invalid, or a file has no
            inferable vault context.
        OSError: Directory traversal fails.
    """
    if path.is_dir():
        return validate_directory(path, vault)
    return validate_markdown(path, vault)


def validate_markdown(
    path: Path, vault: Path | None = None, *, index: VaultIndex | None = None
) -> Result:
    """Parse and schema-validate one supplied Markdown file.

    Args:
        path: Existing Markdown file, absolute or relative to the working
            directory. Direct symlink targets are excluded.
        vault: Optional explicit vault boundary; otherwise infer the nearest
            enclosing vault from its structural markers.
        index: Optional index for this vault, shared during directory validation.

    Returns:
        Result: Diagnostics and checked/skipped/unsupported counts for this
            file. Parse failures and missing or malformed types are errors.
            After parsing, only files under reference/templates are skipped,
            with an explicit informational diagnostic. Type/status definitions
            are records too and require declared types and schema validation.
            Typed files receive their vault-local schema checks;
            absent schemas produce errors. Invalid schemas
            fail validation without being counted as missing coverage.
            Links are checked against the whole vault; only linked Markdown
            dependencies are parsed. No source files are modified.

    Raises:
        ValueError: The target is not a regular Markdown file, is a symlink,
            lies outside the selected vault or has no inferable vault.
    """
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".md":
        raise ValueError("target must be a regular Markdown file, not a symlink")
    root = check_vault(path, vault) if vault is not None else find_vault(path)
    path = path.resolve()
    relative = path.relative_to(root).as_posix()
    if index is not None and index.root != root:
        raise ValueError("index must belong to the selected vault")
    note, diagnostics = (
        index.parse(path) if index is not None else Note.parse(path, root)
    )
    if note is None:
        return Result(diagnostics=diagnostics, checked=1)
    if path.is_relative_to(root / "reference/templates"):
        return Result(
            diagnostics=[
                Diagnostic(
                    relative,
                    "record.template",
                    "template parsed; completed-record validation skipped",
                    severity="info",
                )
            ],
            skipped=1,
        )
    if note.parsed_type is None:
        return Result(
            diagnostics=[
                Diagnostic(
                    relative,
                    "record.type",
                    "type is required and must be a canonical wikilink",
                    field="type",
                )
            ],
            checked=1,
        )
    schema, diagnostics = select_schema(note, root)
    if schema is not None:
        diagnostics.extend(schema.validate(note))
    if index is None:
        index = VaultIndex(root)
        index.notes[path] = (note, [])
    diagnostics.extend(validate_wikilinks(note, index))
    diagnostics.extend(validate_placement(note, index))
    diagnostics.extend(validate_filename(note, index))
    return Result(
        diagnostics=sorted(diagnostics),
        checked=1,
        unsupported=int(any(d.rule == "schema.unsupported" for d in diagnostics)),
    )


def validate_directory(path: Path, vault: Path | None = None) -> Result:
    """Validate visible Markdown descendants, discovering vaults as needed.

    Args:
        path: Directory to scan recursively. Hidden entries, caches,
            node_modules and symlinks are excluded by find_files.
        vault: Optional explicit vault containing the entire selected directory.
            Otherwise try the selected directory, then descend until a vault
            is found. A selected vault applies to its entire subtree.

    Returns:
        Result: Aggregated findings and counts, with diagnostic paths relative
            to the scanned directory. Markdown outside discovered vaults is
            ignored. Empty directories succeed with zero counts. Templates
            receive the same parse-only handling as single-file validation.

    Raises:
        ValueError: The target is not a real directory, or the explicit vault
            does not contain it.
        OSError: Directory traversal fails. The scan does not claim completeness
            when part of the directory cannot be read.
    """
    if path.is_symlink() or not path.is_dir():
        raise ValueError("directory validation requires a real directory")
    try:
        context = check_vault(path, vault) if vault is not None else find_vault(path)
    except VaultNotFoundError:
        results = [
            validate_directory(child).add_context(child.name)
            for child in find_children(path)
            if child.is_dir()
        ]
        return sum(results, Result())
    files = [file for file in find_files(path) if file.suffix.lower() == ".md"]
    index = VaultIndex(context)
    result = sum(
        (validate_markdown(file, context, index=index) for file in files), Result()
    )
    return result.add_context(context, relative_to=path.resolve())


def validate_wikilinks(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Check every link the note contains against the vault.

    Links anywhere within a type-bound top-level field must target a correctly
    placed record of that field's type.

    Args:
        note: Selected note inside the indexed vault.
        index: Whole-vault file index and lazy note cache for this run.

    Returns:
        list[Diagnostic]: Findings attributed to the selected note, with metadata
            locations or body source lines. Unrelated notes are not parsed.
            Heading and block existence, query execution and ordinary URLs are
            excluded.
    """
    path = note.path.relative_to(index.root).as_posix()
    types = LINK_TYPES | RECORD_LINK_TYPES.get(note.parsed_type or "", {})
    diagnostics: list[Diagnostic] = []
    for link in note.links:
        if link.error is not None:
            problem: tuple[str, str] | None = ("link.syntax", link.error)
        else:
            problem = validate_wikilink(link.target, note, index, types.get(link.field))
        if problem is not None:
            diagnostics.append(Diagnostic(path, *problem, link.location, link.line))
    return diagnostics


def validate_wikilink(
    target: str, note: Note, index: VaultIndex, record_type: str | None = None
) -> tuple[str, str] | None:
    """Check that one wikilink target resolves to a usable vault file.

    Args:
        target: Parsed wikilink target, without alias, heading or block suffix.
        note: Note containing the link; its path breaks resolution ties and its
            declared type takes part in target-specific checks.
        index: Whole-vault file index and lazy note cache for this run.
        record_type: Required declared type of the target, or None for any file.

    Returns:
        tuple[str, str] | None: Rule and message for a missing, ambiguous or
            unparseable target, one that is not a correctly placed record of the
            required type, or one failing that type's own check; None when the
            target is usable. Only a linked Markdown note is parsed.
    """
    resolved, rule = index.resolve(target, note.path)
    if rule:
        return rule, f"cannot uniquely resolve [[{target}]]; use a vault-relative path"
    linked = None
    if resolved is not None and resolved.suffix.lower() == ".md":
        linked, failures = index.parse(resolved)
        if failures:
            relative = resolved.relative_to(index.root)
            return "link.malformed", f"referenced note {relative} cannot be parsed"
    if record_type is None:
        return None
    if (
        linked is None
        or linked.parsed_type != record_type
        or validate_placement(linked, index)
    ):
        return "link.type", f"[[{target}]] must link to a placed {record_type} record"
    check = _TARGET_CHECKS.get(record_type)
    return check(linked, note, index) if check else None


def _validate_wikilink_status(
    status: Note, note: Note, index: VaultIndex
) -> tuple[str, str] | None:
    """Check that a linked Status applies to the linking record's type.

    Args:
        status: Correctly placed Status definition the link resolved to.
        note: Record containing the link.
        index: Whole-vault index used to resolve applies_to and the record type.

    Returns:
        tuple[str, str] | None: An applicability error when the Status's
            applies_to and the record's type resolve to different files.
    """
    if _resolve_field(status, "applies_to", index) == _resolve_field(
        note, "type", index
    ):
        return None
    return (
        "status.applicability",
        f"status does not apply to {note.parsed_type} records",
    )


# Extra checks on a typed link target, keyed by the target's declared type.
_TARGET_CHECKS: dict[
    str, Callable[[Note, Note, VaultIndex], tuple[str, str] | None]
] = {"Status": _validate_wikilink_status}


def validate_placement(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Check the record's directory against its declared type.

    Args:
        note: Selected record; templates are excluded by the caller.
        index: Index supplying the selected vault boundary.

    Returns:
        list[Diagnostic]: A placement error for a misplaced built-in type.
            Unknown custom types and Reference records have no placement rule.
    """
    kind = note.parsed_type
    directories = {
        "Content": "content",
        "Session": "sessions",
        "Clue": "clues",
        "Transcript": "sessions/transcripts",
        "Player": "reference/players",
        "Type": "reference/types",
        "Status": "reference/statuses",
    }
    if kind not in directories:
        return []
    scope = find_campaign(note.path, index.root)
    prefix = index.root
    if scope and kind not in {"Type", "Status"}:
        prefix /= f"campaigns/{scope}"
    expected = prefix / directories[kind]
    valid = note.path.is_relative_to(expected)
    if kind in {"Session", "Clue", "Transcript", "Player"} and not scope:
        valid = False
    # The Transcript subtree is reserved for transcripts, not Session records.
    if kind == "Session" and note.path.is_relative_to(expected / "transcripts"):
        valid = False
    if valid:
        return []
    return [
        Diagnostic(
            note.path.relative_to(index.root).as_posix(),
            "record.placement",
            f"{kind} belongs under {expected.relative_to(index.root)}"
            + (
                " inside a numeric campaign"
                if scope is None and kind not in {"Content", "Type", "Status"}
                else ""
            ),
        )
    ]


def validate_filename(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Check campaign record filenames and the Session ordinal they encode.

    Args:
        note: Selected record; templates are excluded by the caller.
        index: Index supplying the selected vault boundary.

    Returns:
        list[Diagnostic]: A Session, Clue or Transcript filename that does not
            match its campaign's pattern, or a Session whose session_number
            differs from its filename. Other types and records outside numeric
            campaigns have no filename rule.
    """
    scope = find_campaign(note.path, index.root)
    kind = note.parsed_type
    if scope is None or kind not in {"Session", "Clue", "Transcript"}:
        return []
    path = note.path.relative_to(index.root).as_posix()
    number = scope.removeprefix("campaign_")
    pattern = {
        "Clue": rf"C-{number}-[0-9]{{4}}",
        "Session": rf"S-{number}-([0-9]{{3}})",
        "Transcript": rf"S-{number}-[0-9]{{3}} Transcript",
    }[kind]
    match = re.fullmatch(pattern, note.path.stem)
    if match is None:
        return [
            Diagnostic(path, "record.identity", f"{kind} filename must match {pattern}")
        ]
    ordinal = note.frontmatter.get("session_number")
    # bool is an int subclass, so compare the exact type.
    if kind == "Session" and (type(ordinal) is not int or ordinal != int(match[1])):
        return [
            Diagnostic(
                path,
                "record.identity",
                "session_number must match filename ordinal",
                "session_number",
            )
        ]
    return []


def _resolve_field(note: Note, field: str, index: VaultIndex) -> Path | None:
    """Resolve the link held directly by one top-level frontmatter field.

    Args:
        note: Note containing the field.
        field: Top-level frontmatter field name.
        index: Whole-vault index used for resolution.

    Returns:
        Path | None: The unique file named by the field's first well-formed
            link, or None when the field holds no such link or the link does
            not resolve uniquely.
    """
    for link in note.links:
        if link.location == field and link.error is None:
            return index.resolve(link.target, note.path)[0]
    return None
