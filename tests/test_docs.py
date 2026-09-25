"""The package documentation names every enumerable fact the code enforces."""

from pathlib import Path

import pytest

from armarium.validate import (
    CAMPAIGN_DIRECTORIES,
    CAMPAIGN_FILES,
    VAULT_DIRECTORIES,
    VAULT_STATUSES,
    VAULT_TEMPLATES,
    VAULT_TYPES,
)

DOCS = Path(__file__).resolve().parents[1] / "docs"


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
