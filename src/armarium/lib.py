"""Shared utilities and data types for Armarium."""

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from armarium.logging import logger

# -----------------------------------------------------------------------------
# Wikilink parsing
# -----------------------------------------------------------------------------

_WIKILINK = re.compile(r"\[\[([^\[\]\r\n]+)\]\]")


def parse_wikilink(value: object, *, canonical: bool = False) -> str:
    """Extract the file target from one complete wikilink.

    Args:
        value: Candidate wikilink, including its double brackets. Non-strings
            and text surrounding a wikilink are not accepted.
        canonical: Require a file target without a display alias or anchor.
            Use this for identity fields such as a note's declared type.

    Returns:
        str: The file target, with surrounding whitespace, display alias and
            anchor removed. A self-anchor such as ``[[#Heading]]`` returns an
            empty string when canonical is False. Paths and optional .md
            extensions are preserved; target existence is not checked.

    Raises:
        ValueError: The input is not one complete wikilink, its target is empty,
            or canonical is True and the link contains an alias or anchor.
    """
    if not isinstance(value, str):
        raise ValueError("wikilink must be a string")
    match = _WIKILINK.fullmatch(value)
    if match is None:
        raise ValueError("use [[target]] with balanced double brackets on one line")
    contents = match[1].replace("\\|", "|")
    if canonical and ("|" in contents or "#" in contents):
        raise ValueError(
            "canonical wikilinks cannot contain display aliases or anchors"
        )
    target = contents.split("|", 1)[0].split("#", 1)[0].strip()
    if not target and (canonical or not contents.startswith("#")):
        raise ValueError("wikilink target must not be empty")
    return target


def _find_wikilink_candidates(text: str) -> Iterator[str]:
    """Find wikilink candidates, retaining malformed delimiters for validation.

    Args:
        text: Text to scan. The caller decides which Markdown regions are prose
            or executable queries and which are illustrative code.

    Yields:
        str: Candidate text, including unmatched delimiters, nested openers and empty
            links. A new opener recovers scanning after an unclosed link,
            preserving later links.
    """
    start: int | None = None
    for match in re.finditer(r"\[\[|\]\]", text):
        if match[0] == "[[":
            if start is not None:
                yield text[start : match.start()]
            start = match.start()
        elif start is None:
            yield match[0]
        else:
            yield text[start : match.end()]
            start = None
    if start is not None:
        yield text[start:]


def iter_wikilinks(text: str) -> Iterator[str | ValueError]:
    """Parse links in text, returning syntax errors without stopping the scan.

    Args:
        text: Text to scan. The caller excludes illustrative code or other
            regions where wikilink syntax should not be interpreted.

    Yields:
        str | ValueError: The parsed file target or the ValueError explaining
            invalid syntax.
            A valid self-anchor has an empty-string target. Errors are yielded
            as data, not raised, so later links are still parsed.
    """
    for candidate in _find_wikilink_candidates(text):
        try:
            target = parse_wikilink(candidate)
        except ValueError as exc:
            yield exc
        else:
            yield target


# -----------------------------------------------------------------------------
# Diagnostics and validation results
# -----------------------------------------------------------------------------


@dataclass(frozen=True, order=True)
class Diagnostic:
    """Describe one problem or informational finding.

    Parsing and validation return these records to their caller. The CLI reports
    them for a person; directory scans collect them so one bad file does not stop
    the scan. For example, malformed YAML produces a ``parse.invalid`` error.

    Attributes:
        path: File path relative to the selected vault.
        rule: Stable identifier for the check, such as ``parse.invalid``.
        message: Human-readable explanation of the finding.
        field: Metadata field path, if known; otherwise an empty string.
        line: One-based source-file line, or 0 when no line is known.
        severity: Error, warning or info. Only errors make validation fail.
    """

    path: str
    rule: str
    message: str
    field: str = ""
    line: int = 0
    severity: Literal["error", "warning", "info"] = "error"

    def report(self) -> None:
        """Log this finding with its severity and available source location."""
        levels = {
            "error": logging.ERROR,
            "warning": logging.WARNING,
            "info": logging.INFO,
        }
        location = self.path
        if self.line:
            location += f":{self.line}"
        if self.field:
            location += f" [{self.field}]"
        logger.log(
            levels[self.severity], "%s: %s: %s", location, self.rule, self.message
        )


@dataclass
class Result:
    """Accumulate findings and coverage counts for one validation run.

    Attributes:
        diagnostics: Findings collected by the checks, owned by this result.
        checked: Number of records checked.
        skipped: Number of files deliberately excluded from record checks.
        unsupported: Checked records without an available type schema; these
            can still receive checks that do not require a schema.
    """

    diagnostics: list[Diagnostic] = field(default_factory=list)
    checked: int = 0
    skipped: int = 0
    unsupported: int = 0

    def report(self) -> None:
        """Report each finding in order, then log coverage counts at INFO."""
        for diagnostic in self.diagnostics:
            diagnostic.report()
        logger.info(
            "%s checked, %s skipped, %s unsupported",
            self.checked,
            self.skipped,
            self.unsupported,
        )

    @property
    def failed_files(self) -> int:
        """Count distinct files with validation errors.

        Returns:
            int: Number of distinct diagnostic paths with error severity.
                Multiple errors in one file count once; warnings and info
                findings do not contribute.
        """
        return len({d.path for d in self.diagnostics if d.severity == "error"})

    @property
    def failed(self) -> bool:
        """Report whether the accumulated findings include an error.

        Returns:
            bool: True if any diagnostic has error severity. Warnings, info
                findings and coverage counts alone do not fail validation.
        """
        return any(d.severity == "error" for d in self.diagnostics)


# -----------------------------------------------------------------------------
# Vault discovery
# -----------------------------------------------------------------------------


def find_vault(path: Path, explicit: Path | None = None) -> Path:
    """Find the nearest enclosing vault or check an explicit vault boundary.

    Args:
        path: Target file or directory, absolute or relative to the working
            directory. The target need not exist yet.
        explicit: Optional vault directory. Explicit selection does not require
            structural markers, so incomplete vaults can still be checked.

    Returns:
        Path: Resolved vault directory. Inference requires reference/types and
            campaigns directories; a repository marker alone is insufficient.

    Raises:
        ValueError: No vault can be inferred, the explicit root is not a
            directory, or the target resolves outside the selected vault.
    """
    target = path.absolute()
    if explicit is not None:
        root = explicit.resolve()
        if not root.is_dir() or not target.resolve().is_relative_to(root):
            raise ValueError("target must be inside the selected vault directory")
        return root
    # Infer from the target's location before resolving symlinks, so an escaping
    # link cannot silently select a different vault around its destination.
    for candidate in (target, *target.parents):
        if (candidate / "reference/types").is_dir() and (
            candidate / "campaigns"
        ).is_dir():
            root = candidate.resolve()
            if not target.resolve().is_relative_to(root):
                raise ValueError("target escapes the inferred vault")
            return root
    raise ValueError("cannot infer vault; supply --vault PATH")


def find_files(root: Path) -> list[Path]:
    """List visible regular files below a directory in deterministic path order.

    Args:
        root: Directory to traverse. A symlink as the starting root is rejected.

    Returns:
        list[Path]: Sorted file paths retaining the root's absolute or relative
            form. Includes all file extensions. Hidden entries, __pycache__,
            node_modules and all descendant symlinks are excluded.

    Raises:
        ValueError: The root is a symlink or is not a directory.
        OSError: A directory cannot be read.
    """
    if root.is_symlink() or not root.is_dir():
        raise ValueError("file discovery requires a real directory")
    found: list[Path] = []
    pending = [root]
    while pending:
        for path in pending.pop().iterdir():
            if path.name.startswith(".") or path.is_symlink():
                continue
            if path.is_dir():
                if path.name not in {"__pycache__", "node_modules"}:
                    pending.append(path)
            elif path.is_file():
                found.append(path)
    return sorted(found)
