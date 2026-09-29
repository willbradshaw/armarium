"""Command-line adapters for vault and campaign creation and validation."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from armarium.add import add_campaign
from armarium.init import init_vault
from armarium.logging import configure_logging, logger
from armarium.validate import validate


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command arguments separately from command execution.

    Args:
        argv: Arguments without the executable name, or None to read sys.argv.

    Returns:
        argparse.Namespace: Selected command and its paths and options.

    Raises:
        SystemExit: Argparse exits with 0 for help or 2 for invalid arguments.
    """
    parser = argparse.ArgumentParser(prog="armarium")
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser(
        "init",
        help="create and validate a vault from the starter vault",
        description=(
            "Create and validate a single-campaign vault at a new path. Missing "
            "parent directories are created. Use --force to replace an existing directory."
        ),
    )
    initialize.add_argument("path", type=Path, help="new vault directory")
    initialize.add_argument(
        "--force",
        action="store_true",
        help="replace an existing directory and all its contents; refuse files and symlinks",
    )
    add = commands.add_parser("add", help="add to an existing vault")
    additions = add.add_subparsers(dest="addition", required=True)
    campaign = additions.add_parser("campaign", help="create a new campaign")
    campaign.add_argument(
        "--vault",
        type=Path,
        help="vault root; otherwise discover from the current directory",
    )
    campaign.add_argument(
        "--number",
        type=int,
        help="positive campaign number; default: largest existing number + 1",
    )
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
    args = parser.parse_args(argv)
    if args.command == "add" and args.number is not None and args.number < 1:
        parser.error("--number must be positive")
    return args


def main() -> None:
    """Run the selected command and log its result.

    Raises:
        SystemExit: Status 1 when creation fails or files fail validation.
            Creation reports validation warnings and errors; validate also reports
            informational diagnostics and coverage counts. Argument parsing
            exits with 0 for help or 2 for usage errors.
    """
    args = parse_args()
    configure_logging()
    if args.command == "init":
        try:
            logger.info(
                "Initializing new vault at %s", args.path.expanduser().resolve()
            )
            destination = init_vault(args.path, force=args.force)
        except OSError as exc:
            logger.error("Cannot create vault at %s: %s", args.path, exc)
            sys.exit(1)
        logger.info("New vault successfully initialized; validating")
        result = validate(destination)
    elif args.command == "add":
        try:
            destination = add_campaign(args.vault, number=args.number)
        except (OSError, ValueError) as exc:
            logger.error("Cannot add campaign: %s", exc)
            sys.exit(1)
        logger.info("New campaign successfully created; validating")
        result = validate(destination.parent.parent)
    else:
        result = validate(args.path, args.vault)
        result.report()
    if args.command in {"init", "add"}:
        for diagnostic in result.diagnostics:
            if diagnostic.severity != "info":
                diagnostic.report()
    if result.failed:
        failed_files = result.failed_files
        noun = "file" if failed_files == 1 else "files"
        logger.error("%s %s failed validation", failed_files, noun)
        if args.command == "init":
            logger.error("Vault retained at %s for inspection", destination)
        elif args.command == "add":
            logger.error("Campaign retained at %s for inspection", destination)
        sys.exit(1)
    if args.command in {"init", "add"}:
        logger.info("Validation completed successfully")


if __name__ == "__main__":
    main()
