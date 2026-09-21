"""Frontmatter and Markdown parsing, independent of vault policy."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import PurePosixPath
import re

import yaml

from .schema import CAMPAIGN

# YAML may contain non-JSON values; field rules narrow known properties safely.
type Properties = dict[object, object]
type Resolution = tuple[str | None, str | None, str | None]


@dataclass(frozen=True, slots=True)
class Diagnostic:
    path: str
    rule: str
    message: str
    line: int | None = None
    field: str | None = None

    def __str__(self) -> str:
        location = self.path + (f":{self.line}" if self.line else "")
        location += f" ({self.field})" if self.field else ""
        return f"{location}: [{self.rule}] {self.message}"


@dataclass(slots=True)
class Page:
    path: str
    text: str
    data: Properties = field(default_factory=dict)
    body: str = ""
    body_line: int = 1
    has_frontmatter: bool = False

    @property
    def parts(self) -> tuple[str, ...]:
        return PurePosixPath(self.path).parts

    @property
    def folder(self) -> str:
        return PurePosixPath(self.path).parent.as_posix()

    @property
    def stem(self) -> str:
        return PurePosixPath(self.path).stem

    @property
    def is_template(self) -> bool:
        return self.parts[0] == "templates"

    @property
    def is_definition(self) -> bool:
        return self.parts[0] in {"types", "statuses"}

    @property
    def campaign(self) -> str | None:
        scope = self.parts[0]
        return scope if CAMPAIGN.fullmatch(scope) else None


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate keys at every depth, including YAML merge collisions."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> Properties:
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in result
            except TypeError as exc:
                raise yaml.constructor.ConstructorError(
                    None, None, "mapping keys must be scalars", key_node.start_mark
                ) from exc
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key {key!r}", key_node.start_mark
                )
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def parse_page(path: str, text: str) -> tuple[Page, list[Diagnostic]]:
    page = Page(path, text, body=text)
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip("\ufeff \r\n") != "---":
        return page, []
    page.has_frontmatter = True
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return page, [Diagnostic(path, "yaml.syntax", "Close frontmatter with ---.", 1)]
    page.body = "".join(lines[end + 1:])
    page.body_line = end + 2
    try:
        data = yaml.load("".join(lines[1:end]), Loader=UniqueLoader)
        if data is not None and not isinstance(data, dict):
            return page, [Diagnostic(path, "yaml.mapping", "Frontmatter must be a mapping.", 2)]
        page.data = data or {}
    except (yaml.YAMLError, ValueError) as exc:
        mark = getattr(exc, "problem_mark", None)
        rule = "yaml.duplicate" if "duplicate key" in str(exc) else "yaml.syntax"
        return page, [Diagnostic(path, rule, getattr(exc, "problem", None) or str(exc),
                                 mark.line + 2 if mark else 2)]
    return page, []


@dataclass(frozen=True, slots=True)
class Link:
    target: str
    line: int
    raw: str


LINK = re.compile(r"!?\[\[([^\[\]\n]+)\]\]")


def link_target(value: str) -> str | None:
    match = LINK.fullmatch(value.strip())
    if not match:
        return None
    return re.split(r"(?:\\)?\|", match[1], maxsplit=1)[0].split("#", 1)[0].strip()


def markdown_lines(text: str) -> Iterator[tuple[int, str, bool]]:
    """Yield prose and executable Dataview; omit fenced/inline examples.

    Only dataview/dataviewjs fences and inline `= ...` / `$= ...` are
    executable. Ordinary inline code and other fenced blocks are examples.
    """
    fence = None
    executable = False
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if match:
            marker, info = match.groups()
            if fence is None:
                fence = marker
                executable = info.strip().lower() in {"dataview", "dataviewjs"}
                continue
            if marker[0] == fence[0] and len(marker) >= len(fence) and not info.strip():
                fence = None
                executable = False
                continue
        if fence is not None:
            if executable:
                yield number, line, False
            continue
        line = re.sub(r"(`+)(.*?)\1", lambda m: m[2] if m[2].lstrip().startswith(("=", "$=")) else "", line)
        yield number, line, True


def scan_links(page: Page) -> tuple[list[Link], list[Diagnostic]]:
    links, errors = [], []
    # Frontmatter is scanned even when YAML parsing failed.
    prefix = page.text.splitlines()[:page.body_line - 1] if page.body_line > 1 else []
    lines = [(n, line, False) for n, line in enumerate(prefix, 1)]
    lines += [(n + page.body_line - 1, line, prose)
              for n, line, prose in markdown_lines(page.body)]
    for number, line, prose in lines:
        for match in LINK.finditer(line):
            raw = match[1]
            target = link_target(match[0])
            if not raw.split("|", 1)[0].strip():
                errors.append(Diagnostic(page.path, "link.syntax", "Provide a target or self-anchor.", number))
            elif target is not None:
                links.append(Link(target, number, match[0]))
            if prose and re.search(r"(?<!\\)\|", raw) and "|" in LINK.sub("", line):
                errors.append(Diagnostic(page.path, "link.table-pipe",
                                         "Escape display-alias pipes in tables as \\|.", number))
        remainder = LINK.sub("", line)
        if "[[" in remainder or "]]" in remainder:
            errors.append(Diagnostic(page.path, "link.syntax", "Malformed wikilink; use [[target|display]].", number))
    return links, errors


class Resolver:
    def __init__(self, files: set[str], pages: dict[str, Page]) -> None:
        self.files = files
        self.names: dict[str, list[str]] = {}
        self.aliases: dict[str, list[str]] = {}
        for path in sorted(files):
            self.names.setdefault(PurePosixPath(path).name, []).append(path)
            if path.endswith(".md"):
                self.names.setdefault(PurePosixPath(path).stem, []).append(path)
        for path, page in pages.items():
            aliases = page.data.get("aliases")
            if isinstance(aliases, list):
                for alias in aliases:
                    if isinstance(alias, str) and alias:
                        self.aliases.setdefault(alias, []).append(path)

    def resolve(self, target: str, current: str) -> Resolution:
        if not target:
            return current, None, None
        if target.startswith("/") or ".." in target.split("/"):
            return None, "link.path", "Use a path relative to the vault root, without '..'."
        if "/" in target:
            matches = [p for p in (target, target + ".md") if p in self.files]
        else:
            matches = self.names.get(target, [])
        if len(matches) == 1:
            return matches[0], None, None
        if len(matches) > 1:
            return None, "link.ambiguous", f"Qualify {target!r}: {', '.join(matches)}."
        if target in self.aliases:
            return None, "link.alias", f"{target!r} is an alias; link to {', '.join(self.aliases[target])} with a display alias."
        return None, "link.missing", f"Target {target!r} does not exist in the vault."
