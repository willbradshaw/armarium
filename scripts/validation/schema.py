"""Supported Armarium fields and headings, collected here for easy review."""

import re

CAMPAIGN = re.compile(r"campaign_([0-9]+)$")

ENTITY_FOLDERS = {
    "Location": "locations",
    "NPC": "npcs",
    "Faction": "factions",
    "Lore": "lore",
    "Object": "objects",
    "PC": "pcs",
}
CONTENT_FOLDERS = ENTITY_FOLDERS | {
    "Session": "sessions",
    "Clue": "clues",
    "Player": "players",
    "Transcript": "transcripts",
}
CAMPAIGN_ONLY = {"PC", "Session", "Clue", "Player", "Transcript"}

# Campaign mappings are conditional on scope, rather than required on all pages.
REQUIRED_FIELDS = {
    "Location": ("summary", "parent_location"),
    "NPC": ("summary", "aliases", "stats", "birth_year"),
    "Faction": ("summary", "members"),
    "Lore": ("summary", "aliases"),
    "Object": ("summary",),
    "PC": ("summary", "player", "pronouns"),
    "Clue": ("status", "text", "subjects", "first_session", "last_session"),
    "Session": (
        "date", "campaign", "session_number", "aliases", "players_absent",
        "in_game_start_date", "in_game_end_date",
    ),
}

# Values are the allowed types of the linked records, not definition pages.
RECORD_LINK_FIELDS = {
    "parent_location": {"Location"},
    "player": {"Player"},
    "held_by": set(ENTITY_FOLDERS),
    "first_session": {"Session"},
    "last_session": {"Session"},
    "campaign": {"Reference"},
}
LINK_LIST_FIELDS = {
    "members": set(ENTITY_FOLDERS),
    "subjects": set(ENTITY_FOLDERS),
    "players_absent": {"Player"},
}
DEFINITION_LINK_FIELDS = {
    "type": "types",
    "status": "statuses",
    "applies_to": "types",
}
STATE_LINK_FIELDS = {
    key: RECORD_LINK_FIELDS[key]
    for key in ("first_session", "last_session", "held_by")
}

# Heading levels are part of the contract; intervening user headings are allowed.
type Heading = tuple[int, str]
ENTITY_HEADINGS: tuple[Heading, ...] = (
    (2, "Notes"),
    (2, "Active Clues"),
    (2, "Appearances"),
)
SESSION_HEADINGS: tuple[Heading, ...] = (
    (1, "Preparation"),
    (2, "Starting scene"),
    (2, "Other scenes"),
    (2, "Secrets & Clues"),
    (2, "Locations"),
    (2, "Important NPCs"),
    (2, "Scene notes"),
    (2, "Encounters"),
    (2, "Prepared rewards"),
    (1, "Notes"),
    (2, "Preamble"),
    (2, "Events"),
    (2, "Rewards"),
    (3, "Loot"),
)
