"""Contextual checks for a selected note and its direct dependencies."""

from armarium.index import VaultIndex
from armarium.lib import (
    Diagnostic,
    iter_markdown_lines,
    iter_text_values,
    iter_wikilinks,
)
from armarium.parse import Note


def check_links(note: Note, index: VaultIndex) -> list[Diagnostic]:
    """Check link syntax, file resolution and referenced-note readability.

    Args:
        note: Selected note inside the indexed vault.
        index: Whole-vault file index and lazy note cache for this run.

    Returns:
        list[Diagnostic]: Findings attributed to the selected note, with metadata
            fields or body source lines. Unrelated notes are not parsed. Heading
            and block existence, query execution and ordinary URLs are excluded.
    """
    path = note.path.relative_to(index.root).as_posix()
    texts = [(field, 0, text) for field, text in iter_text_values(note.frontmatter)]
    texts.extend(
        ("", note.body_start_line + number - 1, text)
        for number, text in iter_markdown_lines(note.body)
    )
    diagnostics: list[Diagnostic] = []
    for field, line, text in texts:
        for target in iter_wikilinks(text):
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
