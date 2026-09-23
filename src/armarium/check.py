"""Contextual checks for a selected note and its direct dependencies."""

from armarium.index import VaultIndex
from armarium.lib import Diagnostic, iter_wikilinks
from armarium.parse import Note


def check_links(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Check links in frontmatter strings and every Markdown body line.

    Walk nested metadata here so link errors retain their field/list locations.
    Body lines are scanned as written, including inline and fenced code.

    Args:
        note: Selected note inside the indexed vault.
        index: Whole-vault file index and lazy note cache for this run.

    Returns:
        list[Diagnostic]: Findings attributed to the selected note, with metadata
            fields or body source lines. Unrelated notes are not parsed. Heading
            and block existence, query execution and ordinary URLs are excluded.
    """
    path = note.path.relative_to(index.root).as_posix()
    # Pop metadata first, then body lines in source order. Reverse children when
    # adding them to the stack so nested mappings and lists retain their order.
    pending: list[tuple[str, int, object]] = [
        ("", number, text)
        for number, text in reversed(
            list(enumerate(note.body.splitlines(), note.body_start_line))
        )
    ]
    pending.append(("", 0, note.frontmatter))
    diagnostics: list[Diagnostic] = []
    while pending:
        field, line, value = pending.pop()
        if isinstance(value, dict):
            pending.extend(
                (f"{field}.{key}" if field else key, 0, item)
                for key, item in reversed(value.items())
            )
            continue
        if isinstance(value, list):
            pending.extend(
                (f"{field}.{number}", 0, value[number])
                for number in reversed(range(len(value)))
            )
            continue
        if not isinstance(value, str):
            continue
        for target in iter_wikilinks(value):
            if isinstance(target, ValueError):
                diagnostics.append(
                    Diagnostic(path, "link.syntax", str(target), field, line)
                )
                continue
            resolved, rule = index.resolve(target, note.path)
            if rule:
                diagnostics.append(
                    Diagnostic(
                        path,
                        rule,
                        f"cannot uniquely resolve [[{target}]]; use a vault-relative path",
                        field,
                        line,
                    )
                )
            elif resolved is not None and resolved.suffix.lower() == ".md":
                _, failures = index.parse(resolved)
                if failures:
                    diagnostics.append(
                        Diagnostic(
                            path,
                            "link.malformed",
                            f"referenced note {resolved.relative_to(index.root)} cannot be parsed",
                            field,
                            line,
                        )
                    )
    return diagnostics
