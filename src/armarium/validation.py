"""Read-only validation orchestration; rules return structured diagnostics."""

from pathlib import Path

from armarium.discovery import find_vault
from armarium.lib import Diagnostic, Result
from armarium.parse import parse
from armarium.schemas import Schemas


def validate(path: Path, vault: Path | None = None) -> Result:
    """Validate one Markdown file using its selected vault's schemas."""
    path = path.resolve()
    root = find_vault(path, vault)
    if not path.is_file() or path.suffix.lower() != ".md":
        raise ValueError("target must be a Markdown file")
    result = Result()
    note, errors = parse(path, root)
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
    result.diagnostics.sort()
    return result
