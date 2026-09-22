"""Vault-local Draft 2020-12 schemas with offline, confined references."""

import json
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import unquote, urlparse

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource, Unresolvable
from referencing.jsonschema import DRAFT202012

from armarium.lib import Diagnostic
from armarium.parse import Note


class Resolver(Protocol):
    """Public resolver methods used during offline schema preflight."""

    def lookup(self, ref: str) -> Any:
        """Return contents and the resolver for a resolved reference."""
        ...

    def in_subresource(self, resource: Resource[Any]) -> "Resolver":
        """Enter a child schema's identifier scope."""
        ...


class Schemas:
    """Load schemas from this vault only; no fallback or network retrieval."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "reference/schemas"

    def read(self, path: Path) -> Any:
        """Read and meta-validate a schema inside the schema directory."""
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
        """Resolve file URIs locally; refuse remote schema fetching."""
        parsed = urlparse(uri)
        if parsed.scheme != "file" or parsed.netloc:
            raise NoSuchResource(uri)
        return Resource.from_contents(
            self.read(Path(unquote(parsed.path))), default_specification=DRAFT202012
        )

    def registry(self, path: Path) -> Registry[Any]:
        """Check every schema reference, even in instance branches not exercised."""
        resource = Resource.from_contents(
            self.read(path), default_specification=DRAFT202012
        )
        registry: Registry[Any] = Registry(retrieve=self.retrieve)  # type: ignore[call-arg]
        registry = registry.with_resource(path.as_uri(), resource).crawl()
        seen: set[tuple[str, str]] = set()

        def visit(part: Resource[Any], resolver: Resolver, base: str) -> None:
            identifier = part.id()
            if identifier:
                from urllib.parse import urljoin

                base = urljoin(base, identifier)
            resolver = resolver.in_subresource(part)
            contents = part.contents
            if isinstance(contents, dict):
                for key in ("$ref", "$dynamicRef"):
                    reference = contents.get(key)
                    if isinstance(reference, str) and (base, reference) not in seen:
                        seen.add((base, reference))
                        located = resolver.lookup(reference)
                        visit(
                            Resource.from_contents(
                                located.contents, default_specification=DRAFT202012
                            ),
                            located.resolver,
                            base,
                        )
            for child in part.subresources():
                visit(child, resolver, base)

        visit(resource, registry.resolver(path.as_uri()), path.as_uri())
        return registry

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
            registry = self.registry(path)
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
