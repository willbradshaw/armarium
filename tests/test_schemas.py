"""Schema loading, retrieval, validation and selection contracts."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from jsonschema.exceptions import SchemaError
from referencing.exceptions import NoSuchResource

from armarium.parse import Body, Frontmatter, Record
from armarium.schemas import Schema, select_schema

ROOT = Path(__file__).resolve().parents[1]


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
def record(root: Path) -> Record:
    return Record(
        root / "content/Example.md",
        Frontmatter({"type": "[[types/Widget]]", "name": "Example"}),
        Body("## Notes\n", 5),
    )


class TestSchema:
    def test_represents_one_schema(
        self, root: Path, write_schema: Callable[..., Path], record: Record
    ) -> None:
        path = write_schema(True)
        schema = Schema.load(path, root)
        assert schema.path == path
        assert schema.root == root
        assert schema.contents is True
        # Loading fixes the selected schema's contents for reuse across records.
        path.write_text("false")
        assert schema.validate(record) == []


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
        self,
        root: Path,
        write_schema: Callable[..., Path],
        record: Record,
        reference: str,
    ) -> None:
        schema = Schema.load(write_schema({"$ref": reference}), root)
        diagnostics = schema.validate(record)
        assert len(diagnostics) == 1
        assert diagnostics[0].rule == "schema.invalid" and diagnostics[0].message

    def test_escaping_reference(
        self,
        root: Path,
        write_schema: Callable[..., Path],
        record: Record,
        tmp_path: Path,
    ) -> None:
        outside = tmp_path / "outside.json"
        outside.write_text("{}")
        schema = Schema.load(write_schema({"$ref": outside.as_uri()}), root)
        assert schema.validate(record)[0].rule == "schema.invalid"

    @pytest.mark.parametrize("outside", [False, True])
    def test_record_scope(
        self,
        root: Path,
        write_schema: Callable[..., Path],
        tmp_path: Path,
        outside: bool,
    ) -> None:
        schema = Schema.load(write_schema(True), root)
        record = Record(
            (tmp_path if outside else root) / "record.md", Frontmatter({}), Body("", 1)
        )
        if outside:
            with pytest.raises(ValueError):
                schema.validate(record)
        else:
            # Explicit validation does not require a type for schema selection.
            assert schema.validate(record) == []

    @pytest.mark.parametrize(
        "schema", [True, {}, {"required": ["frontmatter", "body"]}]
    )
    def test_valid_record(
        self,
        root: Path,
        write_schema: Callable[..., Path],
        record: Record,
        schema: Any,
    ) -> None:
        path = write_schema(schema)
        before = path.read_bytes()
        assert (
            Schema.load(root / "reference/schemas/widget.schema.json", root).validate(
                record
            )
            == []
        )
        assert path.read_bytes() == before
        assert record.frontmatter == {"type": "[[types/Widget]]", "name": "Example"}
        assert record.body.text == "## Notes\n"

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
        record: Record,
        schema: Any,
        field: str,
    ) -> None:
        write_schema(schema)
        diagnostics = Schema.load(
            root / "reference/schemas/widget.schema.json", root
        ).validate(record)
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
        self, root: Path, write_schema: Callable[..., Path], record: Record
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
            ).validate(record)
        ] == ["body", "frontmatter"]

    @pytest.mark.parametrize("external", [False, True], ids=["fragment", "file"])
    @pytest.mark.parametrize("valid", [False, True])
    def test_references(
        self,
        root: Path,
        write_schema: Callable[..., Path],
        record: Record,
        external: bool,
        valid: bool,
    ) -> None:
        target = {
            "properties": {"body": {"const": record.body.text if valid else "Other"}}
        }
        if external:
            write_schema(target, "nested dir/helper.json")
            schema = {"$ref": "nested%20dir/helper.json"}
        else:
            schema = {"$defs": {"target": target}, "$ref": "#/$defs/target"}
        write_schema(schema)
        diagnostics = Schema.load(
            root / "reference/schemas/widget.schema.json", root
        ).validate(record)
        assert [d.rule for d in diagnostics] == ([] if valid else ["schema.instance"])

    def test_relative_reference_chain(
        self, root: Path, write_schema: Callable[..., Path], record: Record
    ) -> None:
        write_schema({"$ref": "nested/first.json"})
        write_schema({"$ref": "second.json"}, "nested/first.json")
        write_schema({"required": ["body"]}, "nested/second.json")
        assert (
            Schema.load(root / "reference/schemas/widget.schema.json", root).validate(
                record
            )
            == []
        )


class TestSelectSchema:
    @pytest.mark.parametrize("relative", [False, True])
    def test_selects_without_validating(
        self,
        root: Path,
        write_schema: Callable[..., Path],
        record: Record,
        monkeypatch: pytest.MonkeyPatch,
        relative: bool,
    ) -> None:
        path = write_schema(False)
        monkeypatch.chdir(root.parent)
        selected_root = Path(root.name) if relative else root
        selected_record = (
            Record(
                record.path.relative_to(root.parent),
                record.frontmatter,
                Body(record.body.text, 1),
            )
            if relative
            else record
        )
        schema, diagnostics = select_schema(selected_record, selected_root)
        assert diagnostics == [] and schema is not None
        assert schema.path == path
        assert schema.contents is False

    def test_missing_schema_is_error(self, root: Path, record: Record) -> None:
        schema, diagnostics = select_schema(record, root)
        assert schema is None and len(diagnostics) == 1
        error = diagnostics[0]
        assert (error.path, error.rule, error.severity) == (
            "content/Example.md",
            "schema.unsupported",
            "error",
        )
        assert "Widget" in error.message

    @pytest.mark.parametrize(
        "contents",
        [
            b"{",
            b"\xff",
            b'{"type": 12}',
            b'{"$schema": "http://json-schema.org/draft-07/schema#"}',
        ],
    )
    def test_invalid_schema(self, root: Path, record: Record, contents: bytes) -> None:
        (root / "reference/schemas/widget.schema.json").write_bytes(contents)
        schema, diagnostics = select_schema(record, root)
        assert schema is None and len(diagnostics) == 1
        assert diagnostics[0].rule == "schema.invalid"
        assert diagnostics[0].severity == "error"
        assert diagnostics[0].message

    def test_escaping_schema(self, root: Path, record: Record, tmp_path: Path) -> None:
        outside = tmp_path / "outside.json"
        outside.write_text("{}")
        (root / "reference/schemas/widget.schema.json").symlink_to(outside)
        schema, diagnostics = select_schema(record, root)
        assert schema is None and diagnostics[0].rule == "schema.invalid"

    @pytest.mark.parametrize("problem", ["missing-type", "outside-vault"])
    def test_caller_errors(
        self, root: Path, record: Record, tmp_path: Path, problem: str
    ) -> None:
        invalid = Record(
            tmp_path / "outside.md" if problem == "outside-vault" else record.path,
            Frontmatter({}) if problem == "missing-type" else record.frontmatter,
            Body(record.body.text, 1),
        )
        with pytest.raises(ValueError):
            select_schema(invalid, root)

    def test_uses_only_selected_vault(
        self,
        root: Path,
        write_schema: Callable[..., Path],
        record: Record,
        tmp_path: Path,
    ) -> None:
        write_schema(False)
        other = tmp_path / "other"
        (other / "reference/schemas").mkdir(parents=True)
        (other / "reference/schemas/widget.schema.json").write_text("true")
        other_record = Record(
            other / "record.md", record.frontmatter, Body(record.body.text, 1)
        )
        for selected_record, selected_root, expected in [
            (record, root, False),
            (other_record, other, True),
        ]:
            schema, diagnostics = select_schema(selected_record, selected_root)
            assert diagnostics == [] and schema is not None
            assert schema.contents is expected

    @pytest.mark.parametrize("vault", ["starter", "example"])
    @pytest.mark.parametrize(
        "kind",
        [
            "content",
            "clue",
            "session",
            "transcript",
            "player",
            "reference",
            "type",
            "status",
        ],
    )
    def test_shipped_schema_contract(self, vault: str, kind: str) -> None:
        fixture = json.loads(
            (ROOT / f"tests/schemas/fixtures/{kind}.json").read_text()
        )["base"]
        root = ROOT / f"vaults/{vault}"
        record = Record(
            root / "record.md",
            Frontmatter(fixture["frontmatter"]),
            Body(fixture["body"], 1),
        )
        schema, diagnostics = select_schema(record, root)
        assert diagnostics == [] and schema is not None
        assert schema.validate(record) == []

    @pytest.mark.parametrize("vault", ["starter", "example"])
    @pytest.mark.parametrize(
        ("status", "replacement", "valid"),
        [
            ("Superseded", "[[C-1-0005]]", True),
            ("Superseded", ..., False),
            ("Revealed", "[[C-1-0005]]", False),
            ("Revealed", None, False),
        ],
        ids=["present", "absent", "present outside", "null outside"],
    )
    def test_shipped_clue_replacement(
        self, vault: str, status: str, replacement: object, valid: bool
    ) -> None:
        fixture = json.loads((ROOT / "tests/schemas/fixtures/clue.json").read_text())
        metadata = dict(fixture["base"]["frontmatter"], status=f"[[{status}]]")
        if replacement is not ...:
            metadata["superseded_by"] = replacement
        root = ROOT / f"vaults/{vault}"
        record = Record(
            root / "record.md", Frontmatter(metadata), Body(fixture["base"]["body"], 1)
        )
        schema, diagnostics = select_schema(record, root)
        assert diagnostics == [] and schema is not None
        assert (schema.validate(record) == []) is valid
