"""Schema loading, retrieval, validation and selection contracts."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from jsonschema.exceptions import SchemaError
from referencing.exceptions import NoSuchResource

from armarium.parse import Note
from armarium.schemas import Schema, select_schema


@pytest.fixture
def root(tmp_path: Path) -> Path:
    root = tmp_path / "vault with spaces"
    (root / "reference/schemas").mkdir(parents=True)
    return root


@pytest.fixture
def write_schema(root: Path) -> Callable[..., Path]:
    def write(data: Any, name: str = "widget.schema.json") -> Path:
        path = (root / "reference/schemas") / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    return write


@pytest.fixture
def note(root: Path) -> Note:
    return Note(
        root / "content/Example.md",
        {"type": "[[types/Widget]]", "name": "Example"},
        "## Notes\n",
        5,
    )


class TestSchema:
    def test_represents_one_schema(
        self, root: Path, write_schema: Callable[..., Path], note: Note
    ) -> None:
        path = write_schema(True)
        schema = Schema.load(path, root)
        assert schema.path == path
        assert schema.root == root
        assert schema.contents is True
        # Loading fixes the selected schema's contents for reuse across notes.
        path.write_text("false")
        assert schema.validate(note) == []


class TestSchemaLoad:
    @pytest.mark.parametrize("relative", [False, True])
    def test_absolute_paths(
        self,
        root: Path,
        write_schema: Callable[..., Path],
        monkeypatch: pytest.MonkeyPatch,
        relative: bool,
    ) -> None:
        path = write_schema(True)
        monkeypatch.chdir(root.parent)
        schema = Schema.load(
            path.relative_to(root.parent) if relative else path,
            Path(root.name) if relative else root,
        )
        assert schema.path == path and schema.root == root

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
        self, root: Path, write_schema: Callable[..., Path], schema: Any
    ) -> None:
        path = write_schema(schema)
        before = path.read_bytes()
        assert Schema.load(path, root).contents == schema
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
        self, root: Path, contents: bytes, exception: type[Exception]
    ) -> None:
        path = (root / "reference/schemas") / "broken.json"
        path.write_bytes(contents)
        with pytest.raises(exception):
            Schema.load(path, root).contents
        assert path.read_bytes() == contents

    @pytest.mark.parametrize("escape", ["parent", "file-symlink", "directory-symlink"])
    def test_confined_paths(self, root: Path, tmp_path: Path, escape: str) -> None:
        outside = tmp_path / "outside.json"
        outside.write_text("{}")
        if escape == "parent":
            path = outside
        elif escape == "file-symlink":
            path = (root / "reference/schemas") / "outside.json"
            path.symlink_to(outside)
        else:
            (root / "reference/schemas").rmdir()
            (root / "reference/schemas").symlink_to(tmp_path, target_is_directory=True)
            path = (root / "reference/schemas") / "outside.json"
        with pytest.raises(ValueError, match="escapes reference/schemas"):
            Schema.load(path, root).contents

    def test_missing_file(self, root: Path) -> None:
        with pytest.raises(FileNotFoundError):
            Schema.load(root / "reference/schemas/missing.json", root)


class TestSchemaRetrieve:
    @pytest.fixture
    def schema(self, root: Path, write_schema: Callable[..., Path]) -> Schema:
        return Schema.load(write_schema(True), root)

    @pytest.mark.parametrize("name", ["helper.json", "nested dir/Café.json"])
    def test_local_uri(
        self, schema: Schema, write_schema: Callable[..., Path], name: str
    ) -> None:
        path = write_schema({"type": "string"}, name)
        assert schema._retrieve(path.as_uri()).contents == {"type": "string"}

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
    def test_refuses_nonlocal_uri(self, schema: Schema, uri: str) -> None:
        with pytest.raises(NoSuchResource):
            schema._retrieve(uri)

    def test_refuses_file_outside_vault(self, schema: Schema, tmp_path: Path) -> None:
        path = tmp_path / "outside.json"
        path.write_text("{}")
        with pytest.raises(ValueError, match="escapes"):
            schema._retrieve(path.as_uri())


class TestSchemaValidate:
    @pytest.mark.parametrize(
        "reference",
        [
            "missing.json",
            "https://example.invalid/schema.json",
            "#/$defs/missing",
            "widget.schema.json",
        ],
    )
    def test_reference_failures(
        self, root: Path, write_schema: Callable[..., Path], note: Note, reference: str
    ) -> None:
        schema = Schema.load(write_schema({"$ref": reference}), root)
        diagnostics = schema.validate(note)
        assert len(diagnostics) == 1
        assert diagnostics[0].rule == "schema.invalid" and diagnostics[0].message

    def test_escaping_reference(
        self, root: Path, write_schema: Callable[..., Path], note: Note, tmp_path: Path
    ) -> None:
        outside = tmp_path / "outside.json"
        outside.write_text("{}")
        schema = Schema.load(write_schema({"$ref": outside.as_uri()}), root)
        assert schema.validate(note)[0].rule == "schema.invalid"

    @pytest.mark.parametrize("outside", [False, True])
    def test_note_scope(
        self,
        root: Path,
        write_schema: Callable[..., Path],
        tmp_path: Path,
        outside: bool,
    ) -> None:
        schema = Schema.load(write_schema(True), root)
        note = Note((tmp_path if outside else root) / "note.md", {}, "", 1)
        if outside:
            with pytest.raises(ValueError):
                schema.validate(note)
        else:
            # Explicit validation does not require a type for schema selection.
            assert schema.validate(note) == []

    @pytest.mark.parametrize(
        "schema", [True, {}, {"required": ["frontmatter", "body"]}]
    )
    def test_valid_note(
        self,
        root: Path,
        write_schema: Callable[..., Path],
        note: Note,
        schema: Any,
    ) -> None:
        path = write_schema(schema)
        before = path.read_bytes()
        assert (
            Schema.load(root / "reference/schemas/widget.schema.json", root).validate(
                note
            )
            == []
        )
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
        root: Path,
        write_schema: Callable[..., Path],
        note: Note,
        schema: Any,
        field: str,
    ) -> None:
        write_schema(schema)
        diagnostics = Schema.load(
            root / "reference/schemas/widget.schema.json", root
        ).validate(note)
        assert len(diagnostics) == 1
        error = diagnostics[0]
        assert (error.path, error.rule, error.field, error.severity) == (
            "content/Example.md",
            "schema.instance",
            field,
            "error",
        )
        assert error.message

    def test_deterministic_field_order(
        self, root: Path, write_schema: Callable[..., Path], note: Note
    ) -> None:
        write_schema(
            {
                "properties": {
                    "frontmatter": {"type": "array"},
                    "body": {"type": "integer"},
                }
            }
        )
        assert [
            d.field
            for d in Schema.load(
                root / "reference/schemas/widget.schema.json", root
            ).validate(note)
        ] == ["body", "frontmatter"]

    @pytest.mark.parametrize("external", [False, True], ids=["fragment", "file"])
    @pytest.mark.parametrize("valid", [False, True])
    def test_references(
        self,
        root: Path,
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
        diagnostics = Schema.load(
            root / "reference/schemas/widget.schema.json", root
        ).validate(note)
        assert [d.rule for d in diagnostics] == ([] if valid else ["schema.instance"])

    def test_relative_reference_chain(
        self, root: Path, write_schema: Callable[..., Path], note: Note
    ) -> None:
        write_schema({"$ref": "nested/first.json"})
        write_schema({"$ref": "second.json"}, "nested/first.json")
        write_schema({"required": ["body"]}, "nested/second.json")
        assert (
            Schema.load(root / "reference/schemas/widget.schema.json", root).validate(
                note
            )
            == []
        )


class TestSelectSchema:
    @pytest.mark.parametrize("relative", [False, True])
    def test_selects_without_validating(
        self,
        root: Path,
        write_schema: Callable[..., Path],
        note: Note,
        monkeypatch: pytest.MonkeyPatch,
        relative: bool,
    ) -> None:
        path = write_schema(False)
        monkeypatch.chdir(root.parent)
        selected_root = Path(root.name) if relative else root
        selected_note = (
            Note(note.path.relative_to(root.parent), note.frontmatter, note.body, 1)
            if relative
            else note
        )
        schema, diagnostics = select_schema(selected_note, selected_root)
        assert diagnostics == [] and schema is not None
        assert schema.path == path
        assert schema.contents is False

    def test_missing_schema_has_partial_coverage(self, root: Path, note: Note) -> None:
        schema, diagnostics = select_schema(note, root)
        assert schema is None and len(diagnostics) == 1
        warning = diagnostics[0]
        assert (warning.path, warning.rule, warning.severity) == (
            "content/Example.md",
            "schema.unsupported",
            "warning",
        )
        assert "Widget" in warning.message

    @pytest.mark.parametrize(
        "contents",
        [
            b"{",
            b"\xff",
            b'{"type": 12}',
            b'{"$schema": "http://json-schema.org/draft-07/schema#"}',
        ],
    )
    def test_invalid_schema(self, root: Path, note: Note, contents: bytes) -> None:
        (root / "reference/schemas/widget.schema.json").write_bytes(contents)
        schema, diagnostics = select_schema(note, root)
        assert schema is None and len(diagnostics) == 1
        assert diagnostics[0].rule == "schema.invalid"
        assert diagnostics[0].severity == "error"
        assert diagnostics[0].message

    def test_escaping_schema(self, root: Path, note: Note, tmp_path: Path) -> None:
        outside = tmp_path / "outside.json"
        outside.write_text("{}")
        (root / "reference/schemas/widget.schema.json").symlink_to(outside)
        schema, diagnostics = select_schema(note, root)
        assert schema is None and diagnostics[0].rule == "schema.invalid"

    @pytest.mark.parametrize("problem", ["missing-type", "outside-vault"])
    def test_caller_errors(
        self, root: Path, note: Note, tmp_path: Path, problem: str
    ) -> None:
        invalid = Note(
            tmp_path / "outside.md" if problem == "outside-vault" else note.path,
            {} if problem == "missing-type" else note.frontmatter,
            note.body,
            1,
        )
        with pytest.raises(ValueError):
            select_schema(invalid, root)

    def test_uses_only_selected_vault(
        self, root: Path, write_schema: Callable[..., Path], note: Note, tmp_path: Path
    ) -> None:
        write_schema(False)
        other = tmp_path / "other"
        (other / "reference/schemas").mkdir(parents=True)
        (other / "reference/schemas/widget.schema.json").write_text("true")
        other_note = Note(other / "note.md", note.frontmatter, note.body, 1)
        for selected_note, selected_root, expected in [
            (note, root, False),
            (other_note, other, True),
        ]:
            schema, diagnostics = select_schema(selected_note, selected_root)
            assert diagnostics == [] and schema is not None
            assert schema.contents is expected

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
        schema, diagnostics = select_schema(note, root)
        assert diagnostics == [] and schema is not None
        assert schema.validate(note) == []
