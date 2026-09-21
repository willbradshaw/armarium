#!/usr/bin/env python3
"""Install the basic Armarium starter at a new, independent filesystem path.

Uses only Python's standard library. This is a starter installer, not the future
packaged CLI, updater, skill installer, or general vault validator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "starter"
TOKEN = re.compile(r"\{\{([A-Z_]+)\}\}")
CAMPAIGN_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def display_name(value: str) -> str:
    """Names are display text, never paths or raw YAML."""
    value = value.strip()
    if not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("Names must be nonempty, single-line text without control characters.")
    return value


def markdown(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]<>#|])", r"\\\1", value)


def render(text: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise ValueError(f"Unknown starter substitution: {key}")
        return values[key]

    return TOKEN.sub(replace, text)


def copy_scaffold(source: Path, target: Path, values: dict[str, str]) -> None:
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Starter cannot contain symlinks: {path}")
        if path.is_file():
            output = target / render(path.relative_to(source).as_posix(), values)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(render(path.read_text(encoding="utf-8"), values), encoding="utf-8")


def starter_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted(STARTER.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(STARTER).as_posix().encode("utf-8") + b"\0")
            digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def install(destination: Path, name: str, campaigns: list[tuple[str, str]]) -> Path:
    destination = destination.expanduser()
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Destination already exists; nothing changed: {destination}")
    destination = destination.resolve()
    if destination.is_relative_to(ROOT):
        raise ValueError("Choose a setting-vault destination outside the Armarium checkout.")
    if not destination.parent.is_dir():
        raise ValueError(f"Parent directory does not exist: {destination.parent}")
    name = display_name(name)
    if not campaigns:
        raise ValueError("At least one campaign is required.")
    records = []
    seen: set[str] = set()
    for identifier, title in campaigns:
        if len(identifier) > 40 or not CAMPAIGN_ID.fullmatch(identifier):
            raise ValueError("Campaign IDs must be 1–40 lowercase letters/digits with optional internal hyphens.")
        if identifier in seen:
            raise ValueError(f"Duplicate campaign ID: {identifier}")
        seen.add(identifier)
        records.append({"id": identifier, "name": display_name(title), "path": f"campaigns/{identifier}"})

    manifest = json.loads((STARTER / "manifest.json").read_text(encoding="utf-8"))
    values = {
        "SETTING_NAME_JSON": json.dumps(name, ensure_ascii=False),
        "SETTING_TITLE": markdown(name),
        "CAMPAIGN_NAVIGATION": "\n".join(
            f'- [[{record["path"]}/Campaign-{record["id"]}]] — {markdown(record["name"])}'
            for record in records
        ),
    }
    # Fully render before touching the destination. copytree refuses even an
    # existing empty directory, including one created between validation and copy.
    with tempfile.TemporaryDirectory(prefix=".armarium-starter-", dir=destination.parent) as staging:
        stage = Path(staging)
        copy_scaffold(STARTER / "vault", stage, values)
        for directory in manifest["vault_directories"]:
            folder = stage / directory
            folder.mkdir(parents=True, exist_ok=True)
            (folder / ".gitkeep").touch()
        for record in records:
            context = values | {
                "CAMPAIGN_ID": record["id"],
                "CAMPAIGN_ID_JSON": json.dumps(record["id"]),
                "CAMPAIGN_NAME_JSON": json.dumps(record["name"], ensure_ascii=False),
                "CAMPAIGN_TITLE": markdown(record["name"]),
            }
            campaign = stage / record["path"]
            copy_scaffold(STARTER / "campaign", campaign, context)
            for directory in manifest["campaign_directories"]:
                folder = campaign / directory
                folder.mkdir(parents=True, exist_ok=True)
                (folder / ".gitkeep").touch()
        config = {
            "schema_version": 1,
            "name": name,
            "starter": {"version": manifest["version"], "sha256": starter_hash()},
            "toolkit": {"repository": "https://github.com/willbradshaw/armarium", "revision": None},
            "campaigns": records,
        }
        (stage / "armarium.json").write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        shutil.copytree(stage, destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="New directory outside the Armarium checkout; parent must exist")
    parser.add_argument("--name", required=True, help="Setting/vault display name")
    parser.add_argument("--campaign", nargs=2, action="append", metavar=("ID", "NAME"),
                        help="Initial campaign; repeat for multiple campaigns (default: 1 'First Campaign')")
    args = parser.parse_args()
    try:
        target = install(args.destination, args.name, args.campaign or [("1", "First Campaign")])
    except (ValueError, OSError) as error:
        parser.exit(1, f"Could not create vault: {error}\n")
    print(f"Created {target}\nOpen this folder as an Obsidian vault; start at Home.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
