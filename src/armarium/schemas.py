"""Vault-local Draft 2020-12 schemas with offline, confined references."""

import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource, Unresolvable
from referencing.jsonschema import DRAFT202012

from armarium.lib import Diagnostic
from armarium.parse import Note


class Schemas:
    """Validate notes with this vault's lowercase <type>.schema.json files.

    Attributes:
        root: Absolute vault path used to label diagnostics.
        directory: The vault's reference/schemas directory.
    """

    def __init__(self, root: Path) -> None:
        """Select a vault without reading or creating any files.

        Args:
            root: Absolute or working-directory-relative vault path.

        Returns:
            None: Initialize the vault and schema directory paths.
        """
        self.root = root.absolute()
        self.directory = self.root / "reference/schemas"

    def read(self, path: Path) -> Any:
        """Read a local JSON schema and check its Draft 2020-12 syntax.

        Args:
            path: Schema file path, relative to the working directory or absolute.

        Returns:
            Any: The schema object or boolean. An omitted $schema defaults to
                Draft 2020-12; an explicit different dialect is rejected.

        Raises:
            OSError: The schema cannot be read.
            ValueError: The path escapes reference/schemas, JSON is invalid or
                the declared dialect is unsupported.
            SchemaError: The schema fails Draft 2020-12 meta-validation.
        """
        if not self.directory.resolve().is_relative_to(
            self.root.resolve()
        ) or not path.resolve().is_relative_to(self.directory.resolve()):
            raise ValueError("schema reference escapes reference/schemas")
        data = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(data)
        if (
            isinstance(data, dict)
            and data.get("$schema", "https://json-schema.org/draft/2020-12/schema")
            != "https://json-schema.org/draft/2020-12/schema"
        ):
            raise ValueError("schema must use Draft 2020-12")
        return data

    def retrieve(self, uri: str) -> Resource[Any]:
        """Retrieve a referenced schema using only a confined local file URI.

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
        return Resource.from_contents(
            self.read(Path(unquote(parsed.path))), default_specification=DRAFT202012
        )

    def validate(self, note: Note) -> tuple[bool, list[Diagnostic]]:
        """Validate a typed note and report schema coverage and failures.

        Args:
            note: Parsed note inside this vault with a canonical declared type.

        Returns:
            tuple[bool, list[Diagnostic]]: Whether a schema was found, plus
                findings. Missing schemas return False and a schema.unsupported
                warning. Found schemas return True with schema.instance errors
                for invalid note data or schema.invalid for schema/read/reference
                failures. Successful validation returns True and an empty list.
                References are resolved as validation encounters them; this does
                not audit unused branches of the schema. No files are modified.

        Raises:
            ValueError: The note has no canonical type or lies outside the vault.
        """
        kind = note.kind
        if kind is None:
            raise ValueError("schema validation requires a canonical note type")
        path = self.directory / f"{kind.lower()}.schema.json"
        relative = note.path.absolute().relative_to(self.root).as_posix()
        if not path.exists():
            return False, [
                Diagnostic(
                    relative,
                    "schema.unsupported",
                    f"no vault-local schema for {kind}; validation is partial",
                    severity="warning",
                )
            ]
        try:
            schema = self.read(path)
            resource = Resource.from_contents(schema, default_specification=DRAFT202012)
            registry: Registry[Any] = Registry(retrieve=self.retrieve)  # type: ignore[call-arg]
            registry = registry.with_resource(path.as_uri(), resource)
            validator = Draft202012Validator(
                {"$ref": path.as_uri()},
                registry=registry,
                format_checker=FormatChecker(),
            )
            errors = sorted(
                validator.iter_errors(
                    {"frontmatter": note.frontmatter, "body": note.body}
                ),
                key=lambda e: str(list(e.absolute_path)),
            )
            return True, [
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
            return True, [Diagnostic(relative, "schema.invalid", str(exc))]
