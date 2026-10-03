"""Vault-local Draft 2020-12 schemas with offline, confined references."""

import functools
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource, Unresolvable
from referencing.jsonschema import DRAFT202012

from armarium.lib import Diagnostic
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
        relative = record.path.absolute().relative_to(self.root).as_posix()
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
                validator.iter_errors(
                    {"frontmatter": dict(record.frontmatter), "body": record.body.text}
                ),
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
    relative = record.path.absolute().relative_to(root.absolute()).as_posix()
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
