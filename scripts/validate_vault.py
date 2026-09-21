#!/usr/bin/env python3
"""Validate an explicit vault path without modifying it."""

import argparse
import sys

if sys.version_info < (3, 14):
    sys.exit("Vault validation requires Python 3.14 or newer.")

try:
    from validation import validate_vault
except ModuleNotFoundError as exc:
    if exc.name != "yaml":
        raise
    sys.exit("Missing PyYAML. Install with: python -m pip install -r requirements.txt")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault", help="Path to your Armarium vault")
    args = parser.parse_args()
    errors = validate_vault(args.vault)
    for error in errors:
        print(error)
    if errors:
        print(f"Validation failed: {len(errors)} error(s).")
        return 1
    print("Vault validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
