"""Vault-local schema loading and validation, grouped by public method."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from jsonschema.exceptions import SchemaError
from referencing.exceptions import NoSuchResource

from armarium.parse import Note
from armarium.schemas import Schemas


@pytest.fixture
def schemas(tmp_path: Path) -> Schemas:
    root = tmp_path / "vault with spaces"
    directory = root / "reference/schemas"
    directory.mkdir(parents=True)
    return Schemas(root)


@pytest.fixture
def write_schema(schemas: Schemas) -> Callable[..., Path]:
    def write(data: Any, name: str = "widget.schema.json") -> Path:
        path = schemas.directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    return write


@pytest.fixture
def note(schemas: Schemas) -> Note:
    return Note(
        schemas.root / "content/Example.md",
        {"type": "[[types/Widget]]", "name": "Example"},
        "## Notes\n",
        5,
    )


class TestSchemas:
    @pytest.mark.parametrize("relative", [False, True], ids=["absolute", "relative"])
    def test_vault_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: bool
    ) -> None:
        monkeypatch.chdir(tmp_path)
        root = Path("vault") if relative else tmp_path / "vault"
        schemas = Schemas(root)
        assert schemas.root == tmp_path / "vault"
        assert schemas.directory == tmp_path / "vault/reference/schemas"
        assert not schemas.root.exists()


class TestSchemasRead:
    @pytest.mark.parametrize(
        "schema",
        [
            True,
            False,
            {},
            {"type": "object"},
            {"$schema": "https://json-schema.org/draft/2020-12/schema"},
        ],
    )
    def test_valid_schema(
        self, schemas: Schemas, write_schema: Callable[..., Path], schema: Any
    ) -> None:
        path = write_schema(schema)
        before = path.read_bytes()
        assert schemas.read(path) == schema
        assert path.read_bytes() == before

    @pytest.mark.parametrize(
        ("contents", "exception"),
        [
            (b"{", ValueError),
            (b"\xff", UnicodeError),
            (b'{"type": 12}', SchemaError),
            (b'{"$schema": "http://json-schema.org/draft-07/schema#"}', ValueError),
        ],
    )
    def test_invalid_schema(
        self, schemas: Schemas, contents: bytes, exception: type[Exception]
    ) -> None:
        path = schemas.directory / "broken.json"
        path.write_bytes(contents)
        with pytest.raises(exception):
            schemas.read(path)
        assert path.read_bytes() == contents

    @pytest.mark.parametrize("escape", ["parent", "file-symlink", "directory-symlink"])
    def test_confined_paths(
        self, schemas: Schemas, tmp_path: Path, escape: str
    ) -> None:
        outside = tmp_path / "outside.json"
        outside.write_text("{}")
        if escape == "parent":
            path = outside
        elif escape == "file-symlink":
            path = schemas.directory / "outside.json"
            path.symlink_to(outside)
        else:
            schemas.directory.rmdir()
            schemas.directory.symlink_to(tmp_path, target_is_directory=True)
            path = schemas.directory / "outside.json"
        with pytest.raises(ValueError, match="escapes reference/schemas"):
            schemas.read(path)

    def test_missing_file(self, schemas: Schemas) -> None:
        with pytest.raises(FileNotFoundError):
            schemas.read(schemas.directory / "missing.json")


class TestSchemasRetrieve:
    @pytest.mark.parametrize("name", ["helper.json", "nested dir/Café.json"])
    def test_local_uri(
        self, schemas: Schemas, write_schema: Callable[..., Path], name: str
    ) -> None:
        path = write_schema({"type": "string"}, name)
        assert schemas.retrieve(path.as_uri()).contents == {"type": "string"}

    @pytest.mark.parametrize(
        "uri",
        [
            "https://example.invalid/schema",
            "http://localhost/schema",
            "file://host/schema",
            "relative.json",
            "urn:example:schema",
        ],
    )
    def test_refuses_nonlocal_uri(self, schemas: Schemas, uri: str) -> None:
        with pytest.raises(NoSuchResource):
            schemas.retrieve(uri)

    def test_refuses_file_outside_vault(self, schemas: Schemas, tmp_path: Path) -> None:
        path = tmp_path / "outside.json"
        path.write_text("{}")
        with pytest.raises(ValueError, match="escapes"):
            schemas.retrieve(path.as_uri())


class TestSchemasValidate:
    @pytest.mark.parametrize(
        "schema", [True, {}, {"required": ["frontmatter", "body"]}]
    )
    def test_valid_note(
        self,
        schemas: Schemas,
        write_schema: Callable[..., Path],
        note: Note,
        schema: Any,
    ) -> None:
        path = write_schema(schema)
        before = path.read_bytes()
        assert schemas.validate(note) == (True, [])
        assert path.read_bytes() == before
        assert note.frontmatter == {"type": "[[types/Widget]]", "name": "Example"}
        assert note.body == "## Notes\n"

    @pytest.mark.parametrize(
        ("schema", "field"),
        [
            (False, ""),
            ({"properties": {"body": {"const": "Other"}}}, "body"),
            (
                {
                    "properties": {
                        "frontmatter": {"properties": {"name": {"type": "integer"}}}
                    }
                },
                "frontmatter.name",
            ),
            ({"properties": {"frontmatter": {"required": ["missing"]}}}, "frontmatter"),
            (
                {
                    "properties": {
                        "frontmatter": {"properties": {"name": {"format": "uri"}}}
                    }
                },
                "frontmatter.name",
            ),
        ],
    )
    def test_instance_errors(
        self,
        schemas: Schemas,
        write_schema: Callable[..., Path],
        note: Note,
        schema: Any,
        field: str,
    ) -> None:
        write_schema(schema)
        covered, diagnostics = schemas.validate(note)
        assert covered and len(diagnostics) == 1
        error = diagnostics[0]
        assert (error.path, error.rule, error.field, error.severity) == (
            "content/Example.md",
            "schema.instance",
            field,
            "error",
        )
        assert error.message

    def test_deterministic_field_order(
        self, schemas: Schemas, write_schema: Callable[..., Path], note: Note
    ) -> None:
        write_schema(
            {
                "properties": {
                    "frontmatter": {"type": "array"},
                    "body": {"type": "integer"},
                }
            }
        )
        assert [d.field for d in schemas.validate(note)[1]] == ["body", "frontmatter"]

    def test_missing_schema_has_partial_coverage(
        self, schemas: Schemas, note: Note
    ) -> None:
        covered, diagnostics = schemas.validate(note)
        assert not covered and len(diagnostics) == 1
        warning = diagnostics[0]
        assert (warning.rule, warning.severity) == ("schema.unsupported", "warning")
        assert "Widget" in warning.message

    @pytest.mark.parametrize(
        "schema",
        [
            {"type": 12},
            {"$schema": "http://json-schema.org/draft-07/schema#"},
            {"$ref": "missing.json"},
            {"$ref": "https://example.invalid/schema.json"},
            {"$ref": "#/$defs/missing"},
            {"$ref": "widget.schema.json"},
        ],
    )
    def test_schema_errors(
        self,
        schemas: Schemas,
        write_schema: Callable[..., Path],
        note: Note,
        schema: Any,
    ) -> None:
        write_schema(schema)
        covered, diagnostics = schemas.validate(note)
        assert covered and len(diagnostics) == 1
        assert diagnostics[0].rule == "schema.invalid"
        assert diagnostics[0].message

    @pytest.mark.parametrize("contents", [b"{", b"\xff"])
    def test_unreadable_schema(
        self, schemas: Schemas, note: Note, contents: bytes
    ) -> None:
        (schemas.directory / "widget.schema.json").write_bytes(contents)
        assert schemas.validate(note)[1][0].rule == "schema.invalid"

    @pytest.mark.parametrize("external", [False, True], ids=["fragment", "file"])
    @pytest.mark.parametrize("valid", [False, True])
    def test_references(
        self,
        schemas: Schemas,
        write_schema: Callable[..., Path],
        note: Note,
        external: bool,
        valid: bool,
    ) -> None:
        target = {"properties": {"body": {"const": note.body if valid else "Other"}}}
        if external:
            write_schema(target, "nested dir/helper.json")
            schema = {"$ref": "nested%20dir/helper.json"}
        else:
            schema = {"$defs": {"target": target}, "$ref": "#/$defs/target"}
        write_schema(schema)
        covered, diagnostics = schemas.validate(note)
        assert covered
        assert [d.rule for d in diagnostics] == ([] if valid else ["schema.instance"])

    def test_relative_reference_chain(
        self, schemas: Schemas, write_schema: Callable[..., Path], note: Note
    ) -> None:
        write_schema({"$ref": "nested/first.json"})
        write_schema({"$ref": "second.json"}, "nested/first.json")
        write_schema({"required": ["body"]}, "nested/second.json")
        assert schemas.validate(note) == (True, [])

    @pytest.mark.parametrize("escape", ["reference", "schema-symlink"])
    def test_escaping_schema(
        self,
        schemas: Schemas,
        write_schema: Callable[..., Path],
        note: Note,
        tmp_path: Path,
        escape: str,
    ) -> None:
        outside = tmp_path / "outside.json"
        outside.write_text("{}")
        if escape == "reference":
            write_schema({"$ref": outside.as_uri()})
        else:
            (schemas.directory / "widget.schema.json").symlink_to(outside)
        assert schemas.validate(note)[1][0].rule == "schema.invalid"

    @pytest.mark.parametrize("problem", ["missing-type", "outside-vault"])
    def test_caller_errors(
        self, schemas: Schemas, note: Note, tmp_path: Path, problem: str
    ) -> None:
        invalid = Note(
            tmp_path / "outside.md" if problem == "outside-vault" else note.path,
            {} if problem == "missing-type" else note.frontmatter,
            note.body,
            1,
        )
        with pytest.raises(ValueError):
            schemas.validate(invalid)

    def test_relative_vault_and_note_paths(
        self,
        schemas: Schemas,
        write_schema: Callable[..., Path],
        note: Note,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        write_schema(True)
        monkeypatch.chdir(schemas.root.parent)
        relative = Note(
            note.path.relative_to(schemas.root.parent), note.frontmatter, note.body, 1
        )
        assert Schemas(Path(schemas.root.name)).validate(relative) == (True, [])

    def test_uses_only_selected_vault(
        self,
        schemas: Schemas,
        write_schema: Callable[..., Path],
        note: Note,
        tmp_path: Path,
    ) -> None:
        write_schema(False)
        other = Schemas(tmp_path / "other")
        other.directory.mkdir(parents=True)
        (other.directory / "widget.schema.json").write_text("true")
        other_note = Note(other.root / "note.md", note.frontmatter, note.body, 1)
        assert other.validate(other_note) == (True, [])
        assert schemas.validate(note)[1][0].rule == "schema.instance"

    @pytest.mark.parametrize("vault", ["starter", "example"])
    @pytest.mark.parametrize(
        "kind", ["content", "clue", "session", "transcript", "player", "reference"]
    )
    def test_shipped_schema_contract(self, vault: str, kind: str) -> None:
        fixture = json.loads(Path(f"tests/schemas/fixtures/{kind}.json").read_text())[
            "base"
        ]
        root = Path(f"vaults/{vault}")
        note = Note(root / "record.md", fixture["frontmatter"], fixture["body"], 1)
        assert Schemas(root).validate(note) == (True, [])
