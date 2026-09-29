"""Command-line adapters for creating and validating vaults and records."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from armarium.add import add_campaign
from armarium.clue import add_clue
from armarium.content import SUBTYPES, add_content
from armarium.init import init_vault
from armarium.lib import find_vault
from armarium.logging import configure_logging, logger
from armarium.note import add_note
from armarium.parse import Record
from armarium.player import add_player
from armarium.session import add_session
from armarium.transcript import add_transcript
from armarium.validate import validate


def _clue_text_help(vault: Path | None) -> str:
    """Describe the selected vault's template text without making help fail.

    Show usable text as a quoted string with escaped newlines. Missing vaults,
    unreadable templates and invalid defaults are described explicitly. Escape
    percent signs because argparse interpolates help strings.
    """
    try:
        selected = vault.expanduser().resolve() if vault is not None else Path.cwd()
        root = find_vault(selected)
        if vault is not None and selected != root:
            raise ValueError("--vault must name the vault root")
        path = root / "reference/templates/Clue.md"
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError("template must be a regular file")
        template, _ = Record.parse(path, root)
        if template is None or template.frontmatter.type != "Clue":
            raise ValueError("cannot read a Clue template")
        text = template.frontmatter.get("text")
        default = (
            json.dumps(text, ensure_ascii=False)
            if isinstance(text, str) and text.strip()
            else "none; --text required"
        )
    except OSError, ValueError:
        default = "unavailable; select a vault with a readable Clue template"
    return f"nonblank clue text (default: {default})".replace("%", "%%")


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
        help="vault root (default: discovered from the current directory)",
    )
    campaign.add_argument(
        "--number",
        type=int,
        help="positive campaign number (default: largest existing number + 1)",
    )
    content = additions.add_parser("content", help="create a Content record")
    content.add_argument("name", help="record name without .md")
    content.add_argument("--subtype", required=True, choices=SUBTYPES)
    content.add_argument(
        "--vault",
        type=Path,
        help="vault root (default: discovered from the current directory)",
    )
    content.add_argument(
        "--campaign",
        type=int,
        help="campaign number within vault (default: current campaign directory, or shared content)",
    )
    content.add_argument(
        "--player", help="existing Player name or vault-relative path (PC only)"
    )
    player = additions.add_parser("player", help="create a Player record")
    player.add_argument("name", help="record name without .md")
    player.add_argument(
        "--vault",
        type=Path,
        help="vault root (default: discovered from the current directory)",
    )
    player.add_argument(
        "--campaign",
        type=int,
        help="campaign number within vault (default: current campaign directory)",
    )
    note = additions.add_parser("note", help="create a Note record")
    note.add_argument("name", help="record name without .md")
    note.add_argument(
        "--vault",
        type=Path,
        help="vault root (default: discovered from the current directory)",
    )
    note.add_argument(
        "--campaign",
        type=int,
        help="campaign number within vault (default: current campaign directory, or shared notes)",
    )
    session = additions.add_parser("session", help="create a Session record")
    session.add_argument(
        "--vault",
        type=Path,
        help="vault root (default: discovered from the current directory)",
    )
    session.add_argument(
        "--campaign",
        type=int,
        help="campaign number within vault (default: current campaign directory)",
    )
    session.add_argument(
        "--number",
        type=int,
        help="session number from 1 to 999 (default: largest existing number + 1)",
    )
    clue = additions.add_parser("clue", help="create a Clue record", add_help=False)
    clue.add_argument(
        "-h",
        "--help",
        action="store_true",
        dest="clue_help",
        help="show this help message and exit",
    )
    clue.add_argument(
        "--vault",
        type=Path,
        help="vault root (default: discovered from the current directory)",
    )
    clue.add_argument(
        "--campaign",
        type=int,
        help="campaign number within vault (default: current campaign directory)",
    )
    clue.add_argument(
        "--number",
        type=int,
        help="clue number from 1 to 9999 (default: largest existing number + 1)",
    )
    clue_text = clue.add_argument("--text", help="nonblank clue text")
    transcript = additions.add_parser(
        "transcript", help="create a Transcript for an existing Session"
    )
    transcript.add_argument(
        "session", help="unambiguous Session name or vault-relative path"
    )
    transcript.add_argument(
        "--body-file",
        type=Path,
        required=True,
        help="UTF-8 Markdown file containing transcript body",
    )
    transcript.add_argument(
        "--vault",
        type=Path,
        help="vault root (default: discovered from the current directory)",
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
    if args.command == "add" and args.addition == "clue" and args.clue_help:
        clue_text.help = _clue_text_help(args.vault)
        clue.print_help()
        parser.exit()
    if args.command == "add":
        for option in ("number", "campaign"):
            value = getattr(args, option, None)
            if value is not None and value < 1:
                parser.error(f"--{option} must be positive")
        if args.addition == "session" and args.number is not None and args.number > 999:
            parser.error("--number must be between 1 and 999")
        if args.addition == "clue" and args.number is not None and args.number > 9999:
            parser.error("--number must be between 1 and 9999")
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
            elif args.addition == "player":
                destination = add_player(args.name, args.vault, campaign=args.campaign)
            elif args.addition == "note":
                destination = add_note(args.name, args.vault, campaign=args.campaign)
            elif args.addition == "clue":
                destination = add_clue(
                    args.vault,
                    campaign=args.campaign,
                    number=args.number,
                    text=args.text,
                )
            elif args.addition == "session":
                destination = add_session(
                    args.vault, campaign=args.campaign, number=args.number
                )
            elif args.addition == "transcript":
                destination = add_transcript(args.session, args.body_file, args.vault)
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
