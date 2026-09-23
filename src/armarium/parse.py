"""Safe frontmatter parsing with duplicate detection and JSON normalization."""

import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import MappingNode

from armarium.lib import Diagnostic, parse_wikilink


class FrontmatterLoader(yaml.SafeLoader):
    """Load safe YAML frontmatter with unique keys and JSON-compatible values."""

    def construct_mapping(self, node: MappingNode, deep: bool = False) -> Any:
        """Construct a YAML mapping after checking its keys for duplicates.

        Args:
            node: YAML mapping node supplied by PyYAML.
            deep: Whether PyYAML should recursively construct nested values now.

        Returns:
            dict[Any, Any]: The mapping constructed by SafeLoader.

        Raises:
            ValueError: A key is not a scalar string representation.
            yaml.constructor.ConstructorError: A mapping contains duplicate keys.
        """
        seen: set[str] = set()
        for key, _ in node.value:
            if not isinstance(key.value, str):
                raise ValueError("frontmatter mapping keys must be strings")
            if key.value in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key: {key.value}", key.start_mark
                )
            seen.add(key.value)
        return super().construct_mapping(node, deep=deep)

    def get_single_data(self) -> Any:
        """Load and normalize one YAML document after constructing all aliases.

        Returns:
            Any: JSON-compatible metadata with ISO date/timestamp strings, or
                None for an empty document. The note parser checks that the
                top-level value is a mapping.

        Raises:
            yaml.YAMLError: The document is invalid or contains duplicate keys.
            ValueError: A constructed value cannot be represented in JSON.
        """
        return self._normalize(super().get_single_data())

    def _normalize(self, value: Any, ancestors: frozenset[int] = frozenset()) -> Any:
        """Convert parsed YAML values into JSON-compatible schema input.

        Args:
            value: A value produced by the safe YAML loader.
            ancestors: Container identities on the current recursion path. Callers
                should leave this empty; recursive calls use it to detect cycles.

        Returns:
            Any: A JSON-compatible value with dates/timestamps converted to ISO
                strings and dictionaries/lists copied recursively. The input is
                not modified.

        Raises:
            ValueError: A cycle, non-string mapping key, nonfinite float or other
                value that JSON cannot represent is encountered.
        """
        # YAML recognizes date scalars automatically; JSON schemas expect strings.
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, (dict, list)):
            # Track only the active path: two siblings may legitimately share a YAML
            # alias. A reference back to an ancestor is a cycle JSON cannot encode.
            if id(value) in ancestors:
                raise ValueError("recursive YAML aliases are not JSON-compatible")
            ancestors = ancestors | {id(value)}
            if isinstance(value, list):
                return [self._normalize(item, ancestors) for item in value]
            # JSON object keys must be strings; coercing keys would hide bad input
            # and could collapse distinct YAML keys into the same JSON key.
            if any(not isinstance(key, str) for key in value):
                raise ValueError("frontmatter mapping keys must be strings")
            return {
                key: self._normalize(item, ancestors) for key, item in value.items()
            }
        if value is None or isinstance(value, (str, bool, int)):
            return value
        # YAML accepts NaN and infinities, but they are not standard JSON numbers.
        if isinstance(value, float) and math.isfinite(value):
            return value
        raise ValueError("frontmatter contains a non-JSON YAML value")


@dataclass(frozen=True)
class Note:
    """A note's parsed metadata, Markdown body and source location.

    Attributes:
        path: Source Markdown file path.
        frontmatter: JSON-compatible YAML metadata, or an empty mapping when
            the note has no frontmatter.
        body: Markdown after the closing frontmatter delimiter, or the entire
            file when frontmatter is absent.
        body_start_line: One-based source-file line at which body begins. This
            is 1 without frontmatter. A check at one-based body line N reports
            source line ``body_start_line + N - 1``. For an empty body, this is
            the line immediately after the closing delimiter.
    """

    path: Path
    frontmatter: dict[str, Any]
    body: str
    body_start_line: int

    @property
    def parsed_type(self) -> str | None:
        """Return the declared record type name without resolving its target.

        Returns:
            str | None: The final path component of the canonical type wikilink,
                without an optional .md extension, or None if type is absent or
                malformed. For example, ``[[types/Content.md]]`` declares Content.
                Whether the target is the correct type definition is a contextual
                check.
        """
        # Missing/invalid type is classified by record validation; other callers
        # of the shared parser receive its ValueError directly.
        try:
            target = parse_wikilink(self.frontmatter.get("type"), canonical=True)
        except ValueError:
            return None
        return target.removesuffix(".md").rsplit("/", 1)[-1] if target else None

    @classmethod
    def parse(cls, path: Path, root: Path) -> tuple["Note | None", list[Diagnostic]]:
        """Read a Markdown note, returning either its contents or an error report.

        Args:
            path: Markdown file inside root. Both paths must use the same absolute
                or relative form so a vault-relative diagnostic path can be formed.
            root: Vault directory used to label errors with relative file paths.

        Returns:
            tuple[Note | None, list[Diagnostic]]: A pair of (note, diagnostics).
                Success returns a Note and an empty list. Read, YAML and normalization
                failures return None and a Diagnostic with rule ``parse.invalid``.
                A Diagnostic is data describing the failure, not an exception: the
                caller can report it and keep checking other files. This function
                neither prints nor changes the source file.

        Raises:
            ValueError: path is not lexically inside root (a caller contract error).
        """
        relative = path.relative_to(root).as_posix()
        try:
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError("note escapes the vault boundary")
            text = path.read_text(encoding="utf-8-sig")
            lines = text.splitlines(keepends=True)
            if not lines or lines[0].strip() != "---":
                return cls(path, {}, text, 1), []
            end = next(
                (i for i in range(1, len(lines)) if lines[i].strip() == "---"), None
            )
            if end is None:
                raise ValueError("frontmatter has no closing --- delimiter")
            data = yaml.load("".join(lines[1:end]), Loader=FrontmatterLoader)
            if data is None:
                data = {}
            if not isinstance(data, dict):
                raise ValueError("frontmatter must be a mapping")
            return cls(path, data, "".join(lines[end + 1 :]), end + 2), []
        except (
            OSError,
            UnicodeError,
            yaml.YAMLError,
            ValueError,
            RecursionError,
        ) as exc:
            # PyYAML counts from zero within the frontmatter slice. Add two for
            # one-based file lines and the opening --- delimiter omitted above.
            mark = getattr(exc, "problem_mark", None)
            return None, [
                Diagnostic(
                    relative,
                    "parse.invalid",
                    str(exc),
                    line=mark.line + 2 if mark else 0,
                )
            ]
