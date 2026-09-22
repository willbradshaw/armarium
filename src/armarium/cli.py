"""Command-line adapter for read-only single-file Markdown validation."""

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from armarium.validate import validate_markdown

logger = logging.getLogger(__name__)


class _LogFormatter(logging.Formatter):
    """Format local timestamps to hundredths of a second."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Render a log record's creation time.

        Args:
            record: Record whose timestamp should be formatted.
            datefmt: Optional explicit strftime format, overriding the default.

        Returns:
            str: Local time as YYYY-MM-DD HH:MM:SS.SS, or the requested format.
        """
        timestamp = super().formatTime(record, datefmt or "%Y-%m-%d %H:%M:%S")
        return timestamp if datefmt else f"{timestamp}.{int(record.msecs) // 10:02d}"


def _configure_logging() -> None:
    """Configure this command's logger to emit timestamped messages to stderr.

    Returns:
        None: Replace this logger's handlers so repeated main calls do not
            duplicate output. Other application loggers are left unchanged.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(_LogFormatter("[%(asctime)s] %(levelname)s: %(message)s"))
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command arguments separately from command execution.

    Args:
        argv: Arguments without the executable name, or None to read sys.argv.

    Returns:
        argparse.Namespace: Selected command, Markdown path and optional vault.

    Raises:
        SystemExit: Argparse exits with 0 for help or 2 for invalid arguments.
    """
    parser = argparse.ArgumentParser(prog="armarium")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser(
        "validate",
        help="validate one Markdown file",
        description=(
            "Parse and schema-validate one Markdown file without changing it. "
            "Missing types are errors; templates are skipped after parsing. "
            "Missing schemas produce partial-coverage warnings. Directory and "
            "vault-wide checks are not supported yet."
        ),
        epilog=(
            "Exit codes: 0 no errors (including skips and warnings), "
            "1 validation errors, 2 invalid invocation. "
            "Timestamped diagnostics and counts are logged to stderr."
        ),
    )
    command.add_argument("path", type=Path, help="Markdown file to validate")
    command.add_argument("--vault", type=Path, help="explicit vault directory")
    return parser.parse_args(argv)


def main() -> int:
    """Run the command from process arguments and log its validation result.

    Returns:
        int: 0 for no validation errors, including explicit skips and partial
            coverage; 1 for validation errors; 2 for invalid target/vault paths
            or I/O failures outside note parsing. Findings use their severity;
            counts use INFO. Logs go to standard error.

    Raises:
        SystemExit: Argument parsing exits with 0 for help or 2 for usage errors.
    """
    args = parse_args()
    _configure_logging()
    try:
        result = validate_markdown(args.path, args.vault)
    except (ValueError, OSError) as exc:
        logger.error("%s", exc)
        return 2
    levels = {"error": logging.ERROR, "warning": logging.WARNING, "info": logging.INFO}
    for diagnostic in result.diagnostics:
        location = diagnostic.path
        if diagnostic.line:
            location += f":{diagnostic.line}"
        if diagnostic.field:
            location += f" [{diagnostic.field}]"
        logger.log(
            levels[diagnostic.severity],
            "%s: %s: %s",
            location,
            diagnostic.rule,
            diagnostic.message,
        )
    logger.info(
        "%s checked, %s skipped, %s unsupported",
        result.checked,
        result.skipped,
        result.unsupported,
    )
    return int(result.failed)


if __name__ == "__main__":
    raise SystemExit(main())
