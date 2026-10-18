"""Schema loading, retrieval, validation and selection contracts."""

import contextlib
import json
import math
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import jsonschema_rs
import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource, Unresolvable
from referencing.jsonschema import DRAFT202012

from armarium.parse import Body, Frontmatter, Record
from armarium.schemas import (
    RUST_SPACE,
    SPACE,
    Schema,
    UnsupportedSchema,
    _check_numbers,
    _check_schema,
    _class_item,
    _conforms,
    _count_rewritten,
    _rewrite,
    _rust_char,
    _rust_class,
    _rust_formats,
    _walk_references,
    read_subtype_records,
    rust_pattern,
    rust_schema,
    select_schema,
)

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


class TestCheckSchema:
    @pytest.mark.parametrize("text", ["true", "{}", '{"type": "object"}'])
    def test_valid_schema_is_checked_once(self, text: str) -> None:
        _check_schema.cache_clear()
        with patch(
            "armarium.schemas.Draft202012Validator.check_schema",
            wraps=Draft202012Validator.check_schema,
        ) as check:
            _check_schema(text)
            _check_schema(text)
        check.assert_called_once_with(json.loads(text))

    def test_invalid_schema_raises_every_time(self) -> None:
        _check_schema.cache_clear()
        for _ in range(2):
            with pytest.raises(SchemaError):
                _check_schema('{"type": 12}')
        assert _check_schema.cache_info().currsize == 0


def rust_matches(pattern: str, text: str) -> bool:
    """Search text with a pattern as jsonschema-rs does."""
    validator = jsonschema_rs.Draft202012Validator({"pattern": pattern})
    return bool(validator.is_valid(text))


# Strings that tell apart how Python and Rust read patterns.
PROBES = [
    "",
    "a",
    "a\n",
    "a\nb",
    "\x1c",
    " a",
    "　",
    "ab]c",
    "a-b",
    "[[Port Briselle]]",
    "[[Port Briselle]]\n",
    "#x",
    "aaa",
    "é",
    "\n## Notes\nText",
]


class TestRustChar:
    @pytest.mark.parametrize(
        ("char", "expected"),
        [
            ("a", "a"),
            ("Z", "Z"),
            ("7", "7"),
            ("-", "\\x{2D}"),
            (" ", "\\x{20}"),
            ("é", "\\x{E9}"),
            ("\x1c", "\\x{1C}"),
            ("😀", "\\x{1F600}"),
        ],
    )
    def test_escapes_all_but_ascii_letters_and_digits(
        self, char: str, expected: str
    ) -> None:
        assert _rust_char(char) == expected
        assert rust_matches(f"^{expected}$", char)


class TestSpace:
    def test_is_what_python_s_matches(self) -> None:
        assert SPACE == "".join(
            chr(code) for code in range(0x110000) if re.match(r"\s", chr(code))
        )


class TestClassItem:
    @pytest.mark.parametrize(
        ("pattern", "expected"),
        [
            ("a", ("a", 1)),
            ("\\s", (None, 2)),
            ("\\S", ("\\S", 2)),
            ("\\n", ("\n", 2)),
            ("\\r", ("\r", 2)),
            ("\\t", ("\t", 2)),
            ("\\]", ("]", 2)),
            ("\\\\", ("\\", 2)),
        ],
    )
    def test_reads_one_item(
        self, pattern: str, expected: tuple[str | None, int]
    ) -> None:
        assert _class_item(pattern, 0) == expected

    @pytest.mark.parametrize("pattern", ["", "[", "\\d", "\\w", "\\x41", "\\"])
    def test_refuses(self, pattern: str) -> None:
        with pytest.raises(UnsupportedSchema):
            _class_item(pattern, 0)


class TestRustClass:
    @pytest.mark.parametrize(
        ("pattern", "expected"),
        [
            ("[a-z]x", ("[a-z]", 5)),
            ("[^a]", ("[^a]", 4)),
            ("[]a]", ("[\\x{5D}a]", 4)),
            ("[-a]", ("[\\x{2D}a]", 4)),
            ("[a-]", ("[a\\x{2D}]", 4)),
            ("[\\s\\S]", ("(?s:.)", 6)),
        ],
    )
    def test_translates(self, pattern: str, expected: tuple[str, int]) -> None:
        assert _rust_class(pattern, 0) == expected

    @pytest.mark.parametrize("pattern", ["[a", "[\\S]", "[^\\s\\S]", "[a-\\s]", "[[]"])
    def test_refuses(self, pattern: str) -> None:
        with pytest.raises(UnsupportedSchema):
            _rust_class(pattern, 0)


class TestRustPattern:
    @pytest.mark.parametrize(
        "pattern",
        [
            r"\S",
            r"^\s*$",
            r"^a$",
            r"a$|^b",
            r"^\[\[[^\[\]#|]+\]\]$",
            r"^\[\[(?!\s*\]\])[^\[\]#|\r\n]+\]\](?![\s\S])",
            r"[^\s\r\n]",
            r"[a-z\-]+",
            r"[]a]",
            r"a{2}",
            r"a{2,}",
            r"(?:a|b)+?c?",
            r"(?=a)a",
            r"\.\s*$",
            r"#x",
            r"[&&]|[~~]",
            r"\ |\}|}|]",
            r"(?:^|\n)## Notes[ \t]*(?=\r?\n|$)",
            "é",
        ],
    )
    def test_matches_as_python_does(self, pattern: str) -> None:
        translated = rust_pattern(pattern)
        for text in PROBES:
            assert rust_matches(translated, text) is bool(re.search(pattern, text)), (
                text
            )

    @pytest.mark.parametrize(
        "pattern",
        [
            r"\d",
            r"\w",
            r"\b",
            r"(?i)a",
            r"(?P<n>a)",
            r"(?<=a)b",
            r"a*+",
            r"a{,2}",
            r"\1",
            r"[[]",
            r"{",
            r"a{2}+",
        ],
    )
    def test_refuses_what_it_cannot_translate(self, pattern: str) -> None:
        with pytest.raises(UnsupportedSchema):
            rust_pattern(pattern)


class TestCheckNumbers:
    @pytest.mark.parametrize(
        "value",
        [None, True, "text", 1.5, -(2**63) + 1, 2**63 - 1, [1, {"a": [2.0]}]],
    )
    def test_accepts_exact_json(self, value: Any) -> None:
        _check_numbers(value)

    @pytest.mark.parametrize(
        "value",
        [2**63, [-(2**63)], {"a": math.inf}, math.nan, {1: "a"}, (1,), {"a": {1}}],
    )
    def test_refuses(self, value: Any) -> None:
        with pytest.raises(UnsupportedSchema):
            _check_numbers(value)


class TestCountRewritten:
    @pytest.mark.parametrize(
        ("value", "count"),
        [
            ({}, 0),
            ({"pattern": "a"}, 1),
            ({"pattern": "a", "multipleOf": 2}, 1),
            ([{"patternProperties": {}}, {"x": {"pattern": 1}}], 2),
            ({"const": {"pattern": "a"}}, 1),
            ("pattern", 0),
        ],
    )
    def test_counts_objects_holding_rewritten_keys(
        self, value: Any, count: int
    ) -> None:
        assert _count_rewritten(value) == count


class TestRewrite:
    def test_rewrites_every_subschema(self) -> None:
        schema = {
            "properties": {"pattern": {"pattern": "a$"}},
            "patternProperties": {"^b$": {"items": {"pattern": "c$"}}},
            "allOf": [{"pattern": "d$"}],
            "$defs": {"e": {"not": {"pattern": "e$"}}},
            "enum": [{"pattern": "f$"}],
            "pattern": "g$",
        }
        rewritten, found = _rewrite(schema)
        end = r"(?=\n?\z)"
        assert rewritten == {
            "properties": {"pattern": {"pattern": f"a{end}"}},
            "patternProperties": {f"^b{end}": {"items": {"pattern": f"c{end}"}}},
            "allOf": [{"pattern": f"d{end}"}],
            "$defs": {"e": {"not": {"pattern": f"e{end}"}}},
            "enum": [{"pattern": "f$"}],
            "pattern": f"g{end}",
        }
        # The schema itself and four subschemas; enum holds data, not schemas.
        assert found == 5

    @pytest.mark.parametrize("schema", [True, None, "text"])
    def test_leaves_other_values(self, schema: Any) -> None:
        assert _rewrite(schema) == (schema, 0)

    def test_refuses_multiple_of(self) -> None:
        with pytest.raises(UnsupportedSchema, match="multipleOf"):
            _rewrite({"items": {"multipleOf": 0.1}})


class TestRustSchema:
    def test_rewrites(self) -> None:
        assert rust_schema({"pattern": "\\S"}) == {"pattern": f"[^{RUST_SPACE}]"}

    @pytest.mark.parametrize(
        "schema",
        [
            {"pattern": "\\d"},
            {"maximum": 2**64},
            {"x-unknown": {"pattern": "a"}},
            {"$defs": {"a": {"multipleOf": 2}}},
        ],
    )
    def test_refuses(self, schema: Any) -> None:
        with pytest.raises(UnsupportedSchema):
            rust_schema(schema)


class TestWalkReferences:
    def walk(self, schema: Any, others: dict[str, Any] | None = None) -> None:
        registry: Registry[Any] = Registry().with_resources(
            [
                (uri, Resource.from_contents(contents, DRAFT202012))
                for uri, contents in {
                    "file:///s.json": schema,
                    **(others or {}),
                }.items()
            ]
        )
        _walk_references(schema, registry.resolver("file:///s.json"), (), set())

    @pytest.mark.parametrize(
        "schema",
        [
            True,
            {"$defs": {"a": {"type": "string"}}, "allOf": [{"$ref": "#/$defs/a"}] * 3},
            {"properties": {"x": {"$ref": "other.json"}}},
            {"$id": "file:///dir/inner.json", "$ref": "other.json"},
        ],
    )
    def test_accepts(self, schema: Any) -> None:
        self.walk(
            schema,
            {"file:///other.json": {"type": "string"}, "file:///dir/other.json": {}},
        )

    @pytest.mark.parametrize(
        "schema",
        [
            {"$ref": "#"},
            {
                "$defs": {"a": {"$ref": "#/$defs/b"}, "b": {"$ref": "#/$defs/a"}},
                "$ref": "#/$defs/a",
            },
            {"properties": {"child": {"$ref": "#"}}},
            {"$ref": "other.json"},
            {"$dynamicRef": "#a"},
            json.loads('{"not": ' * 60 + "{}" + "}" * 60),
        ],
    )
    def test_refuses(self, schema: Any) -> None:
        with pytest.raises(UnsupportedSchema):
            self.walk(schema, {"file:///other.json": {"$ref": "s.json"}})

    def test_unresolvable(self) -> None:
        with pytest.raises(Unresolvable):
            self.walk({"$ref": "#/$defs/missing"})


class TestRustFormats:
    def test_checks_jsonschema_s_formats(self) -> None:
        formats = _rust_formats()
        assert set(formats) == set(FormatChecker().checkers)
        assert formats["date"]("2026-10-18") and not formats["date"]("18/10/2026")

    @pytest.mark.parametrize("value", [5, 1.5, None, True, [], {}])
    def test_jsonschema_passes_values_that_are_not_strings(self, value: Any) -> None:
        # jsonschema-rs checks formats of strings only, which is safe only if
        # jsonschema's checkers pass everything else.
        checker = FormatChecker()
        assert all(checker.conforms(value, name) for name in checker.checkers)


class TestConforms:
    @pytest.mark.parametrize(("value", "expected"), [("a@b.c", True), ("ab", False)])
    def test_uses_the_checker(self, value: str, expected: bool) -> None:
        assert _conforms(FormatChecker(), "email", value) is expected


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


class TestSchemaRetrieveForRust:
    def test_rewrites_the_referenced_schema(
        self, root: Path, write_schema: Callable[..., Path]
    ) -> None:
        schema = Schema.load(write_schema(True), root)
        path = write_schema({"pattern": "a$"}, "helper.json")
        assert schema._retrieve_for_rust(path.as_uri()) == {"pattern": "a(?=\\n?\\z)"}

    @pytest.mark.parametrize(
        ("contents", "error"),
        [({"pattern": "\\d"}, UnsupportedSchema), (None, NoSuchResource)],
    )
    def test_raises(
        self,
        root: Path,
        write_schema: Callable[..., Path],
        contents: Any,
        error: type[Exception],
    ) -> None:
        schema = Schema.load(write_schema(True), root)
        path = write_schema(contents, "helper.json")
        uri = path.as_uri() if contents is not None else "https://example.invalid/"
        with pytest.raises(error):
            schema._retrieve_for_rust(uri)


class TestSchemaRustValidator:
    @pytest.mark.parametrize(
        ("contents", "built"),
        [
            (True, True),
            ({"properties": {"body": {"$ref": "helper.json"}}}, True),
            ({"pattern": "\\d"}, False),
            ({"$ref": "widget.schema.json"}, False),
            ({"$ref": "missing.json"}, False),
            ({"$ref": "https://example.invalid/schema.json"}, False),
            ({"anyOf": [{"$ref": "#/$defs/missing"}, True]}, False),
        ],
    )
    def test_built_only_where_rust_agrees(
        self, root: Path, write_schema: Callable[..., Path], contents: Any, built: bool
    ) -> None:
        write_schema({"type": "string"}, "helper.json")
        schema = Schema.load(write_schema(contents), root)
        assert (schema._rust_validator is not None) is built
        # Built once per schema.
        assert schema._rust_validator is schema._rust_validator


class TestSchemaPassesInRust:
    @pytest.mark.parametrize(
        ("instance", "passes"),
        [
            ({"name": "Example"}, True),
            ({"name": 5}, False),
            ({"name": "\x1c"}, False),
            ({"name": "\ud800"}, False),
            ({1: "Example"}, False),
            ({"name": "Example", "count": 2**70}, False),
        ],
    )
    def test_passes_only_what_rust_checks_and_passes(
        self,
        root: Path,
        write_schema: Callable[..., Path],
        instance: dict[Any, Any],
        passes: bool,
    ) -> None:
        schema = Schema.load(
            write_schema(
                {"properties": {"name": {"type": "string", "pattern": "\\S"}}}
            ),
            root,
        )
        assert schema._passes_in_rust(instance) is passes

    def test_without_a_validator(
        self, root: Path, write_schema: Callable[..., Path]
    ) -> None:
        schema = Schema.load(write_schema({"pattern": "\\d"}), root)
        assert schema._passes_in_rust({}) is False

    def test_a_failing_format_checker(
        self, root: Path, write_schema: Callable[..., Path]
    ) -> None:
        schema = Schema.load(write_schema({"format": "date"}), root)
        with patch.object(FormatChecker, "conforms", side_effect=RuntimeError):
            assert schema._passes_in_rust("2026-10-18") is False


class TestSchemaValidate:
    @pytest.mark.parametrize("rust", [False, True])
    @pytest.mark.parametrize(
        ("name", "errors"),
        [("Example", 0), ("\x1c", 1), ("Example\n", 0), ("", 1), ("é", 0)],
    )
    def test_same_with_and_without_rust(
        self,
        root: Path,
        write_schema: Callable[..., Path],
        rust: bool,
        name: str,
        errors: int,
    ) -> None:
        write_schema(
            {
                "properties": {
                    "frontmatter": {"properties": {"name": {"pattern": "^\\S+$"}}}
                }
            }
        )
        schema = Schema.load(root / "reference/schemas/widget.schema.json", root)
        record = Record(
            root / "content/Example.md", Frontmatter({"name": name}), Body("", 1)
        )
        with (
            patch.object(Schema, "_passes_in_rust", return_value=False)
            if not rust
            else (contextlib.nullcontext())
        ):
            diagnostics = schema.validate(record)
        assert len(diagnostics) == errors
        assert {d.rule for d in diagnostics} <= {"schema.instance"}

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

    def test_custom_loader(
        self, root: Path, write_schema: Callable[..., Path], record: Record
    ) -> None:
        path = write_schema(False)
        calls: list[tuple[Path, Path]] = []

        def load(schema_path: Path, schema_root: Path) -> Schema:
            calls.append((schema_path, schema_root))
            return Schema.load(schema_path, schema_root)

        schema, diagnostics = select_schema(record, root, load)
        assert diagnostics == [] and schema is not None and schema.path == path
        assert calls == [(path, root)]

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


class TestExtensionSchemaPaths:
    @pytest.mark.parametrize(
        "directory,valid", [("schemas", True), ("templates", False), ("notes", False)]
    )
    def test_extension_directories(
        self, root: Path, directory: str, valid: bool
    ) -> None:
        path = root / "reference/extensions/example" / directory / "test.schema.json"
        path.parent.mkdir(parents=True)
        path.write_text("true")
        if valid:
            assert Schema.load(path, root).contents is True
        else:
            with pytest.raises(ValueError, match="escapes"):
                Schema.load(path, root)

    def test_composes_with_core_schema(self, root: Path, record: Record) -> None:
        path = root / "reference/extensions/example/schemas/test.schema.json"
        path.parent.mkdir(parents=True)
        (root / "reference/schemas/core.schema.json").write_text("true")
        path.write_text('{"$ref": "../../../schemas/core.schema.json"}')
        assert Schema.load(path, root).validate(record) == []


class TestReadSubtypeRecords:
    SCHEMA = {
        "properties": {"frontmatter": {"properties": {"size": {"type": "integer"}}}}
    }

    @staticmethod
    def write(root: Path, relative: str, text: str) -> None:
        path = root / "reference/things" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_reads_the_subtype_in_path_order(
        self, root: Path, write_schema: Callable[..., Path]
    ) -> None:
        write_schema(self.SCHEMA, "reference.schema.json")
        thing = '---\ntype: "[[Reference]]"\nsubtype: Thing\nsize: 2\n---\n'
        self.write(root, "b.md", thing)
        self.write(root, "nested/a.md", thing)
        self.write(root, "other.md", '---\ntype: "[[Reference]]"\nsize: x\n---\n')
        self.write(
            root, "content.md", '---\ntype: "[[Content]]"\nsubtype: Thing\n---\n'
        )
        self.write(root, "notes.txt", "not a record")
        records = read_subtype_records(root, "reference/things", "Thing")
        assert [r.path.relative_to(root).as_posix() for r in records] == [
            "reference/things/b.md",
            "reference/things/nested/a.md",
        ]

    def test_a_missing_folder_holds_none(self, root: Path) -> None:
        assert read_subtype_records(root, "reference/things", "Thing") == []

    @pytest.mark.parametrize(
        ("text", "schema", "message"),
        [
            ("---\ntype: [\n---\n", True, "^reference/things/a.md: "),
            (
                '---\ntype: "[[Reference]]"\nsubtype: Thing\nsize: x\n---\n',
                True,
                "^reference/things/a.md: frontmatter.size: 'x' is not of type",
            ),
            (
                '---\ntype: "[[Reference]]"\nsubtype: Thing\n---\n',
                False,
                "^reference/things/a.md: no vault-local schema for Reference$",
            ),
        ],
    )
    def test_refuses_a_record_it_cannot_use(
        self,
        root: Path,
        write_schema: Callable[..., Path],
        text: str,
        schema: bool,
        message: str,
    ) -> None:
        if schema:
            write_schema(self.SCHEMA, "reference.schema.json")
        self.write(root, "a.md", text)
        with pytest.raises(ValueError, match=message):
            read_subtype_records(root, "reference/things", "Thing")
