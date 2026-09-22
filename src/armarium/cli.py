"""Command-line adapter for read-only single-file Markdown validation."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from armarium.validate import validate_markdown


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected command and render its validation result.

    Args:
        argv: Command arguments without the executable name. None reads the
            process arguments, as required by a console-script entry point.

    Returns:
        int: 0 when validation reports no errors, including explicit skips and
            partial-coverage warnings; 1 when it reports an error. Findings and
            coverage counts are printed to standard output.

    Raises:
        SystemExit: Argparse exits with 0 for help or 2 for invalid invocation.
            Invocation errors, including invalid target/vault paths and I/O
            failures outside note parsing, are printed to standard error.
    """
    parser = argparse.ArgumentParser(prog="armarium")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("validate", help="validate one Markdown file")
    command.add_argument("path", type=Path, help="Markdown file to validate")
    command.add_argument("--vault", type=Path, help="explicit vault directory")
    args = parser.parse_args(argv)
    try:
        result = validate_markdown(args.path, args.vault)
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


if __name__ == "__main__":
    raise SystemExit(main())
