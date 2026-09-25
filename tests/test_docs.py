"""The package documentation names every enumerable fact the code enforces."""

from pathlib import Path

import pytest

from armarium.index import VaultIndex
from armarium.validate import (
    CAMPAIGN_DIRECTORIES,
    CAMPAIGN_FILES,
    VAULT_DIRECTORIES,
    VAULT_STATUSES,
    VAULT_TEMPLATES,
    VAULT_TYPES,
)

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
STARTER = ROOT / "vaults/starter"


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
