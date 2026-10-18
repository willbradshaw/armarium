"""Vault-local Draft 2020-12 schemas with offline, confined references."""

import functools
import json
import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import jsonschema_rs
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource, Unresolvable
from referencing.jsonschema import DRAFT202012

from armarium.lib import Diagnostic, find_files, relative_posix
from armarium.parse import Record


@functools.cache
def _check_schema(text: str) -> None:
    """Meta-validate schema JSON once per distinct text.

    Draft 2020-12 meta-validation is slow, and the same schema files are loaded
    again for every referencing record and every installed vault. Only passing
    texts are cached, so an invalid schema raises each time it is loaded.

    Args:
        text: JSON text of a schema, already known to parse.

    Raises:
        SchemaError: The schema fails Draft 2020-12 meta-validation.
    """
    Draft202012Validator.check_schema(json.loads(text))


# -----------------------------------------------------------------------------
# A fast first pass in Rust
# -----------------------------------------------------------------------------
# jsonschema-rs checks a record many times faster than jsonschema. It only
# decides whether a record passes: a record that fails, or that it cannot
# check, is validated again by jsonschema, whose messages are reported. So it
# must never pass a record that jsonschema fails. Where the two differ, the
# schema is rewritten for Rust or left to jsonschema alone.


class UnsupportedSchema(ValueError):
    """A schema uses something whose Rust meaning may differ from Python's."""


# The characters \s matches in a Python str pattern, which are those for which
# str.isspace is true. Rust's \s leaves out \x1c to \x1f.
SPACE = "\t\n\x0b\x0c\r\x1c\x1d\x1e\x1f \x85\xa0                　"

# Escapes that name the same character in both: carriage return, newline, tab.
CONTROL_ESCAPES = {"r": "\r", "n": "\n", "t": "\t"}

# A bounded repetition, the only form Python and Rust read alike.
REPETITION = re.compile(r"\{[0-9]+(?:,[0-9]*)?\}")

# Keywords whose value is a schema, an array of schemas or a map of them.
SUBSCHEMA = frozenset(
    {
        "additionalProperties",
        "contains",
        "else",
        "if",
        "items",
        "not",
        "propertyNames",
        "then",
        "unevaluatedItems",
        "unevaluatedProperties",
    }
)
SUBSCHEMA_ARRAYS = frozenset({"allOf", "anyOf", "oneOf", "prefixItems"})
SUBSCHEMA_MAPS = frozenset(
    {"$defs", "dependentSchemas", "patternProperties", "properties"}
)

# Keywords the two libraries compute differently: multipleOf divides floats.
UNSUPPORTED_KEYWORDS = frozenset({"multipleOf"})

# Keys a schema object holds whose meaning the rewrite must have handled.
REWRITTEN_KEYS = frozenset({"pattern", "patternProperties"} | UNSUPPORTED_KEYWORDS)

# Integers both libraries hold exactly.
LARGEST_INTEGER = 2**63

# The deepest nesting of subschemas left to jsonschema-rs, far within the
# recursion limit jsonschema would meet.
MAX_DEPTH = 50


def _rust_char(char: str) -> str:
    """Write one character as a Rust regex literal, escaping all but ASCII letters and digits."""
    return char if char.isascii() and char.isalnum() else f"\\x{{{ord(char):X}}}"


# The members of Python's \s, as written inside a Rust character class.
RUST_SPACE = "".join(map(_rust_char, SPACE))


def _class_item(pattern: str, start: int) -> tuple[str | None, int]:
    """Read one character or escape at a position inside a character class.

    Returns:
        tuple[str | None, int]: The literal character, or None for \\s; and
            the position after the item. \\S is returned as "\\S".

    Raises:
        UnsupportedSchema: An escape other than \\s, \\S, \\r, \\n, \\t and
            escaped ASCII punctuation, or an unclosed class.
    """
    if start >= len(pattern):
        raise UnsupportedSchema("unclosed character class")
    char = pattern[start]
    if char == "[":
        raise UnsupportedSchema("[ inside a character class")
    if char != "\\":
        return char, start + 1
    escaped = pattern[start + 1 : start + 2]
    if escaped == "s":
        return None, start + 2
    if escaped == "S":
        return "\\S", start + 2
    if escaped in CONTROL_ESCAPES:
        return CONTROL_ESCAPES[escaped], start + 2
    if escaped.isascii() and escaped and not escaped.isalnum():
        return escaped, start + 2
    raise UnsupportedSchema(f"escape \\{escaped}")


def _rust_class(pattern: str, start: int) -> tuple[str, int]:
    """Translate the character class opening at a position.

    Returns:
        tuple[str, int]: The Rust class and the position after the class.

    Raises:
        UnsupportedSchema: As _class_item, or \\S in a class other than [\\s\\S].
    """
    position = start + 1
    negated = pattern[position : position + 1] == "^"
    position += negated
    items: list[str] = []
    space = nonspace = False
    first = True
    while first or pattern[position : position + 1] != "]":
        first = False
        item, position = _class_item(pattern, position)
        if item is None:
            space = True
        elif item == "\\S":
            nonspace = True
        elif (
            pattern[position : position + 1] == "-"
            and pattern[position + 1 : position + 2] != "]"
        ):
            end, position = _class_item(pattern, position + 1)
            if end is None or end == "\\S":
                raise UnsupportedSchema("range to a class escape")
            items.append(f"{_rust_char(item)}-{_rust_char(end)}")
        else:
            items.append(_rust_char(item))
        if position >= len(pattern):
            raise UnsupportedSchema("unclosed character class")
    if nonspace:
        if space and not negated:
            return "(?s:.)", position + 1
        raise UnsupportedSchema("\\S inside a character class")
    body = "".join(items) + (RUST_SPACE if space else "")
    return f"[{'^' if negated else ''}{body}]", position + 1


def rust_pattern(pattern: str) -> str:
    """Translate a Python regular expression into Rust's, with the same matches.

    Rust's \\s leaves out \\x1c to \\x1f, its $ matches only at the end, not
    also before a final newline, and it reads some punctuation as operators
    that Python reads as characters. The translation covers what schemas
    use: characters, escaped punctuation, \\r, \\n, \\t, \\s and \\S, classes
    and ranges, groups, lookaheads, alternation and quantifiers.

    Args:
        pattern: A Python regular expression.

    Returns:
        str: A Rust regular expression matching the same strings with search.

    Raises:
        UnsupportedSchema: The pattern uses anything else, such as \\d, \\w,
            \\b, flags, named groups, lookbehinds or possessive quantifiers.
    """
    output: list[str] = []
    position = 0
    while position < len(pattern):
        char = pattern[position]
        if char == "\\":
            item, position = _class_item(pattern, position)
            if item is None:
                output.append(f"[{RUST_SPACE}]")
            elif item == "\\S":
                output.append(f"[^{RUST_SPACE}]")
            else:
                output.append(_rust_char(item))
            continue
        if char == "[":
            translated, position = _rust_class(pattern, position)
            output.append(translated)
            continue
        if char == "(":
            opening = pattern[position : position + 3]
            if opening in ("(?:", "(?=", "(?!"):
                output.append(opening)
                position += 3
                continue
            if opening[1:2] == "?":
                raise UnsupportedSchema(f"group {opening}")
            output.append(char)
        elif char == "{":
            repetition = REPETITION.match(pattern, position)
            if repetition is None:
                raise UnsupportedSchema("{ outside a repetition")
            output.append(repetition.group())
            position = repetition.end() - 1
        elif char == "$":
            output.append(r"(?=\n?\z)")
        elif char in "^.|)*+?":
            output.append(char)
        else:
            output.append(_rust_char(char))
        position += 1
        if char in "*+?{" and pattern[position : position + 1] == "+":
            raise UnsupportedSchema("possessive quantifier")
    return "".join(output)


def _check_numbers(node: Any) -> None:
    """Require every number in a JSON value to be one both libraries hold exactly.

    Raises:
        UnsupportedSchema: An integer of 2**63 or more in size, a float that is
            not finite, a key that is not a string, or a value that is not JSON.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if not isinstance(key, str):
                raise UnsupportedSchema("a key that is not a string")
            _check_numbers(value)
    elif isinstance(node, list):
        for value in node:
            _check_numbers(value)
    elif isinstance(node, bool) or node is None or isinstance(node, str):
        return
    elif isinstance(node, int):
        if abs(node) >= LARGEST_INTEGER:
            raise UnsupportedSchema("an integer too large for Rust")
    elif isinstance(node, float):
        if not math.isfinite(node):
            raise UnsupportedSchema("a number that is not finite")
    else:
        raise UnsupportedSchema(f"a {type(node).__name__} value")


def _count_rewritten(node: Any) -> int:
    """Count the objects anywhere in a JSON value holding a REWRITTEN_KEYS key."""
    if isinstance(node, dict):
        own = int(not REWRITTEN_KEYS.isdisjoint(node))
        return own + sum(_count_rewritten(value) for value in node.values())
    if isinstance(node, list):
        return sum(_count_rewritten(value) for value in node)
    return 0


def _rewrite(schema: Any) -> tuple[Any, int]:
    """Rewrite the patterns of a schema and its subschemas; see rust_schema.

    Returns:
        tuple[Any, int]: The rewritten schema and how many of its schema
            objects hold a REWRITTEN_KEYS key.
    """
    if not isinstance(schema, dict):
        return schema, 0
    rewritten: dict[str, Any] = {}
    found = int(not REWRITTEN_KEYS.isdisjoint(schema))
    for key, value in schema.items():
        if key in UNSUPPORTED_KEYWORDS:
            raise UnsupportedSchema(key)
        if key == "pattern" and isinstance(value, str):
            value = rust_pattern(value)
        elif key in SUBSCHEMA:
            value, count = _rewrite(value)
            found += count
        elif key in SUBSCHEMA_ARRAYS and isinstance(value, list):
            items = [_rewrite(item) for item in value]
            value = [item for item, _ in items]
            found += sum(count for _, count in items)
        elif key in SUBSCHEMA_MAPS and isinstance(value, dict):
            named = {name: _rewrite(item) for name, item in value.items()}
            value = {
                rust_pattern(name) if key == "patternProperties" else name: item
                for name, (item, _) in named.items()
            }
            found += sum(count for _, count in named.values())
        rewritten[key] = value
    return rewritten, found


def rust_schema(schema: Any) -> Any:
    """Rewrite a schema for jsonschema-rs so that it accepts what jsonschema does.

    Args:
        schema: A Draft 2020-12 schema document.

    Returns:
        Any: A copy with every pattern and patternProperties name translated
            by rust_pattern.

    Raises:
        UnsupportedSchema: A pattern cannot be translated; the schema uses
            multipleOf; it holds numbers Rust cannot hold exactly; or a
            pattern, patternProperties or multipleOf lies where the rewrite
            does not reach, such as under an unknown keyword a $ref may name.
    """
    _check_numbers(schema)
    rewritten, found = _rewrite(schema)
    if found != _count_rewritten(schema):
        raise UnsupportedSchema("a pattern outside the schema's keywords")
    return rewritten


def _walk_references(
    schema: Any, resolver: Any, chain: tuple[int, ...], done: set[int]
) -> None:
    """Follow a schema's subschemas and references, as jsonschema may.

    jsonschema recurses through a reference cycle until Python's recursion
    limit, which it reports, where jsonschema-rs passes; a deep enough schema
    does the same. Each schema object is explored once.

    Args:
        schema: A schema object, or a boolean schema.
        resolver: The referencing Resolver for references from this schema object.
        chain: The schema objects leading here, by id.
        done: Schema objects already explored, by id.

    Raises:
        UnsupportedSchema: A reference cycle, a $dynamicRef, or subschemas
            nested more than MAX_DEPTH deep.
        Unresolvable: A reference cannot be resolved.
        NoSuchResource, OSError, ValueError, SchemaError: As Schema._retrieve.
    """
    if not isinstance(schema, dict) or id(schema) in done:
        return
    if id(schema) in chain:
        raise UnsupportedSchema("a reference cycle")
    if len(chain) >= MAX_DEPTH:
        raise UnsupportedSchema("subschemas nested too deeply")
    if "$dynamicRef" in schema:
        raise UnsupportedSchema("$dynamicRef")
    chain += (id(schema),)
    if "$id" in schema:
        resolver = resolver.in_subresource(DRAFT202012.create_resource(schema))
    children: list[Any] = []
    for key, value in schema.items():
        if key in SUBSCHEMA:
            children.append(value)
        elif key in SUBSCHEMA_ARRAYS and isinstance(value, list):
            children += value
        elif key in SUBSCHEMA_MAPS and isinstance(value, dict):
            children += value.values()
    for child in children:
        _walk_references(child, resolver, chain, done)
    if isinstance(schema.get("$ref"), str):
        resolved = resolver.lookup(schema["$ref"])
        _walk_references(resolved.contents, resolved.resolver, chain, done)
    done.add(id(schema))


@functools.cache
def _rust_formats() -> dict[str, Callable[[str], bool]]:
    """Check each format jsonschema knows with jsonschema's own checker.

    jsonschema-rs calls these for strings only; jsonschema's checkers pass
    every value that is not a string.
    """
    checker = FormatChecker()
    return {
        name: functools.partial(_conforms, checker, name) for name in checker.checkers
    }


def _conforms(checker: FormatChecker, name: str, instance: str) -> bool:
    """Tell whether a string conforms to a format, as jsonschema checks it."""
    return checker.conforms(instance, name)


@dataclass(frozen=True)
class Schema:
    """One loaded schema and the vault boundary for its references.

    Attributes:
        path: Absolute path identifying this schema.
        root: Absolute vault path used for confinement and diagnostic labels.
        contents: Meta-validated JSON schema object or boolean.
    """

    path: Path
    root: Path
    contents: Any

    @classmethod
    def load(cls, path: Path, root: Path) -> "Schema":
        """Read one confined schema and check its Draft 2020-12 syntax.

        Args:
            path: Schema file path, absolute or relative to the working directory.
            root: Vault path, absolute or relative to the working directory.

        Returns:
            Schema: The loaded schema. An omitted $schema defaults to Draft
                2020-12; an explicit different dialect is rejected. References
                are retrieved later, as validation encounters them.

        Raises:
            OSError: The schema cannot be read.
            ValueError: The path escapes core/extension schema directories, JSON is
                invalid or the declared dialect is unsupported.
            SchemaError: The schema fails Draft 2020-12 meta-validation.
        """
        root, path = root.absolute(), path.absolute()
        directory = root / "reference/schemas"
        extensions = root / "reference/extensions"
        if path.is_relative_to(extensions):
            relative = path.relative_to(extensions)
            if len(relative.parts) >= 3 and relative.parts[1] == "schemas":
                directory = extensions / relative.parts[0] / "schemas"
        if not directory.resolve().is_relative_to(
            root.resolve()
        ) or not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError(
                "schema reference escapes reference/schemas or extension schemas"
            )
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        _check_schema(text)
        if (
            isinstance(data, dict)
            and data.get("$schema", "https://json-schema.org/draft/2020-12/schema")
            != "https://json-schema.org/draft/2020-12/schema"
        ):
            raise ValueError("schema must use Draft 2020-12")
        return cls(path, root, data)

    def _retrieve(self, uri: str) -> Resource[Any]:
        """Serve the registry callback using only a confined local file URI.

        Args:
            uri: Absolute URI requested by the reference registry.

        Returns:
            Resource[Any]: A meta-validated Draft 2020-12 schema resource.

        Raises:
            NoSuchResource: The URI is not a local file URI with no host.
            OSError: The file cannot be read.
            ValueError: The file escapes the schema directory or is invalid JSON
                or uses an unsupported dialect.
            SchemaError: The referenced schema is invalid.
        """
        parsed = urlparse(uri)
        if parsed.scheme != "file" or parsed.netloc:
            raise NoSuchResource(uri)
        referenced = self.load(Path(unquote(parsed.path)), self.root)
        return Resource.from_contents(
            referenced.contents, default_specification=DRAFT202012
        )

    def _retrieve_for_rust(self, uri: str) -> Any:
        """Serve jsonschema-rs a referenced schema, rewritten by rust_schema.

        Args:
            uri: Absolute URI of the referenced schema.

        Returns:
            Any: The confined, meta-validated schema, rewritten for Rust.

        Raises:
            NoSuchResource, OSError, ValueError, SchemaError: As _retrieve.
            UnsupportedSchema: As rust_schema.
        """
        return rust_schema(self._retrieve(uri).contents)

    @functools.cached_property
    def _rust_validator(self) -> jsonschema_rs.Validator | None:
        """Build this schema's jsonschema-rs validator once, if it can have one.

        jsonschema-rs resolves every reference as it builds, used or not, so a
        schema with any reference that fails to load, or any part it cannot
        take, has none and is left to jsonschema alone.
        """
        try:
            resource = Resource.from_contents(
                self.contents, default_specification=DRAFT202012
            )
            registry: Registry[Any] = Registry(retrieve=self._retrieve)  # type: ignore[call-arg]
            registry = registry.with_resource(self.path.as_uri(), resource)
            _walk_references(
                self.contents, registry.resolver(self.path.as_uri()), (), set()
            )
            return jsonschema_rs.Draft202012Validator(
                rust_schema(self.contents),
                base_uri=self.path.as_uri(),
                retriever=self._retrieve_for_rust,
                validate_formats=True,
                formats=_rust_formats(),
            )
        except Exception:  # noqa: BLE001 - any failure falls back to jsonschema
            return None

    def _passes_in_rust(self, instance: dict[str, Any]) -> bool:
        """Tell whether jsonschema-rs passes an instance; see _rust_validator.

        Returns:
            bool: True only when jsonschema-rs checked the instance and found
                it valid. An instance it cannot take, such as one holding a
                date or a surrogate, or a format checker that raises, gives
                False, so that jsonschema reports what it finds.
        """
        validator = self._rust_validator
        if validator is None:
            return False
        try:
            _check_numbers(instance)
            return validator.is_valid(instance)
        except Exception:  # noqa: BLE001 - any failure falls back to jsonschema
            return False

    def validate(self, record: Record) -> list[Diagnostic]:
        """Validate a record against this explicitly loaded schema.

        Args:
            record: Parsed record inside this vault. Schema selection is independent
                of validation; this method does not inspect the declared type.

        Returns:
            list[Diagnostic]: Field-located schema.instance errors, schema.invalid
                findings for reference failures, or an empty list on success.
                References are resolved as encountered, without auditing unused
                branches. The loaded contents and source files are not modified.

        Raises:
            ValueError: The record lies outside the vault.
        """
        relative = relative_posix(record.path.absolute(), self.root)
        instance = {"frontmatter": dict(record.frontmatter), "body": record.body.text}
        # jsonschema-rs passes most records quickly; jsonschema checks the rest.
        if self._passes_in_rust(instance):
            return []
        try:
            resource = Resource.from_contents(
                self.contents, default_specification=DRAFT202012
            )
            registry: Registry[Any] = Registry(retrieve=self._retrieve)  # type: ignore[call-arg]
            registry = registry.with_resource(self.path.as_uri(), resource)
            validator = Draft202012Validator(
                {"$ref": self.path.as_uri()},
                registry=registry,
                format_checker=FormatChecker(),
            )
            errors = sorted(
                validator.iter_errors(instance),
                key=lambda e: str(list(e.absolute_path)),
            )
            return [
                Diagnostic(
                    relative,
                    "schema.instance",
                    error.message,
                    field=".".join(map(str, error.absolute_path)),
                )
                for error in errors
            ]
        except (
            OSError,
            ValueError,
            SchemaError,
            NoSuchResource,
            Unresolvable,
            RecursionError,
        ) as exc:
            return [Diagnostic(relative, "schema.invalid", str(exc))]


def select_schema(
    record: Record, root: Path, load: Callable[[Path, Path], Schema] = Schema.load
) -> tuple[Schema | None, list[Diagnostic]]:
    """Load the vault-local schema selected by a record's canonical type.

    Args:
        record: Parsed record inside the vault with a canonical declared type.
        root: Vault path, absolute or relative to the working directory.
        load: Schema loader taking the schema path and vault root; a validation
            run passes VaultIndex.load_schema to load each schema once.

    Returns:
        tuple[Schema | None, list[Diagnostic]]: A loaded schema and no findings,
            or None with a schema.unsupported error for a missing schema or a
            schema.invalid error for an unreadable/invalid schema. This function
            selects and loads the schema; it does not validate the record.

    Raises:
        ValueError: The record has no canonical type or lies outside the vault.
    """
    parsed_type = record.frontmatter.type
    if parsed_type is None:
        raise ValueError("schema selection requires a canonical record type")
    relative = relative_posix(record.path.absolute(), root.absolute())
    path = root / "reference/schemas" / f"{parsed_type.lower()}.schema.json"
    if not path.exists():
        return None, [
            Diagnostic(
                relative,
                "schema.unsupported",
                f"no vault-local schema for {parsed_type}",
            )
        ]
    try:
        return load(path, root), []
    except (OSError, ValueError, SchemaError, RecursionError) as exc:
        return None, [Diagnostic(relative, "schema.invalid", str(exc))]


def read_subtype_records(root: Path, directory: str, subtype: str) -> list[Record]:
    """Read the Reference records of a subtype in a folder, schema-checked.

    Args:
        root: Vault root.
        directory: Vault-relative folder to read, with its subfolders.
        subtype: The Reference subtype to read, such as Style.

    Returns:
        list[Record]: The folder's Reference records of that subtype, in path
            order; other records are passed over. Empty when the folder does
            not exist.

    Raises:
        ValueError: A record cannot be parsed, or one of the subtype fails
            the vault's Reference schema.
        OSError: A file cannot be read.
    """
    folder = root / directory
    if not folder.is_dir() or folder.is_symlink():
        return []
    records: list[Record] = []
    for path in find_files(folder, ".md"):
        record, diagnostics = Record.parse(path, root)
        relative = path.relative_to(root).as_posix()
        if record is None:
            raise ValueError(f"{relative}: {diagnostics[0].message}")
        if (
            record.frontmatter.type != "Reference"
            or record.frontmatter.get("subtype") != subtype
        ):
            continue
        schema, diagnostics = select_schema(record, root)
        if schema is not None:
            diagnostics = schema.validate(record)
        if diagnostics:
            failure = diagnostics[0]
            field = f"{failure.field}: " if failure.field else ""
            raise ValueError(f"{relative}: {field}{failure.message}")
        records.append(record)
    return records
