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
    """Load schemas from this vault only; no fallback or network retrieval."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "reference/schemas"

    def read(self, path: Path) -> Any:
        """Read and meta-validate a schema inside the schema directory."""
        if not path.resolve().is_relative_to(self.directory.resolve()):
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
        """Resolve file URIs locally; refuse remote schema fetching."""
        parsed = urlparse(uri)
        if parsed.scheme != "file" or parsed.netloc:
            raise NoSuchResource(uri)
        return Resource.from_contents(
            self.read(Path(unquote(parsed.path))), default_specification=DRAFT202012
        )

    def validate(self, note: Note) -> tuple[bool, list[Diagnostic]]:
        """Return coverage and instance/schema errors for a declared record type."""
        assert note.kind is not None
        path = self.directory / f"{note.kind.lower()}.schema.json"
        relative = note.path.relative_to(self.root).as_posix()
        if not path.exists():
            return False, [
                Diagnostic(
                    relative,
                    "schema.unsupported",
                    f"no vault-local schema for {note.kind}; validation is partial",
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
        ) as exc:
            return True, [Diagnostic(relative, "schema.invalid", str(exc))]
