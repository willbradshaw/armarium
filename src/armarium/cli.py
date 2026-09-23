"""Command-line adapter for read-only Markdown validation."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from armarium.lib import ValidationError
from armarium.logging import configure_logging
from armarium.validate import validate


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command arguments separately from command execution.

    Args:
        argv: Arguments without the executable name, or None to read sys.argv.

    Returns:
        argparse.Namespace: Selected command, file or directory path, and
            optional vault.

    Raises:
        SystemExit: Argparse exits with 0 for help or 2 for invalid arguments.
    """
    parser = argparse.ArgumentParser(prog="armarium")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser(
        "validate",
        help="validate a Markdown file or directory",
        description=(
            "Parse and schema-validate a single Markdown file, or all Markdown "
            "files within a directory. Excludes Markdown files outside valid "
            "Obsidian vaults; single-file mode will fail if outside a vault."
        ),
    )
    command.add_argument(
        "path", type=Path, help="Markdown file or directory to validate"
    )
    command.add_argument("--vault", type=Path, help="explicit vault directory")
    return parser.parse_args(argv)


def main() -> None:
    """Run the command from process arguments and log its validation result.

    Raises:
        ValidationError: One or more files failed validation, after reporting
            all diagnostics and coverage counts.
        SystemExit: Argument parsing exits with 0 for help or 2 for usage errors.
    """
    args = parse_args()
    configure_logging()
    result = validate(args.path, args.vault)
    result.report()
    if result.failed:
        failed_files = result.failed_files
        noun = "file" if failed_files == 1 else "files"
        raise ValidationError(f"{failed_files} {noun} failed validation")


if __name__ == "__main__":
    main()
