# Content

Content pages describe characters, places, groups, objects, or setting lore.
Keep each shared entity in one page under `content/`; campaign-specific entries
live in `campaigns/campaign_1/content/` (or the corresponding campaign folder).

Copy [[templates/Content]], name it for the entity, choose a subtype,
and add its required fields.

## Fields

Every Content record requires `type`, `subtype`, and `summary`. The template sets
`type`; choose subtype NPC, PC, Location, Faction, Object or Lore. Write a short
summary of stable identity, or leave it empty for a stub. `aliases` is optional:
use a list of alternate names, or omit it or leave it empty when there are none.

| Subtype | Additional required fields |
| --- | --- |
| NPC | `stats`: empty, an internal wikilink, or an HTTP/HTTPS URL. |
| PC | `player`: a nonempty wikilink to a Player record. |
| Location | `parent_location`: empty or a wikilink to Location Content. |
| Faction | `members`: empty if unknown, or a list of PC/NPC Content links. An empty list means no recorded members. |
| Object | `held_by` inside each campaign block: holder link(s) or `GONE`; may be empty before entering play. |
| Lore | None. |

Use bare `field:` for null and quote YAML wikilinks. Additional custom fields are
allowed. Object holders are PC, NPC or Faction Content. Shared-party possession
links to the party's Faction. Lists represent split sets. `GONE` means the object
has left play, for example through sale, loss, destruction or consumption.

## Body and campaign history

All subtypes share Notes, Active Clues and Appearances, in that order. Notes contain
established information. A Clue is a candidate fact; displaying it under Active
Clues does not establish it as world canon.

Store campaign state in separate `campaign_1:`, `campaign_2:`, etc. blocks. The
initial template includes campaign 1; retain, remove or add blocks according to
the entry's recorded state. Each existing block requires `first_session` and
`last_session`: both empty before appearances, otherwise links to the earliest
and latest Sessions in that campaign's history.

Use one Appearances list across campaigns; the linked Session IDs identify each
entry's campaign. Record actual interaction, not mentions/prep, and noteworthy PC
contributions rather than attendance. Use `N/A` only when there are no appearances.
Keep acquisition and transfer history in Session records when current possession
changes.

Active Clues contains exactly one Base embed and no additional text. Its scope follows this note’s location: shared
`content/` items include active Clues from all campaigns; items under
`campaigns/campaign_N/` include only that campaign. Only Pending or Hinted Clues
whose canonical `subjects` link to this item appear. Do not split Active Clues
or Appearances into campaign subheadings.

## Schema

A Content note’s frontmatter requires `type`, `subtype`, `summary` and the
subtype fields listed above. Its body contains Notes, Active Clues and
Appearances headings in that order. Each campaign block includes `first_session`
and `last_session`; Object campaign blocks also include `held_by`.

See the [Content schema](../schemas/content.schema.json).
