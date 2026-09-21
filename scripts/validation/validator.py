"""The supported starter schema; no game-system or user-vault dependencies."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import os
import re

from .parsing import Diagnostic, Page, Resolver, link_target, markdown_lines, parse_page, scan_links

CAMPAIGN = re.compile(r"campaign_([0-9]+)$")
ENTITIES = {"Location": "locations", "NPC": "npcs", "Faction": "factions",
            "Lore": "lore", "Object": "objects", "PC": "pcs"}
FOLDERS = {**ENTITIES, "Session": "sessions", "Clue": "clues",
           "Player": "players", "Transcript": "transcripts"}
WORLD = {folder for kind, folder in ENTITIES.items() if kind != "PC"}
CAMPAIGN_FOLDERS = set(FOLDERS.values()) | {"index"}
ENTITY_SECTIONS = [(2, name) for name in ("Notes", "Active Clues", "Appearances")]
SESSION_SECTIONS = [(1, "Preparation")] + [(2, name) for name in (
    "Starting scene", "Other scenes", "Secrets & Clues", "Locations", "Important NPCs",
    "Scene notes", "Encounters", "Prepared rewards")] + [(1, "Notes")] + [
    (2, "Preamble"), (2, "Events"), (2, "Rewards"), (3, "Loot")]


def discover(root: Path):
    """Skip hidden paths and all symlinks, so external files are never read."""
    files, directories, errors = set(), set(), []

    def onerror(exc):
        errors.append(Diagnostic(str(Path(exc.filename).relative_to(root)), "io.read", str(exc)))

    for base, dirs, names in os.walk(root, followlinks=False, onerror=onerror):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (Path(base) / d).is_symlink())
        for name in dirs:
            directories.add((Path(base) / name).relative_to(root).as_posix())
        for name in sorted(names):
            path = Path(base) / name
            if not name.startswith(".") and not path.is_symlink():
                files.add(path.relative_to(root).as_posix())
    return files, directories, errors


def validate_vault(vault: str | Path) -> list[Diagnostic]:
    root = Path(vault).resolve()
    if not root.is_dir():
        return [Diagnostic(".", "structure.root", "Choose an existing vault directory (the starter/ folder, not the repository).")]
    files, directories, errors = discover(root)
    campaigns = sorted(d for d in directories if CAMPAIGN.fullmatch(d))
    required = {"world", "templates", "types", "statuses", "assets", "reference"}
    required |= {f"world/{folder}" for folder in WORLD}
    for campaign in campaigns:
        required |= {f"{campaign}/{folder}" for folder in CAMPAIGN_FOLDERS}
    for directory in sorted(required - directories):
        errors.append(Diagnostic(directory, "structure.directory", "Create the required directory (it may be empty)."))
    if not campaigns:
        errors.append(Diagnostic(".", "structure.campaign", "Provide at least one campaign_<number> directory."))
    pages = {}
    for path in sorted(files):
        if not path.endswith(".md"):
            continue
        try:
            page, problems = parse_page(path, (root / path).read_text(encoding="utf-8"))
            pages[path] = page
            errors.extend(problems)
        except (OSError, UnicodeError) as exc:
            errors.append(Diagnostic(path, "io.read", str(exc)))
    resolver = Resolver(files, pages)
    checker = Checker(pages, resolver, campaigns, errors)
    for page in pages.values():
        links, problems = scan_links(page)
        errors.extend(problems)
        for link in links:
            _, rule, message = resolver.resolve(link.target, page.path)
            if rule:
                errors.append(Diagnostic(page.path, rule, message, link.line))
        checker.check(page)
    return sorted(errors, key=lambda e: (e.path, e.line or 0, e.field or "", e.rule))


class Checker:
    def __init__(self, pages, resolver, campaigns, errors):
        self.pages, self.resolver, self.campaigns, self.errors = pages, resolver, campaigns, errors

    def error(self, page, rule, message, field=None):
        self.errors.append(Diagnostic(page.path, rule, message, field=field))

    def required(self, page, data, names, prefix=""):
        for name in names:
            if name not in data:
                self.error(page, "field.required", "Add this key; unknown values may be null unless documented otherwise.", prefix + name)

    def shape(self, page, value, predicate, field, expected):
        if value is not None and not predicate(value):
            self.error(page, "field.shape", f"Expected {expected}, or null for unknown.", field)

    def kind(self, page):
        value = page.data.get("type")
        if not isinstance(value, str) or link_target(value) is None:
            return None
        path, _, _ = self.resolver.resolve(link_target(value), page.path)
        if path and Path(path).parent.as_posix() == "types":
            return Path(path).stem
        return None

    def record_link(self, page, value, field, kinds=None, directory=None, mandatory=False):
        if value is None and not mandatory:
            return None
        if not isinstance(value, str) or not value.strip() or link_target(value) is None:
            self.error(page, "field.link", "Use a quoted canonical wikilink" + ("." if mandatory else " or null."), field)
            return None
        target, _, _ = self.resolver.resolve(link_target(value), page.path)
        if target is None:
            return None  # The link scanner supplies the resolution diagnostic.
        record = self.pages.get(target)
        if directory and (not record or Path(target).parent.as_posix() != directory):
            self.error(page, "link.kind", f"Link to a definition in {directory}/.", field)
        if kinds and (not record or target.startswith(("templates/", "types/", "statuses/")) or self.kind(record) not in kinds):
            self.error(page, "link.kind", f"Link to an actual {'/'.join(sorted(kinds))} record.", field)
        return target

    def link_list(self, page, value, field, kinds=None):
        if value is None:
            return
        if not isinstance(value, list):
            self.error(page, "field.shape", "Expected a list of canonical wikilinks, or null.", field)
            return
        for i, item in enumerate(value):
            self.record_link(page, item, f"{field}[{i}]", kinds, mandatory=True)

    def sections(self, page, required):
        headings = []
        for _, line, prose in markdown_lines(page.body):
            match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line) if prose else None
            if match:
                headings.append((len(match[1]), match[2]))
        positions = []
        for heading in required:
            if heading not in headings:
                self.error(page, "body.section", f"Add {'#' * heading[0]} {heading[1]}.")
            else:
                positions.append(headings.index(heading))
        if positions != sorted(positions):
            self.error(page, "body.order", "Keep required sections in template order.")

    def check(self, page: Page):
        data, parts = page.data, Path(page.path).parts
        template = parts[0] == "templates"
        campaign = parts[0] if CAMPAIGN.fullmatch(parts[0]) else None
        definition = parts[0] in {"types", "statuses"}
        kind = self.kind(page)
        if "type" in data:
            self.record_link(page, data["type"], "type", directory="types", mandatory=True)
        elif ((parts[0] == "world" or campaign) and len(parts) > 2 and parts[1] in FOLDERS.values()) or (
                template and Path(page.path).stem in set(ENTITIES) | {"Session", "Clue"}):
            self.error(page, "field.required", "Add type: a quoted link to types/<Type>.", "type")
        if "aliases" in data:
            aliases = data["aliases"]
            self.shape(page, aliases, lambda v: isinstance(v, list) and all(
                isinstance(a, str) or (template and a is None) for a in v), "aliases", "a list of strings")
        if parts[0] == "statuses":
            self.required(page, data, ["applies_to"])
        if "applies_to" in data:
            self.record_link(page, data["applies_to"], "applies_to", directory="types", mandatory=True)
        if "status" in data and kind != "Clue":
            self.record_link(page, data["status"], "status", directory="statuses", mandatory=True)
        if "campaign" in data and kind != "Session":
            self.record_link(page, data["campaign"], "campaign", {"Reference"}, mandatory=True)
        if definition:
            return
        if kind in FOLDERS and not template:
            if parts[0] == "world":
                if kind in {"PC", "Session", "Clue", "Player", "Transcript"} or len(parts) < 3 or parts[1] != FOLDERS[kind]:
                    self.error(page, "structure.placement", f"Place {kind} in its supported world/campaign {FOLDERS[kind]}/ folder.")
            elif campaign and (len(parts) < 3 or parts[1] != FOLDERS[kind]):
                self.error(page, "structure.placement", f"Place {kind} under {campaign}/{FOLDERS[kind]}/.")
        if kind in ENTITIES or (template and Path(page.path).stem == "Content"):
            self.sections(page, ENTITY_SECTIONS)
        if kind in ENTITIES:
            self.required(page, data, ["summary"])
            self.shape(page, data.get("summary"), lambda v: isinstance(v, str), "summary", "text")
            extra = {"NPC": ["aliases", "stats", "birth_year"], "Lore": ["aliases"],
                     "Location": ["parent_location"], "Faction": ["members"], "PC": ["player", "pronouns"]}
            self.required(page, data, extra.get(kind, []))
            blocks = [key for key in data if isinstance(key, str) and CAMPAIGN.fullmatch(key)]
            if not blocks:
                self.error(page, "field.required", "Add a campaign_<number> state mapping.", "campaign_<number>")
            if campaign and campaign not in blocks:
                self.error(page, "identity.campaign", f"Add state for containing {campaign}.", campaign)
        # Known properties are checked even on reference/custom pages.
        for key in ("summary", "text", "pronouns"):
            if key in data:
                self.shape(page, data[key], lambda v: isinstance(v, str), key, "text")
        if "birth_year" in data:
            self.shape(page, data["birth_year"], lambda v: type(v) is int or isinstance(v, str), "birth_year", "an integer or calendar-neutral text")
        if "stats" in data:
            self.shape(page, data["stats"], lambda v: isinstance(v, (str, dict)), "stats", "text/a link or a system-specific mapping")
        for key, kinds in {"parent_location": {"Location"}, "player": {"Player"},
                           "held_by": set(ENTITIES), "first_session": {"Session"}, "last_session": {"Session"}}.items():
            if key in data:
                self.record_link(page, data[key], key, kinds)
        for key, kinds in {"members": set(ENTITIES), "subjects": set(ENTITIES), "players_absent": {"Player"}}.items():
            if key in data:
                self.link_list(page, data[key], key, kinds)
        for key, value in data.items():
            if not isinstance(key, str) or not CAMPAIGN.fullmatch(key):
                continue
            if key not in self.campaigns:
                self.error(page, "identity.campaign", f"No {key}/ directory exists.", key)
            if not isinstance(value, dict):
                self.error(page, "field.shape", "Campaign state must be a mapping, with nullable values.", key)
                continue
            self.required(page, value, ["first_session", "last_session"] + (["held_by"] if kind == "Object" else []), key + ".")
            for field, kinds in {"first_session": {"Session"}, "last_session": {"Session"}, "held_by": set(ENTITIES)}.items():
                if field in value:
                    target = self.record_link(page, value[field], key + "." + field, kinds)
                    if target and field.endswith("session") and Path(target).parts[0] != key:
                        self.error(page, "identity.campaign", f"Session must belong to {key}.", key + "." + field)
        if kind == "Clue":
            self.required(page, data, ["status", "text", "subjects", "first_session", "last_session"])
            status = self.record_link(page, data.get("status"), "status", directory="statuses", mandatory=True)
            if status and status in self.pages:
                applies = self.pages[status].data.get("applies_to")
                target = self.resolver.resolve(link_target(applies), status)[0] if isinstance(applies, str) and link_target(applies) is not None else None
                if target != "types/Clue.md":
                    self.error(page, "status.applicability", "Choose a status whose applies_to resolves to types/Clue.", "status")
            self.sections(page, [(2, "Sessions")])
        if kind == "Session":
            self.required(page, data, ["date", "campaign", "session_number", "aliases", "players_absent", "in_game_start_date", "in_game_end_date"])
            self.sections(page, SESSION_SECTIONS)
            target = self.record_link(page, data.get("campaign"), "campaign", {"Reference"}, mandatory=True)
            if not template and target and target != f"{campaign}/Campaign.md":
                self.error(page, "identity.campaign", "Campaign link must resolve to the containing campaign's Campaign.md.", "campaign")
        for key in ("date", "in_game_start_date", "in_game_end_date"):
            if key in data:
                self.shape(page, data[key], lambda v: isinstance(v, (str, date)) or type(v) is int, key, "date text or an integer (no calendar validation)")
        if "session_number" in data:
            self.shape(page, data["session_number"], lambda v: type(v) is int and v > 0, "session_number", "a positive integer")
        if kind in {"Session", "Clue"} and not template:
            prefix, width = ("S", 3) if kind == "Session" else ("C", 4)
            match = re.fullmatch(rf"{prefix}-([0-9]+)-([0-9]{{{width}}})", Path(page.path).stem)
            if not match:
                self.error(page, "identity.filename", f"Name this record {prefix}-<campaign>-{'N' * width}.md.")
            if not campaign or (match and match[1] != CAMPAIGN.fullmatch(campaign)[1]):
                self.error(page, "identity.campaign", "Filename campaign ID must agree with the containing campaign_<number> directory.")
            if kind == "Session" and (type(data.get("session_number")) is not int or (match and data["session_number"] != int(match[2]))):
                self.error(page, "identity.session-number", "Set session_number to the integer in the filename.", "session_number")
            for key in ("first_session", "last_session"):
                value = data.get(key)
                if isinstance(value, str) and link_target(value) is not None:
                    target = self.resolver.resolve(link_target(value), page.path)[0]
                    if target and Path(target).parts[0] != campaign:
                        self.error(page, "identity.campaign", "Session must belong to the containing campaign.", key)
