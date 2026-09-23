"""Read-only entry points coordinating parsing and record validation."""

from pathlib import Path

from armarium.index import VaultIndex
from armarium.lib import (
    Diagnostic,
    Result,
    VaultNotFoundError,
    check_vault,
    find_children,
    find_files,
    find_vault,
    iter_wikilinks,
)
from armarium.parse import Note
from armarium.schemas import select_schema


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
    """Check links in frontmatter strings and every Markdown body line.

    Walk nested metadata here so link errors retain their field/list locations.
    Body lines are scanned as written, including inline and fenced code.

    Args:
        note: Selected note inside the indexed vault.
        index: Whole-vault file index and lazy note cache for this run.

    Returns:
        list[Diagnostic]: Findings attributed to the selected note, with metadata
            fields or body source lines. Unrelated notes are not parsed. Heading
            and block existence, query execution and ordinary URLs are excluded.
    """
    path = note.path.relative_to(index.root).as_posix()
    # Pop metadata first, then body lines in source order. Reverse children when
    # adding them to the stack so nested mappings and lists retain their order.
    pending: list[tuple[str, int, object]] = [
        ("", number, text)
        for number, text in reversed(
            list(enumerate(note.body.splitlines(), note.body_start_line))
        )
    ]
    pending.append(("", 0, note.frontmatter))
    diagnostics: list[Diagnostic] = []
    while pending:
        field, line, value = pending.pop()
        if isinstance(value, dict):
            pending.extend(
                (f"{field}.{key}" if field else key, 0, item)
                for key, item in reversed(value.items())
            )
            continue
        if isinstance(value, list):
            pending.extend(
                (f"{field}.{number}", 0, value[number])
                for number in reversed(range(len(value)))
            )
            continue
        if not isinstance(value, str):
            continue
        for target in iter_wikilinks(value):
            if isinstance(target, ValueError):
                diagnostics.append(
                    Diagnostic(path, "link.syntax", str(target), field, line)
                )
                continue
            problem = validate_wikilink(target, note.path, index)
            if problem is not None:
                diagnostics.append(Diagnostic(path, *problem, field, line))
    return diagnostics


def validate_wikilink(
    target: str, source: Path, index: VaultIndex
) -> tuple[str, str] | None:
    """Check that one wikilink target resolves to a usable vault file.

    Args:
        target: Parsed wikilink target, without alias, heading or block suffix.
        source: Note containing the link, used to break resolution ties.
        index: Whole-vault file index and lazy note cache for this run.

    Returns:
        tuple[str, str] | None: Rule and message for a missing, ambiguous or
            unparseable target; None when the target is usable. Only a linked
            Markdown note is parsed.
    """
    resolved, rule = index.resolve(target, source)
    if rule:
        return rule, f"cannot uniquely resolve [[{target}]]; use a vault-relative path"
    if resolved is not None and resolved.suffix.lower() == ".md":
        _, failures = index.parse(resolved)
        if failures:
            relative = resolved.relative_to(index.root)
            return "link.malformed", f"referenced note {relative} cannot be parsed"
    return None
