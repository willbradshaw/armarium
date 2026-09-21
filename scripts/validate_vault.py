#!/usr/bin/env python3
"""Validate an explicit vault path without modifying it."""

import argparse
import sys

try:
    from validation import validate_vault
except ModuleNotFoundError as exc:
    if exc.name != "yaml":
        raise
    sys.exit("Missing PyYAML. Install with: python -m pip install -r requirements.txt")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault", help="Vault root (for example, starter/)")
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
