"""Shared utilities and data types for Armarium."""

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
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


class ValidationError(Exception):
    """A completed validation run contains errors."""


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


class Findings:
    """Diagnostics collected for one file, all attributed to the same path."""

    def __init__(self, path: str) -> None:
        """Start an empty collection for one file.

        Args:
            path: The file's path relative to its vault, as reported.
        """
        self.path = path
        self.diagnostics: list[Diagnostic] = []

    def add(self, rule: str, message: str, field: str = "", line: int = 0) -> None:
        """Record one diagnostic against the file.

        Args:
            rule: Stable rule identifier such as ``history.order``.
            message: Human-readable explanation.
            field: Frontmatter location, if any.
            line: One-based source line, or 0 when none applies.
        """
        self.diagnostics.append(Diagnostic(self.path, rule, message, field, line))

    def diagnose(
        self, check: bool, rule: str, message: str, field: str = "", line: int = 0
    ) -> bool:
        """Record a diagnostic when a check fails.

        Args:
            check: Whether the problem is present.
            rule: Stable rule identifier such as ``history.order``.
            message: Human-readable explanation.
            field: Frontmatter location, if any.
            line: One-based source line, or 0 when none applies.

        Returns:
            bool: The check, so callers can stop when it held.
        """
        if check:
            self.add(rule, message, field, line)
        return check


@dataclass
@dataclass
class Result:
    """Accumulate findings and coverage counts for one validation run.

    Attributes:
        diagnostics: Findings collected by the checks, owned by this result.
        checked: Number of records checked.
        skipped: Number of files deliberately excluded from record checks.
        unsupported: Checked records without an available type schema. Each
            receives an error diagnostic and fails validation.
    """

    diagnostics: list[Diagnostic] = field(default_factory=list)
    checked: int = 0
    skipped: int = 0
    unsupported: int = 0

    def __add__(self, other: "Result") -> "Result":
        """Combine two validation results without modifying either operand.

        Args:
            other: Result to combine with this one.

        Returns:
            Result: A new result with sorted diagnostics and summed counts.
        """
        if not isinstance(other, Result):
            return NotImplemented
        return Result(
            diagnostics=sorted(self.diagnostics + other.diagnostics),
            checked=self.checked + other.checked,
            skipped=self.skipped + other.skipped,
            unsupported=self.unsupported + other.unsupported,
        )

    def add_context(
        self, context: str | Path, *, relative_to: str | Path | None = None
    ) -> "Result":
        """Prefix or rebase diagnostic paths without changing this result.

        Args:
            context: Directory path to prepend to each diagnostic.
            relative_to: Optional directory to express the resulting paths
                relative to. Use the same absolute or relative basis as context.

        Returns:
            Result: A new result with adjusted paths and unchanged counts.

        Raises:
            ValueError: A prefixed path is not beneath relative_to.
        """
        diagnostics = []
        for diagnostic in self.diagnostics:
            path = Path(context) / diagnostic.path
            if relative_to is not None:
                path = path.relative_to(relative_to)
            diagnostics.append(replace(diagnostic, path=path.as_posix()))
        return replace(self, diagnostics=diagnostics)

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


class VaultNotFoundError(ValueError):
    """No enclosing vault has the required discovery markers."""


def find_vault(path: Path) -> Path:
    """Find the nearest enclosing vault.

    Args:
        path: Target file or directory, absolute or relative to the working
            directory. The target need not exist yet.

    Returns:
        Path: Resolved vault directory. Inference requires reference/types and
            campaigns directories; a repository marker alone is insufficient.

    Raises:
        VaultNotFoundError: No enclosing vault has the discovery markers.
        ValueError: The target resolves outside the inferred vault.
    """
    target = path.absolute()
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
    raise VaultNotFoundError("cannot infer vault; supply --vault PATH")


def check_vault(path: Path, vault: Path) -> Path:
    """Check that a target is contained within an explicitly selected vault.

    Args:
        path: Target file or directory; it need not exist yet.
        vault: Selected vault directory. Structural discovery markers are not
            required, so incomplete vaults can still be checked.

    Returns:
        Path: Resolved vault root after checking containment, including symlinks.

    Raises:
        ValueError: The vault is not a directory or the target resolves outside it.
    """
    root = vault.resolve()
    if not root.is_dir() or not path.resolve().is_relative_to(root):
        raise ValueError("target must be inside the selected vault directory")
    return root


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
    found: list[Path] = []
    pending = [root]
    while pending:
        for path in find_children(pending.pop()):
            if path.is_dir():
                pending.append(path)
            elif path.is_file():
                found.append(path)
    return sorted(found)


def find_children(root: Path) -> list[Path]:
    """List visible immediate children using the shared traversal exclusions.

    Args:
        root: Real directory to inspect; a symlink root is rejected.

    Returns:
        list[Path]: Sorted files and directories, excluding hidden entries,
            symlinks and the __pycache__ and node_modules directories.

    Raises:
        ValueError: The root is a symlink or is not a directory.
        OSError: The directory cannot be read.
    """
    if root.is_symlink() or not root.is_dir():
        raise ValueError("file discovery requires a real directory")
    return sorted(
        path
        for path in root.iterdir()
        if not path.name.startswith(".")
        and not path.is_symlink()
        and not (path.is_dir() and path.name in {"__pycache__", "node_modules"})
    )


# Name of a campaign directory directly under campaigns/.
CAMPAIGN_NAME = re.compile(r"campaign_[0-9]+")


def find_campaign(path: Path, root: Path) -> str | None:
    """Identify a path's containing numeric campaign directory.

    Args:
        path: Record path within root, using the same absolute or relative form.
        root: Vault directory.

    Returns:
        str | None: campaign_N for a path under campaigns/campaign_N, otherwise
            None for shared or other vault paths.

    Raises:
        ValueError: The path is not inside root.
    """
    parts = path.relative_to(root).parts
    if len(parts) > 2 and parts[0] == "campaigns" and CAMPAIGN_NAME.fullmatch(parts[1]):
        return parts[1]
    return None
