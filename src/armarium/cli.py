"""Command-line adapters for creating and validating vaults and records."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from jsonschema.exceptions import SchemaError

from armarium.add import add_campaign, select_vault
from armarium.clue import add_clue
from armarium.content import add_content
from armarium.extensions import (
    content_subtypes,
    enable_extension,
    remove_extension,
    update_extension,
)
from armarium.find import find_records
from armarium.init import init_vault
from armarium.lib import SUBTYPES, find_vault
from armarium.logging import configure_logging, logger
from armarium.note import add_note
from armarium.player import add_player
from armarium.session import add_session
from armarium.trace import trace_outbound, trace_record
from armarium.transcript import add_transcript
from armarium.validate import validate


def _frontmatter_json(value: str) -> dict[str, object]:
    """Parse a strict JSON object, rejecting duplicate keys and nonfinite numbers."""

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, item in items:
            if key in result:
                raise ValueError(f"duplicate frontmatter key: {key}")
            result[key] = item
        return result

    def constant(value: str) -> object:
        raise ValueError(f"invalid JSON constant: {value}")

    try:
        data = json.loads(value, object_pairs_hook=pairs, parse_constant=constant)
        if not isinstance(data, dict):
            raise ValueError("frontmatter must be a JSON object")
        json.dumps(data, allow_nan=False)
        return data
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _jobs(value: str) -> int:
    """Parse a worker-process count of at least one."""
    try:
        jobs = int(value)
    except ValueError:
        jobs = 0
    if jobs < 1:
        raise argparse.ArgumentTypeError("jobs must be a whole number of at least 1")
    return jobs


def _subtype_choices(argv: Sequence[str] | None) -> tuple[tuple[str, ...] | None, str]:
    """Select Content subtypes for `add content` from the vault it targets.

    The vault is the one named by --vault, otherwise the one containing the
    current directory. Its enabled extensions may add subtypes to the core set.

    Args:
        argv: Arguments without the executable name, or None to read sys.argv.

    Returns:
        tuple[tuple[str, ...] | None, str]: The permitted subtypes and a note
            for the help text. Other commands, and add content outside a vault,
            get the core subtypes. When the vault's extensions cannot be loaded
            the choices are None, so creation reports the underlying error.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:2] != ["add", "content"]:
        return SUBTYPES, ""
    options = argparse.ArgumentParser(add_help=False, exit_on_error=False)
    options.add_argument("--vault", type=Path)
    try:
        root = select_vault(options.parse_known_args(arguments[2:])[0].vault)
    except argparse.ArgumentError, OSError, ValueError:
        return SUBTYPES, "; enabled extensions may add others"
    try:
        return content_subtypes(root), " (core subtypes and enabled extensions)"
    except (OSError, ValueError, SchemaError, RecursionError) as exc:
        return None, f"; cannot read the vault's extensions: {exc}"


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
    initialize.add_argument(
        "--extension",
        action="append",
        default=[],
        help="extension to enable throughout the vault; repeat for multiple (default: none)",
    )
    extension = commands.add_parser(
        "extension", help="manage optional vault extensions"
    )
    extensions = extension.add_subparsers(dest="extension_action", required=True)
    for action, description in (
        ("enable", "install an extension into a vault"),
        ("update", "replace an extension with the current Armarium version"),
        ("remove", "remove an extension and its installed files"),
    ):
        command = extensions.add_parser(action, help=description)
        command.add_argument("name", help="extension identifier")
        if action == "update":
            command.add_argument(
                "--allow-downgrade",
                action="store_true",
                help="allow replacement by an older Armarium version",
            )
        command.add_argument(
            "--vault",
            type=Path,
            help="vault root (default: discovered from the current directory)",
        )
    add = commands.add_parser("add", help="add to an existing vault")
    additions = add.add_subparsers(dest="addition", required=True)
    campaign = additions.add_parser("campaign", help="create a new campaign")
    content = additions.add_parser("content", help="create a Content record")
    player = additions.add_parser("player", help="create a Player record")
    note = additions.add_parser("note", help="create a Note record")
    session = additions.add_parser("session", help="create a Session record")
    clue = additions.add_parser("clue", help="create a Clue record")
    transcript = additions.add_parser(
        "transcript", help="create a Transcript for an existing Session"
    )
    for addition, create in (
        (campaign, add_campaign),
        (content, add_content),
        (player, add_player),
        (note, add_note),
        (session, add_session),
        (clue, add_clue),
        (transcript, add_transcript),
    ):
        addition.set_defaults(create=create)
        addition.add_argument(
            "--vault",
            type=Path,
            help="vault root (default: discovered from the current directory)",
        )
    for addition in (content, player, note):
        addition.add_argument("name", help="record name without .md")
    for addition, shared in (
        (content, ", or shared content"),
        (player, ""),
        (note, ", or shared notes"),
        (session, ""),
        (clue, ""),
    ):
        addition.add_argument(
            "--campaign",
            type=int,
            help=f"campaign number within vault (default: current campaign directory{shared})",
        )
    for addition, description in (
        (campaign, "positive campaign number"),
        (session, "session number from 1 to 999"),
        (clue, "clue number from 1 to 9999"),
    ):
        addition.add_argument(
            "--number",
            type=int,
            help=f"{description} (default: largest existing number + 1)",
        )
    subtypes, origin = _subtype_choices(argv)
    content.add_argument(
        "--subtype", required=True, choices=subtypes, help=f"Content subtype{origin}"
    )
    for addition in (content, player, note, session, clue, transcript):
        fields = addition.add_mutually_exclusive_group()
        fields.add_argument(
            "--frontmatter",
            type=_frontmatter_json,
            metavar="JSON",
            help="JSON object merged into template fields (default: template values)",
        )
        fields.add_argument(
            "--frontmatter-file",
            type=Path,
            metavar="PATH",
            help="UTF-8 JSON object file merged into template fields",
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
    find = commands.add_parser(
        "find",
        help="find records by name or alias",
        description=(
            "List the records whose filename or one of whose aliases is a name, "
            "ignoring case: records with that name, then records with that alias. "
            "Each line holds the record's path, type, match kind and summary, "
            "separated by tabs. Exits with 1 when no record has the name or alias."
        ),
    )
    find.add_argument("name", help="record name or alias, without a path or .md")
    find.add_argument(
        "--campaign",
        type=int,
        help=(
            "only list shared records and this campaign's (default: every "
            "campaign's records)"
        ),
    )
    find.add_argument(
        "--vault",
        type=Path,
        help="vault root (default: discovered from the current directory)",
    )
    trace = commands.add_parser(
        "trace",
        help="list the links to a file, or from a record",
        description=(
            "List every link to one file from the vault's records or, with "
            "--outbound, every link from one record to other files. Each line "
            "holds the other file's path, the frontmatter field or body headings "
            "where the link sits, and its line number, separated by tabs. "
            "Use armarium find to get a record's path from its name."
        ),
    )
    trace.add_argument(
        "--outbound",
        action="store_true",
        help="list the files the record links to, not the records that link to it",
    )
    trace.add_argument(
        "path",
        type=Path,
        help="record or asset to trace; with --vault, relative to the vault root",
    )
    trace.add_argument(
        "--vault",
        type=Path,
        help="vault root (default: discovered from the path)",
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
    command.add_argument(
        "--jobs",
        type=_jobs,
        default=1,
        help="worker processes for validating a directory (default: 1)",
    )
    args = parser.parse_args(argv)
    if args.command == "add":
        path = vars(args).pop("frontmatter_file", None)
        if path is not None:
            try:
                args.frontmatter = _frontmatter_json(
                    path.expanduser().read_text(encoding="utf-8")
                )
            except (OSError, UnicodeError, argparse.ArgumentTypeError) as exc:
                parser.error(f"cannot read frontmatter from {path}: {exc}")
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
        SystemExit: Status 1 when creation fails, files fail validation,
            find matches nothing or trace cannot locate its file.
            Creation reports validation warnings and errors; validate also reports
            informational diagnostics and coverage counts. Argument parsing
            exits with 0 for help or 2 for usage errors.
    """
    args = parse_args()
    configure_logging()
    if args.command == "find":
        try:
            matches = find_records(args.name, args.vault, campaign=args.campaign)
        except (OSError, ValueError) as exc:
            logger.error("Cannot find %s: %s", args.name, exc)
            sys.exit(1)
        for match in matches:
            print(match.line)
        if not matches:
            logger.info("No records match %s", args.name)
            sys.exit(1)
        return
    if args.command == "trace":
        try:
            unresolved: list[str] = []
            if args.outbound:
                target, references, unresolved = trace_outbound(args.path, args.vault)
            else:
                target, references = trace_record(args.path, args.vault)
        except (OSError, ValueError) as exc:
            logger.error("Cannot trace %s: %s", args.path, exc)
            sys.exit(1)
        for reference in references:
            print(reference.text)
        for problem in unresolved:
            logger.warning("%s: %s", target, problem)
        logger.info(
            "%s %s %s %s",
            len(references),
            "link" if len(references) == 1 else "links",
            "from" if args.outbound else "to",
            target,
        )
        return
    if args.command == "init":
        try:
            logger.info(
                "Initializing new vault at %s", args.path.expanduser().resolve()
            )
            destination = init_vault(
                args.path, force=args.force, extensions=args.extension
            )
        except (OSError, ValueError) as exc:
            logger.error("Cannot create vault at %s: %s", args.path, exc)
            sys.exit(1)
        logger.info("New vault successfully initialized; validating")
        result = validate(destination)
    elif args.command == "extension":
        try:
            if args.extension_action == "update":
                destination = update_extension(
                    args.name, args.vault, allow_downgrade=args.allow_downgrade
                )
            else:
                change = (
                    enable_extension
                    if args.extension_action == "enable"
                    else remove_extension
                )
                destination = change(args.name, args.vault)
        except (OSError, ValueError) as exc:
            logger.error(
                "Cannot %s extension %s: %s", args.extension_action, args.name, exc
            )
            sys.exit(1)
        logger.info(
            "Extension %s %s; validating",
            args.name,
            {"enable": "enabled", "remove": "removed", "update": "updated"}[
                args.extension_action
            ],
        )
        result = validate(destination)
    elif args.command == "add":
        try:
            options = {
                key: value
                for key, value in vars(args).items()
                if key not in {"command", "addition", "create"}
            }
            destination = args.create(**options)
        except (OSError, ValueError) as exc:
            logger.error("Cannot add %s: %s", args.addition, exc)
            sys.exit(1)
        logger.info("New %s successfully created; validating", args.addition)
        result = validate(find_vault(destination))
    else:
        result = validate(args.path, args.vault, jobs=args.jobs)
        result.report()
    if args.command in {"init", "add", "extension"}:
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
        elif args.command == "extension":
            logger.error("Extension change retained; see validation diagnostics above")
        sys.exit(1)
    if args.command in {"init", "add", "extension"}:
        logger.info("Validation completed successfully")


if __name__ == "__main__":
    main()
