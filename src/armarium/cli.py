"""Command-line adapters for vault creation and read-only validation."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from armarium.init import init_vault
from armarium.logging import configure_logging, logger
from armarium.validate import validate


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command arguments separately from command execution.

    Args:
        argv: Arguments without the executable name, or None to read sys.argv.

    Returns:
        argparse.Namespace: Selected command and path; validate also supplies
            an optional vault.

    Raises:
        SystemExit: Argparse exits with 0 for help or 2 for invalid arguments.
    """
    parser = argparse.ArgumentParser(prog="armarium")
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser(
        "init",
        help="create and validate a vault from the starter vault",
        description=(
            "Create and validate a single-campaign vault at a new path. The parent directory "
            "must exist; existing files and directories are never overwritten."
        ),
    )
    initialize.add_argument("path", type=Path, help="new vault directory")
    command = commands.add_parser(
        "validate",
        help="validate a Markdown file or directory",
        description=(
            "Validate a Markdown file, or all Markdown files within a directory, "
            "checking schemas, links and record context. Excludes files outside valid "
            "Obsidian vaults; single-file mode will fail if outside a vault."
        ),
    )
    command.add_argument(
        "path", type=Path, help="Markdown file or directory to validate"
    )
    command.add_argument("--vault", type=Path, help="explicit vault directory")
    return parser.parse_args(argv)


def main() -> None:
    """Run the selected command and log its result.

    Raises:
        SystemExit: Status 1 when vault creation fails or files fail validation.
            Validation reports all diagnostics and coverage counts before the
            final error line. Argument parsing exits with 0 for help or 2 for
            usage errors.
    """
    args = parse_args()
    configure_logging()
    if args.command == "init":
        try:
            destination = init_vault(args.path)
        except OSError as exc:
            logger.error("Cannot create vault at %s: %s", args.path, exc)
            sys.exit(1)
        result = validate(destination)
    else:
        result = validate(args.path, args.vault)
    result.report()
    if result.failed:
        failed_files = result.failed_files
        noun = "file" if failed_files == 1 else "files"
        logger.error("%s %s failed validation", failed_files, noun)
        if args.command == "init":
            logger.error("Vault retained at %s for inspection", destination)
        sys.exit(1)
    if args.command == "init":
        logger.info("Created vault at %s", destination)


if __name__ == "__main__":
    main()
