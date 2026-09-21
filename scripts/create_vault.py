#!/usr/bin/env python3
"""Copy the Isles-derived starter to a new independent vault directory."""

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "starter" / "vault"


def install(destination: Path) -> Path:
    destination = destination.expanduser()
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Destination already exists; nothing changed: {destination}")
    destination = destination.resolve()
    if destination.is_relative_to(ROOT):
        raise ValueError("Choose a destination outside the Armarium checkout.")
    if not destination.parent.is_dir():
        raise ValueError(f"Parent directory does not exist: {destination.parent}")
    # Refuse unsafe starter sources before creating the destination.
    if any(path.is_symlink() for path in STARTER.rglob("*")):
        raise ValueError("Starter cannot contain symlinks.")
    # copytree also refuses a destination created after the check above.
    shutil.copytree(STARTER, destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path,
                        help="New vault folder; its parent must exist")
    args = parser.parse_args()
    try:
        target = install(args.destination)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Could not create vault: {error}\n")
    print(f"Created {target}\nOpen this folder as an Obsidian vault.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
