"""The records that links in each type-bound frontmatter field must name."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    """Requirements on the record that a type-bound field links to.

    Attributes:
        record_type: Required declared type of the target.
        subtypes: Permitted Content subtypes, or empty for any subtype.
        campaign: Campaign directory name (campaign_N) the target must belong
            to, or None for no fixed campaign.
        local: Whether the target must belong to the campaign containing the
            linking record; no restriction applies when that record is outside
            every campaign. Shared Content outside every campaign satisfies
            either campaign requirement.
    """

    record_type: str
    subtypes: frozenset[str] = frozenset()
    campaign: str | None = None
    local: bool = False


# Top-level frontmatter fields whose links must target a record of a given type:
# on every record, then by the record's (type, subtype), where entries under
# (type, None) apply to every record of that type.
LINK_TARGETS = {"type": Target("Type"), "status": Target("Status")}
RECORD_LINK_TARGETS: dict[tuple[str, str | None], dict[str, Target]] = {
    ("Status", None): {"applies_to": Target("Type")},
    ("Content", "Date"): {
        "reckoning": Target("Content", frozenset({"Lore"}), local=True)
    },
    ("Content", "PC"): {"player": Target("Player", local=True)},
    ("Content", "Location"): {
        "parent_location": Target("Content", frozenset({"Location"}), local=True)
    },
    ("Content", "Faction"): {
        "members": Target("Content", frozenset({"PC", "NPC"}), local=True)
    },
    ("Player", None): {"plays": Target("Content", frozenset({"PC"}), local=True)},
    ("Transcript", None): {"session": Target("Session", local=True)},
    ("Clue", None): {
        "text": Target("Content", local=True),
        "subjects": Target("Content", local=True),
        "first_session": Target("Session", local=True),
        "last_session": Target("Session", local=True),
        "superseded_by": Target("Clue", local=True),
    },
    ("Session", None): {
        "in_game_start_date": Target("Content", frozenset({"Date"}), local=True),
        "in_game_end_date": Target("Content", frozenset({"Date"}), local=True),
        "campaign": Target("Reference", local=True),
        "players_absent": Target("Player", local=True),
        "prepared_clues": Target("Clue", local=True),
        "prepared_locations": Target("Content", frozenset({"Location"}), local=True),
        "prepared_npcs": Target("Content", frozenset({"NPC"}), local=True),
    },
}
