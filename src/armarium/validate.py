"""Read-only entry points coordinating parsing and record validation."""

from dataclasses import replace
from pathlib import Path

from armarium.lib import (
    Diagnostic,
    Result,
    VaultNotFoundError,
    find_children,
    find_files,
    find_vault,
)
from armarium.parse import Note
from armarium.schemas import select_schema


def validate_markdown(path: Path, vault: Path | None = None) -> Result:
    """Parse and schema-validate one supplied Markdown file.

    Args:
        path: Existing Markdown file, absolute or relative to the working
            directory. Direct symlink targets are excluded.
        vault: Optional explicit vault boundary; otherwise infer the nearest
            enclosing vault from its structural markers.

    Returns:
        Result: Diagnostics and checked/skipped/unsupported counts for this
            file. Parse failures and missing or malformed types are errors.
            After parsing, only files under reference/templates are skipped,
            with an explicit informational diagnostic. Type/status definitions
            are records too and require declared types and schema validation.
            Typed files receive their vault-local schema checks;
            absent schemas produce partial-coverage warnings. Invalid schemas
            fail validation without being counted as missing coverage.
            No source files are modified and no other records are checked.

    Raises:
        ValueError: The target is not a regular Markdown file, is a symlink,
            lies outside the selected vault or has no inferable vault.
    """
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".md":
        raise ValueError("target must be a regular Markdown file, not a symlink")
    root = find_vault(path, vault)
    path = path.resolve()
    relative = path.relative_to(root).as_posix()
    note, diagnostics = Note.parse(path, root)
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
            to the scanned directory. Files without inferable vault context
            are errors. Empty directories succeed with zero counts. Templates
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
        context = find_vault(path, vault) if vault is not None else find_vault(path)
    except VaultNotFoundError as exc:
        return _validate_unscoped_directory(path, str(exc))
    return _validate_directory_files(path, context)


def _validate_unscoped_directory(path: Path, message: str) -> Result:
    """Recurse into child directories and report unscoped Markdown files.

    Args:
        path: Directory for which vault discovery failed.
        message: Explanation of the failed vault discovery.

    Returns:
        Result: Combined child results with paths relative to this directory.
            Direct Markdown children receive context errors, not exemptions.
    """
    result = Result()
    for child in find_children(path):
        if child.is_dir():
            checked = validate_directory(child)
            checked = replace(
                checked,
                diagnostics=[
                    replace(d, path=(Path(child.name) / d.path).as_posix())
                    for d in checked.diagnostics
                ],
            )
            result += checked
        elif child.is_file() and child.suffix.lower() == ".md":
            result += Result(
                diagnostics=[Diagnostic(child.name, "vault.context", message)],
                checked=1,
            )
    return result


def _validate_directory_files(path: Path, vault: Path) -> Result:
    """Collect and validate Markdown files with an explicit vault context.

    Args:
        path: Directory whose visible Markdown descendants should be checked.
        vault: Resolved vault root, passed explicitly to validate_markdown.

    Returns:
        Result: Summed file results with diagnostic paths relative to path.
            Per-file containment checks remain active.
    """
    files = [file for file in find_files(path) if file.suffix.lower() == ".md"]
    result = sum((validate_markdown(file, vault) for file in files), Result())
    return replace(
        result,
        diagnostics=[
            replace(d, path=(vault / d.path).relative_to(path.resolve()).as_posix())
            for d in result.diagnostics
        ],
    )
