"""Command-line adapter for read-only single-file Markdown validation."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from armarium.logging import configure_logging
from armarium.validate import validate_markdown


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
            "1 validation or execution errors, 2 invalid command arguments. "
            "UTC-timestamped diagnostics and counts are logged to stderr."
        ),
    )
    command.add_argument("path", type=Path, help="Markdown file to validate")
    command.add_argument("--vault", type=Path, help="explicit vault directory")
    return parser.parse_args(argv)


def main() -> int:
    """Run the command from process arguments and log its validation result.

    Returns:
        int: 0 for no validation errors, including explicit skips and partial
            coverage; 1 for validation errors. Execution exceptions propagate
            normally. Findings and counts are logged to standard error.

    Raises:
        SystemExit: Argument parsing exits with 0 for help or 2 for usage errors.
    """
    args = parse_args()
    configure_logging()
    result = validate_markdown(args.path, args.vault)
    result.report()
    return int(result.failed)


if __name__ == "__main__":
    raise SystemExit(main())
