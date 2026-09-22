"""Read-only validation orchestration; rules return structured diagnostics."""

from pathlib import Path

from armarium.context import check
from armarium.discovery import files, find_vault
from armarium.index import VaultIndex
from armarium.infrastructure import check as check_infrastructure
from armarium.lib import Diagnostic, Result
from armarium.schemas import Schemas


def validate_file(path: Path, index: VaultIndex) -> Result:
    """Apply identical per-file rules within an already indexed vault."""
    root = index.root
    result = Result()
    note, errors = index.note(path)
    result.diagnostics.extend(errors)
    relative = path.relative_to(root).as_posix()
    if note is None:
        result.checked = 1
    elif relative.startswith("reference/templates/"):
        result.skipped = 1
        result.diagnostics.append(
            Diagnostic(
                relative,
                "record.template",
                "unfinished template; not validated as a completed record",
                severity="info",
            )
        )
    elif note.kind is None:
        if "type" in note.frontmatter:
            result.diagnostics.append(
                Diagnostic(
                    relative,
                    "record.type",
                    "type must be a canonical wikilink",
                    field="type",
                )
            )
            result.checked = 1
        else:
            result.skipped = 1
    else:
        result.checked = 1
        covered, errors = Schemas(root).validate(note)
        result.unsupported = int(not covered)
        result.diagnostics.extend(errors)
    if note is not None and not relative.startswith("reference/templates/"):
        result.diagnostics.extend(check(note, index))
    result.diagnostics.sort()
    return result


def validate(path: Path, vault: Path | None = None) -> Result:
    """Validate a file or Markdown descendants with whole-vault context."""
    if path.is_symlink():
        raise ValueError("symlink targets are excluded; select a real vault path")
    path = path.absolute()
    root = find_vault(path, vault)
    if not path.resolve().is_relative_to(root):
        raise ValueError("target escapes the selected vault")
    path = path.resolve()
    if not path.exists():
        raise ValueError("target does not exist")
    index = VaultIndex(root)
    if path.is_file():
        if path.suffix.lower() != ".md":
            raise ValueError("target must be a Markdown file or directory")
        return validate_file(path, index)
    result = Result()
    for selected in files(path):
        if selected.suffix.lower() != ".md":
            continue
        partial = validate_file(selected, index)
        result.diagnostics.extend(partial.diagnostics)
        result.checked += partial.checked
        result.skipped += partial.skipped
        result.unsupported += partial.unsupported
    if path == root:
        result.diagnostics.extend(check_infrastructure(root))
    result.diagnostics.sort()
    return result
