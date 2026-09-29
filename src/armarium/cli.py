"""Command-line adapters for creating and validating vaults and records."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from armarium.add import add_campaign
from armarium.content import SUBTYPES, add_content
from armarium.init import init_vault
from armarium.lib import find_vault
from armarium.logging import configure_logging, logger
from armarium.session import add_session
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
    content = additions.add_parser("content", help="create a Content record")
    content.add_argument("name", help="record name without .md")
    content.add_argument("--subtype", required=True, choices=SUBTYPES)
    content.add_argument(
        "--vault",
        type=Path,
        help="vault root; otherwise discover from the current directory",
    )
    content.add_argument(
        "--campaign",
        type=int,
        help="existing campaign number; default: current campaign, otherwise shared content",
    )
    content.add_argument(
        "--player", help="existing Player name or vault-relative path (PC only)"
    )
    session = additions.add_parser("session", help="create a Session record")
    session.add_argument(
        "--vault",
        type=Path,
        help="vault root; otherwise discover from the current directory",
    )
    session.add_argument(
        "--campaign",
        type=int,
        help="existing campaign number; default: current campaign",
    )
    session.add_argument(
        "--number",
        type=int,
        help="session number (1–999); default: largest existing number + 1",
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
    if args.command == "add":
        for option in ("number", "campaign"):
            value = getattr(args, option, None)
            if value is not None and value < 1:
                parser.error(f"--{option} must be positive")
        if args.addition == "session" and args.number is not None and args.number > 999:
            parser.error("--number must be between 1 and 999")
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
            if args.addition == "campaign":
                destination = add_campaign(args.vault, number=args.number)
            elif args.addition == "session":
                destination = add_session(
                    args.vault, campaign=args.campaign, number=args.number
                )
            else:
                destination = add_content(
                    args.name,
                    args.subtype,
                    args.vault,
                    campaign=args.campaign,
                    player=args.player,
                )
        except (OSError, ValueError) as exc:
            logger.error("Cannot add %s: %s", args.addition, exc)
            sys.exit(1)
        logger.info("New %s successfully created; validating", args.addition)
        result = validate(find_vault(destination))
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
            logger.error(
                "%s retained at %s for inspection",
                args.addition.capitalize(),
                destination,
            )
        sys.exit(1)
    if args.command in {"init", "add"}:
        logger.info("Validation completed successfully")


if __name__ == "__main__":
    main()
