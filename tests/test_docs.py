"""The package documentation names every enumerable fact the code enforces."""

import json
from pathlib import Path
from typing import Any

import pytest

from armarium.index import VaultIndex
from armarium.validate import (
    CAMPAIGN_DIRECTORIES,
    CAMPAIGN_FILES,
    LINK_TARGETS,
    RECORD_LINK_TARGETS,
    VAULT_DIRECTORIES,
    VAULT_STATUSES,
    VAULT_TEMPLATES,
    VAULT_TYPES,
)

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
STARTER = ROOT / "vaults/starter"


def schema_fields(kind: str) -> list[str]:
    """List the frontmatter fields a type's schema requires, in any branch."""
    schema = json.loads(
        (STARTER / f"reference/schemas/{kind.lower()}.schema.json").read_text()
    )
    frontmatter = schema["properties"]["frontmatter"]
    fields: list[str] = list(frontmatter.get("required", []))

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            fields.extend(node.get("then", {}).get("required", []))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(frontmatter.get("allOf", []))
    return sorted(set(fields))


class TestSchemaFields:
    @pytest.mark.parametrize(
        ("kind", "expected"),
        [
            ("Note", ["type"]),
            ("Status", ["applies_to", "type"]),
            (
                "Clue",
                [
                    "first_session",
                    "last_session",
                    "status",
                    "subjects",
                    "superseded_by",
                    "text",
                    "type",
                ],
            ),
            (
                "Content",
                [
                    "members",
                    "parent_location",
                    "player",
                    "stats",
                    "subtype",
                    "summary",
                    "type",
                ],
            ),
        ],
    )
    def test_required_in_any_branch(self, kind: str, expected: list[str]) -> None:
        assert schema_fields(kind) == expected


class TestVaultDocument:
    TEXT = (DOCS / "vault.md").read_text()

    @pytest.mark.parametrize(
        "entry",
        [
            *VAULT_DIRECTORIES,
            *CAMPAIGN_DIRECTORIES,
            *CAMPAIGN_FILES,
            *VAULT_TYPES,
            *VAULT_STATUSES,
            *VAULT_TEMPLATES,
        ],
    )
    def test_names_every_required_entry(self, entry: str) -> None:
        assert entry.rsplit("/", 1)[-1] in self.TEXT

    @pytest.mark.parametrize(
        ("kind", "declared"),
        sorted(VaultIndex(STARTER).declared_directories().items()),
    )
    def test_states_every_declaration(
        self, kind: str, declared: dict[str, str]
    ) -> None:
        inner = ", ".join(f"{scope}: {path}" for scope, path in declared.items())
        assert f"| {kind} | `{{ {inner} }}` |" in self.TEXT


class TestRecordDocument:
    TEXT = (DOCS / "record.md").read_text()

    @pytest.mark.parametrize(
        "field",
        sorted(
            set(LINK_TARGETS)
            | {field for targets in RECORD_LINK_TARGETS.values() for field in targets}
        ),
    )
    def test_names_every_typed_field(self, field: str) -> None:
        assert f"`{field}`" in self.TEXT


class TestTypeDocument:
    TEXT = (DOCS / "type.md").read_text()

    @pytest.mark.parametrize("kind", VAULT_TYPES)
    def test_has_a_section_per_type(self, kind: str) -> None:
        assert f"\n## {kind}\n" in self.TEXT

    @pytest.mark.parametrize(
        ("kind", "field"),
        [(kind, field) for kind in VAULT_TYPES for field in schema_fields(kind)],
    )
    def test_names_every_required_field(self, kind: str, field: str) -> None:
        start = self.TEXT.index(f"\n## {kind}\n")
        end = self.TEXT.find("\n## ", start + 1)
        section = self.TEXT[start : end if end > 0 else None]
        assert f"`{field}`" in section
