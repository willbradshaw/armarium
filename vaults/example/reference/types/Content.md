---
type: "[[Type]]"
directories: { shared: content, campaign: content }
---
# Content

Content records describe characters, places, groups, objects, dates, or setting lore.
Keep each shared entity in one record under `content/`; campaign-specific entries
live in `campaigns/campaign_1/content/` (or the corresponding campaign folder).

Copy [[templates/Content]], name it for the entity, choose a subtype,
and add its required fields.

## Fields

Every Content record requires `type`, `subtype`, and `summary`. The template sets
`type`; choose subtype NPC, PC, Location, Faction, Object, Lore, Date or Gear, or one
an enabled extension adds, as listed in its README under `reference/extensions/`. Write a short
summary of stable identity, or leave it empty for a stub. `aliases` is optional:
use a list of alternate names, or omit it or leave it empty when there are none.

| Subtype | Additional required fields |
| --- | --- |
| NPC | `stats`: empty, an internal wikilink, or an HTTP/HTTPS URL. |
| PC | `player`: a nonempty wikilink to a Player record. |
| Location | `parent_location`: empty or a wikilink to Location Content. |
| Faction | `members`: empty if unknown, or a list of PC/NPC Content links. An empty list means no recorded members. |
| Object, Gear | `held_by` inside each campaign block: holder link(s) or `GONE`; may be empty before entering play. |
| Gear | `source`: publication or homebrew attribution; empty when unrecorded. Optional `image` and `url`. |
| Lore | None. |
| Date | `reckoning`: a nonempty link to Lore describing the calendar. `scale`: a nonblank calendar-defined string, such as day or year. |

Object describes narrative artifacts; Gear describes equipment with recorded game
mechanics, whether magical or mundane. Gear may add an `image` path relative to
the vault root or an image URL, and an HTTP/HTTPS `url` for its source. These fields
may be omitted or empty. Other rules-specific fields are custom frontmatter.

Dates represent particular days or periods within a calendar. Recurring calendar
concepts, such as a named month or weekday, are Lore rather than Dates.
Calendar-specific fields are custom frontmatter. A custom vault-local schema can constrain date
notation and allowed scales; the standard schema does not impose those constraints.

Use bare `field:` for null and quote YAML wikilinks. Additional custom fields are
allowed. Object and Gear holders are PC, NPC or Faction Content. Shared-party possession
links to the party's Faction. Lists represent split sets. `GONE` means the object
has left play, for example through sale, loss, destruction or consumption.

## Body and campaign history

Gear begins with a `> [!rules]` callout containing its rules text, optionally
followed by an image embed. An empty callout is allowed for a stub.

All subtypes share Notes, Active Clues and Appearances, in that order. Notes contain
established information. A Clue is a candidate fact; displaying it under Active
Clues does not establish it as world canon.

Store campaign state in separate `campaign_1:`, `campaign_2:`, etc. blocks. The
initial template includes campaign 1; retain, remove or add blocks according to
the entry's recorded state. Each existing block requires `first_session` and
`last_session`: both empty before appearances, otherwise links to the earliest
and latest Sessions in that campaign's history.

Use one Appearances list across campaigns; the linked Session IDs identify each
entry's campaign. For Dates, appearances record Sessions whose played events occur
within that day or period; historical information and mentions belong in Notes.
For other subtypes, record actual interaction, not mentions/prep, and noteworthy
PC contributions rather than attendance. Use `N/A` only when there are no appearances.
Keep acquisition and transfer history in Session records when current possession
changes.

Active Clues contains exactly one Base embed and no additional text. Its scope follows this record’s location: shared
`content/` items include active Clues from all campaigns; items under
`campaigns/campaign_N/` include only that campaign. Only Pending or Hinted Clues
whose canonical `subjects` link to this item appear. Do not split Active Clues
or Appearances into campaign subheadings.

## Schema

A Content record’s frontmatter requires `type`, `subtype`, `summary` and the
subtype fields listed above. Its body contains Notes, Active Clues and
Appearances headings in that order. Each campaign block includes `first_session`
and `last_session`; Object and Gear campaign blocks also include `held_by`.

See the [Content schema](../schemas/content.schema.json).
