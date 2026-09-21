Content pages describe characters, places, groups, objects, or setting lore.
Shared entries live in `content/`; campaign-specific entries live in
`campaigns/campaign_1/content/` (or the corresponding campaign folder).

Use [[reference/templates/Content]]. Choose subtype NPC, PC, Location, Faction,
Object or Lore, then add its fields. All share Notes, Active Clues and Appearances.

| Subtype | Additional fields |
| --- | --- |
| NPC | `stats`: empty, an internal wikilink, or an HTTP/HTTPS URL. |
| PC | `player`: a nonempty wikilink to a Player record. |
| Location | `parent_location`: empty or a wikilink to Location Content. |
| Faction | `members`: empty if unknown, or a list of PC/NPC Content links. |
| Object | `held_by` inside each campaign block: holder link(s) or `GONE`; may be empty before entering play. |
| Lore | None. |

Use bare `field:` for null and quote YAML wikilinks. Pronouns and birth information
belong in Notes when useful; additional custom fields are allowed.

Object holders are PC, NPC or Faction Content. Shared-party possession links to the
party's Faction. `GONE` means out of play, not unknown; lists represent split sets.

Each existing campaign block requires `first_session` and `last_session`: both
empty before appearances, otherwise links to the earliest/latest Sessions in that
campaign's history. Do not require a block for every campaign in the vault. Separate
shared histories under headings such as `### campaign_1`. Record actual interaction,
not mentions/prep, and noteworthy PC contributions rather than attendance.

The formal [Content schema](../schemas/content.schema.json) defines the field
requirements and heading order. Blank templates are unfinished forms; populate the
subtype and its required fields before treating a copied template as a record.
