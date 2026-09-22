"""Original fixtures test parsing, coverage and the vault-local schema contract."""

import json
import shutil
from pathlib import Path

import pytest

from armarium.parse import parse
from armarium.validation import validate


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault with spaces"
    shutil.copytree(Path("vaults/starter"), root)
    return root


def write(root: Path, text: str) -> Path:
    path = root / "content/Test.md"
    path.write_text(text)
    return path


VALID = (
    '---\ntype: "[[types/Content]]"\nsubtype: Lore\nsummary:\n'
    "---\n## Notes\n## Active Clues\n## Appearances\n- N/A\n"
)


def test_valid_and_readonly(vault: Path) -> None:
    path = write(vault, VALID)
    before = path.read_bytes()
    assert not validate(path).failed
    assert path.read_bytes() == before
    path.write_text(VALID.replace("subtype: Lore", "subtype: invalid"))
    before = path.read_bytes()
    assert validate(path).failed
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "yaml", ["x: [", "x: 1\nx: 2", "x: .nan", "x: &x [*x]", "? [a, b]\n: c"]
)
def test_bad_yaml(vault: Path, yaml: str) -> None:
    result = validate(write(vault, f"---\n{yaml}\n---\n"))
    assert result.failed
    assert result.diagnostics[0].rule == "parse.invalid"


def test_dates(vault: Path) -> None:
    note, errors = parse(write(vault, "---\ndate: 2026-01-02\n---\n"), vault)
    assert not errors and note is not None
    assert note.frontmatter["date"] == "2026-01-02"


def test_schema_missing_invalid_and_additional(vault: Path) -> None:
    path = write(vault, VALID)
    schema = vault / "reference/schemas/content.schema.json"
    schema.unlink()
    assert validate(path).unsupported == 1
    schema.write_text('{"type": 12}')
    assert validate(path).diagnostics[0].rule == "schema.invalid"
    schema.write_text(json.dumps({"$ref": "body.json"}))
    (schema.parent / "body.json").write_text(json.dumps({"required": ["body"]}))
    assert not validate(path).failed
    schema.write_text('{"$ref": "https://example.invalid/no.json"}')
    assert validate(path).failed
    custom = vault / "reference/schemas/widget.schema.json"
    custom.write_text('{"properties":{"frontmatter":{"required":["name"]}}}')
    path.write_text('---\ntype: "[[Widget]]"\n---\n')
    assert validate(path).failed
    path.write_text('---\ntype: "[[Widget]]"\nname: example\n---\n')
    assert not validate(path).failed


def test_templates_and_untyped(vault: Path) -> None:
    assert validate(vault / "reference/templates/Content.md").skipped == 1
    assert validate(vault / "reference/types/Content.md").skipped == 1
