"""Whole-vault structure and shared reference infrastructure checks."""

import re
from pathlib import Path

from jsonschema.exceptions import SchemaError
from referencing.exceptions import NoSuchResource, Unresolvable

from armarium.index import VaultIndex
from armarium.lib import Diagnostic
from armarium.markdown import links
from armarium.schemas import Schemas

ROOT_DIRS = (
    "content",
    "assets",
    "campaigns",
    "reference/types",
    "reference/templates",
    "reference/statuses",
    "reference/schemas",
)
CAMPAIGN_DIRS = (
    "content",
    "clues",
    "sessions",
    "sessions/transcripts",
    "reference/players",
    "reference/indexes",
)
TYPES = ("Content", "Clue", "Session", "Transcript", "Player", "Reference")
STATUSES = ("Pending", "Hinted", "Revealed", "Abandoned", "Dormant", "Superseded")


def check(root: Path, index: VaultIndex) -> list[Diagnostic]:
    """Require current infrastructure while allowing arbitrary extra folders."""
    diagnostics: list[Diagnostic] = []

    def required(relative: str, directory: bool = False) -> None:
        path = root / relative
        exists = path.is_dir() if directory else path.is_file()
        if not exists or path.is_symlink():
            diagnostics.append(
                Diagnostic(
                    relative,
                    "vault.required",
                    "required directory is missing"
                    if directory
                    else "required reference file is missing",
                )
            )

    for relative in ROOT_DIRS:
        required(relative, directory=True)
    for kind in TYPES:
        required(f"reference/types/{kind}.md")
        if kind != "Reference":
            required(f"reference/templates/{kind}.md")
    for status in STATUSES:
        required(f"reference/statuses/{status}.md")
    for kind in TYPES:
        if kind == "Reference":
            continue
        path = root / "reference/templates" / f"{kind}.md"
        if path.is_file():
            note, _ = index.note(path)
            if note and note.kind != kind:
                diagnostics.append(
                    Diagnostic(
                        path.relative_to(root).as_posix(),
                        "vault.template",
                        f"template must declare {kind} type",
                    )
                )
    for status in STATUSES:
        path = root / "reference/statuses" / f"{status}.md"
        if path.is_file():
            note, _ = index.note(path)
            if note:
                value = note.frontmatter.get("applies_to")
                targets = links(value) if isinstance(value, str) else []
                target, _ = (
                    index.resolve(targets[0], path)
                    if len(targets) == 1
                    else (None, None)
                )
                if target != root / "reference/types/Clue.md":
                    diagnostics.append(
                        Diagnostic(
                            path.relative_to(root).as_posix(),
                            "vault.status",
                            "shipped Clue status must apply to types/Clue",
                            field="applies_to",
                        )
                    )
    required("reference/schemas/content.schema.json")
    campaigns = root / "campaigns"
    children = sorted(campaigns.iterdir()) if campaigns.is_dir() else []
    recognized = [
        p
        for p in children
        if p.is_dir() and not p.is_symlink() and re.fullmatch(r"campaign_\d+", p.name)
    ]
    if not recognized:
        diagnostics.append(
            Diagnostic(
                "campaigns",
                "vault.campaigns",
                "at least one campaign_N directory is required",
            )
        )
    for path in recognized:
        for relative in CAMPAIGN_DIRS:
            required(f"campaigns/{path.name}/{relative}", directory=True)
        required(f"campaigns/{path.name}/reference/Campaign.md")
        required(f"campaigns/{path.name}/reference/indexes/Clues.md")
    schemas = Schemas(root)
    for path in sorted(schemas.directory.glob("*.json")):
        try:
            schemas.registry(path)
        except (
            OSError,
            ValueError,
            SchemaError,
            Unresolvable,
            NoSuchResource,
            RecursionError,
        ) as exc:
            diagnostics.append(
                Diagnostic(
                    path.relative_to(root).as_posix(), "schema.invalid", str(exc)
                )
            )
    return diagnostics


def shipped_vaults(repository: Path) -> list[Path]:
    """Discover every direct vaults/ child independently, including damaged vaults."""
    return sorted(
        path
        for path in (repository / "vaults").iterdir()
        if path.is_dir() and not path.name.startswith(".") and not path.is_symlink()
    )
