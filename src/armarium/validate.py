"""Read-only entry points coordinating parsing and record validation."""

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

from armarium.lib import Diagnostic, Result, find_files, find_vault
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
    if vault is not None:
        vault = find_vault(path, vault)
    files = [file for file in find_files(path) if file.suffix.lower() == ".md"]
    root = path.resolve()
    results = list(
        _validate_files(files, vault, root)
        if vault is not None
        else _validate_tree(path, files, root)
    )
    return Result(
        diagnostics=sorted(d for result in results for d in result.diagnostics),
        checked=sum(result.checked for result in results),
        skipped=sum(result.skipped for result in results),
        unsupported=sum(result.unsupported for result in results),
    )


def _validate_tree(path: Path, files: list[Path], root: Path) -> Iterator[Result]:
    """Descend through directories until a vault can be selected.

    Args:
        path: Directory at the current discovery step.
        files: Visible Markdown descendants already collected by find_files.
        root: Resolved scan root used to label diagnostics consistently.

    Yields:
        Result: File validation results, or context errors for files encountered
            before a vault is found. Once selected, a vault applies to all its
            descendants, including any nested vault directories.
    """
    if not files:
        return
    try:
        vault = find_vault(path)
    except ValueError as exc:
        # Group the existing file list instead of walking the filesystem again.
        children: dict[Path, list[Path]] = {}
        for file in files:
            if file.parent == path:
                yield Result(
                    diagnostics=[
                        Diagnostic(
                            file.resolve().relative_to(root).as_posix(),
                            "vault.context",
                            str(exc),
                        )
                    ],
                    checked=1,
                )
            else:
                child = path / file.relative_to(path).parts[0]
                children.setdefault(child, []).append(file)
        for child, descendants in sorted(children.items()):
            yield from _validate_tree(child, descendants, root)
    else:
        yield from _validate_files(files, vault, root)


def _validate_files(files: list[Path], vault: Path, root: Path) -> Iterator[Result]:
    """Validate files within one explicitly selected vault.

    Args:
        files: Markdown files to validate in their supplied order.
        vault: Resolved vault root, passed explicitly to validate_markdown.
        root: Resolved scan root used to label diagnostics consistently.

    Yields:
        Result: Each file's findings and counts, with paths relative to root.
            Per-file containment checks remain active.
    """
    for file in files:
        result = validate_markdown(file, vault)
        yield replace(
            result,
            diagnostics=[
                replace(d, path=(vault / d.path).relative_to(root).as_posix())
                for d in result.diagnostics
            ],
        )
