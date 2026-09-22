"""Small command adapter; all validation behavior lives in the library."""

import argparse
from pathlib import Path

from armarium.validation import validate


def main() -> int:
    """Return 0 for no errors, 1 for invalid notes, 2 for invocation errors."""
    parser = argparse.ArgumentParser(prog="armarium")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("validate", help="validate without changing files")
    command.add_argument("path", type=Path)
    command.add_argument("--vault", type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.path, args.vault)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    for diagnostic in result.diagnostics:
        location = diagnostic.path
        if diagnostic.line:
            location += f":{diagnostic.line}"
        if diagnostic.field:
            location += f" [{diagnostic.field}]"
        print(
            f"{location}: {diagnostic.severity} {diagnostic.rule}: {diagnostic.message}"
        )
    print(
        f"{result.checked} checked, {result.skipped} skipped, "
        f"{result.unsupported} unsupported"
    )
    return int(result.failed)
