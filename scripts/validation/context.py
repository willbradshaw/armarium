"""Shared diagnostic and link helpers used by the individual rule groups."""

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from .parsing import Diagnostic, Page, Resolver, link_target


@dataclass(slots=True)
class ValidationContext:
    pages: dict[str, Page]
    resolver: Resolver
    campaigns: set[str]
    errors: list[Diagnostic] = field(default_factory=list)

    def report(
        self, page: Page, rule: str, message: str, *,
        field: str | None = None, line: int | None = None,
    ) -> None:
        self.errors.append(Diagnostic(page.path, rule, message, line, field))

    def require(
        self, page: Page, data: Mapping[object, object], names: Collection[str],
        *, prefix: str = "",
    ) -> None:
        for name in names:
            if name not in data:
                self.report(
                    page, "field.required", "Add this required property.",
                    field=prefix + name,
                )

    def target(self, value: object, page: Page) -> str | None:
        """Resolve a property quietly; link diagnostics are supplied separately."""
        if not isinstance(value, str):
            return None
        target = link_target(value)
        if target is None:
            return None
        return self.resolver.resolve(target, page.path)[0]

    def kind(self, page: Page) -> str | None:
        target = self.target(page.data.get("type"), page)
        if target and PurePosixPath(target).parent.as_posix() == "types":
            return PurePosixPath(target).stem
        return None

    def check_link(
        self, page: Page, value: object, field: str, *,
        kinds: Collection[str] = (), directory: str | None = None,
        nullable: bool = True,
    ) -> str | None:
        """Check property syntax and target category; return its canonical path."""
        if value is None and nullable:
            return None
        if not isinstance(value, str) or link_target(value) is None:
            expected = "Use a quoted canonical wikilink"
            self.report(
                page, "field.link", expected + (" or null." if nullable else "."),
                field=field,
            )
            return None

        target = self.target(value, page)
        if target is None:
            return None  # scan_links reports missing/ambiguous canonical targets.
        record = self.pages.get(target)
        if directory and (record is None or record.folder != directory):
            self.report(
                page, "link.kind", f"Link to a definition directly in {directory}/.",
                field=field,
            )
        if kinds and (
            record is None or record.is_template or record.is_definition
            or self.kind(record) not in kinds
        ):
            self.report(
                page, "link.kind", f"Link to an actual {'/'.join(sorted(kinds))} record.",
                field=field,
            )
        return target

    def check_link_list(
        self, page: Page, value: object, field: str, kinds: Collection[str],
    ) -> None:
        if value is None:
            return
        if not isinstance(value, list):
            self.report(
                page, "field.shape", "Expected a list of canonical wikilinks, or null.",
                field=field,
            )
            return
        for index, item in enumerate(value):
            self.check_link(page, item, f"{field}[{index}]", kinds=kinds, nullable=False)
