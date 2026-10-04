# Types

Each [record](record.md) has a type, declared in its `type` field, that
determines where it lives, which frontmatter fields it has and what its body
contains. A type is defined by a Type record in `reference/types/` and its
schema in `reference/schemas/`. The built-in types follow, in alphabetical
order. In the frontmatter tables, a *required* field must be present and an
*optional* one may be omitted; a field may hold null only where null is
listed among its values.

## Clue

### Description

A GM-known candidate fact tracked through a lifecycle.

### Location

`campaigns/campaign_N/clues/`, named `C-N-NNNN.md` with the
[campaign](campaign.md) number and a four-digit ordinal.

### Frontmatter

| Field | Presence | Value |
| --- | --- | --- |
| `type` | required | `[[types/Clue]]` |
| `status` | required | a link to a [Status](#status) that applies to Clues: `[[Pending]]`, `[[Hinted]]`, `[[Revealed]]`, `[[Abandoned]]`, `[[Dormant]]` or `[[Superseded]]` |
| `text` | required | non-blank text; its links must be [Content](#content) in the same campaign or shared |
| `subjects` | required | null (unidentified), `[]` (none) or exactly the records linked in `text`, as a list of links |
| `first_session` | required | null, or a link to the [Session](#session) in which the Clue was first prepared or used |
| `last_session` | required | null, or a link to the Session of its latest introduction or development; requires `first_session` and may not precede it |
| `superseded_by` | required when `status` is `[[Superseded]]`, forbidden otherwise | a link to the replacing Clue; following it from Clue to Clue must never return to the starting Clue |

### Body

Exactly `## Sessions` followed by one `.base` embed; nothing else.

## Content

### Description

A character, place, group, object, date or piece of setting lore.

### Location

`content/` when shared by every [campaign](campaign.md), or
`campaigns/campaign_N/content/` when specific to one. Share an entity that
keeps its identity outside any one campaign, such as a city, a people or a
calendar; keep it with its campaign when it matters only through that
campaign's story.

### Frontmatter

| Field | Presence | Value |
| --- | --- | --- |
| `type` | required | `[[types/Content]]` |
| `subtype` | required | `NPC`, `PC`, `Location`, `Faction`, `Object`, `Lore`, `Date` or `Gear`, or a subtype declared by an enabled [extension](extensions.md#declaring-subtypes) |
| `summary` | required | null for a stub, or short text describing stable identity: what the entity is, not its present situation |
| `aliases` | optional | null, `[]` or a list of non-empty strings |
| `content_tags` | optional | null, `[]` or a list of unique, non-blank strings: freeform labels for filtering Content |
| `stats` | required for NPC | null, a link to a record, or an `http(s)://` URL |
| `player` | required for PC | a link to a [Player](#player) in the same campaign |
| `parent_location` | required for Location | null, or a link to Location Content in the same campaign or shared; following it from Location to Location must never return to the starting record |
| `members` | required for Faction | null (unknown), `[]` (none recorded) or a list of links to PC or NPC Content in the same campaign or shared |
| `source` | required for Gear | null when unrecorded, or nonblank publication/homebrew attribution |
| `image` | optional for Gear | null, or a nonblank vault-relative image path or image URL |
| `url` | optional for Gear | null, or an HTTP/HTTPS source URL |
| `reckoning` | required for Date | nonempty wikilink to a Lore record describing the calendar, in the same campaign or shared |
| `scale` | required for Date | nonblank string naming a calendar period, such as `day`, `month`, `year` or `century`; no fixed list of values |
| `campaign_N` | optional, one per campaign the record has state in | a mapping of the record's [state in that campaign](campaign.md#state) |

### Body

Gear begins with a `> [!rules]` callout, optionally followed by an image embed.
The callout may be empty for a stub. Object describes narrative artifacts; Gear
describes equipment with recorded mechanics, whether magical or mundane. Both
use the same [possession fields](campaign.md#state).

`## Notes`, `## Active Clues` and `## Appearances`, in that order. Active
Clues holds exactly one `.base` embed and nothing else. Appearances is one
list of `- [[S-N-NNN]]: what happened` items, or the single item `- N/A` when
there are none; no other blocks or subheadings. The list runs through
campaigns in ascending order and, within a campaign, in ascending session
order without repeats, and each campaign that appears must have a
[`campaign_N` block](campaign.md#state) whose
`first_session` and `last_session` are that campaign's earliest and latest
entries.

Notes hold established, lasting information, read without the context of any
one Session:

- Record only what play or the GM's own material states, or `- N/A` while
  nothing is established.
- Describe the entity in absolute terms, not the scene in which it was met.
- Leave single incidents to that Session's appearance, and changing state to
  the [campaign block](campaign.md#state).
- Add a [Clue](#clue)'s content only once the Clue is Revealed, and link it.

Appearances gives each Session in which the entity appeared one item, saying in
a clause what happened to it or through it:

| Subtype | Appears in a Session when |
| --- | --- |
| NPC | on stage in a scene: speaking, acting or dealing directly with those present |
| PC | doing something noteworthy; attendance alone is not an appearance |
| Location | the party is physically there |
| Faction | acting as a body; a member acting alone appears on their own record |
| Object, Gear | handled: acquired, put to use, transferred or accessed |
| Lore | its particular identity shapes events; background colour is not an appearance |
| Date | the Session's played events occur within that day or period |

A mention is not an appearance, and nor is preparation that play does not
reach. Historical information about a Date belongs in Notes.

Date Content represents a particular day or period. Recurring calendar concepts,
such as a named month or weekday, are Lore. Calendar-specific frontmatter fields
are permitted as custom fields, with no built-in calendar arithmetic or
session-date reconciliation.

## Note

### Description

A freeform document: working notes, design notes, session prep, ideas.
Brainstorming Notes contain proposals, not established setting facts. Adopted
ideas belong in the relevant Content records or Session preparation.

### Location

`notes/` when shared by every [campaign](campaign.md), or
`campaigns/campaign_N/notes/` when specific to one.

### Frontmatter

| Field | Presence | Value |
| --- | --- | --- |
| `type` | required | `[[types/Note]]` |

### Body

Free Markdown, possibly empty.

## Player

### Description

A person at the table.

### Location

`campaigns/campaign_N/reference/players/`.

### Frontmatter

| Field | Presence | Value |
| --- | --- | --- |
| `type` | required | `[[types/Player]]` |
| `plays` | required | a list of links to PC [Content](#content) in the same [campaign](campaign.md), `[]` when unassigned |

### Body

Free Markdown, possibly empty.

## Reference

### Description

A structural, taxonomic or index record, such as a campaign overview or the
clue index.

### Location

`reference/` when shared by every [campaign](campaign.md), or
`campaigns/campaign_N/reference/` when specific to one, including subfolders
such as `indexes/` but not those that belong to another type (`types/`,
`statuses/`, `players/`).

### Frontmatter

| Field | Presence | Value |
| --- | --- | --- |
| `type` | required | `[[Reference]]` |

### Body

Free Markdown, possibly empty.

## Session

### Description

One play session.

### Location

`campaigns/campaign_N/sessions/`, named `S-N-NNN.md` with the
[campaign](campaign.md) number and a three-digit ordinal.

### Frontmatter

| Field | Presence | Value |
| --- | --- | --- |
| `type` | required | `[[types/Session]]` |
| `date` | required | null, or `YYYY-MM-DD` |
| `campaign` | required | a link to the containing campaign's `reference/Campaign.md` |
| `session_number` | required | a positive integer equal to the ordinal in the filename |
| `aliases` | optional | null, `[]` or a list of non-blank strings |
| `players_absent` | required | null, or a list of links to [Players](#player) in the same campaign |
| `in_game_start_date`, `in_game_end_date` | required | null, or a wikilink to Date Content in the same campaign or shared |
| `prepared_clues`, `prepared_locations`, `prepared_npcs` | optional | ordered lists of links to [Clues](#clue) in the same campaign, and to Location and NPC [Content](#content) in the same campaign or shared; `[]` or omitted selects nothing |

### Body

The template's headings in order: `# Preparation` with `## Starting scene`,
`## Other scenes`, `## Secrets & Clues`, `## Locations`, `## Important NPCs`,
`## Scene notes`, `## Encounters`, `## Prepared rewards`; then `# Notes` with
`## Preamble`, `## Events`, `## Rewards`. Secrets & Clues, Locations and
Important NPCs each hold exactly one `.base` embed and nothing else; the
other sections are free Markdown, and subsections such as `### Loot` are
optional.

## Status

### Description

A lifecycle state for one type. The six shipped statuses apply to
[Clues](#clue).

### Location

`reference/statuses/`, named for the status.

### Frontmatter

| Field | Presence | Value |
| --- | --- | --- |
| `type` | required | `[[Status]]` |
| `applies_to` | required | a link to the [Type](#type) record the status applies to |

### Body

Free Markdown describing the status.

## Transcript

### Description

Cleaned, attributed speech from one [Session](#session).

### Location

`campaigns/campaign_N/sessions/transcripts/`, named after its Session:
`S-N-NNN Transcript.md`.

### Frontmatter

| Field | Presence | Value |
| --- | --- | --- |
| `type` | required | `[[types/Transcript]]` |
| `session` | required | a link to the Session in the same [campaign](campaign.md) the transcript records, which the filename must match |

### Body

A run of titled `## ` sections and nothing before the first. Each section
holds exactly one bullet list and nothing else. Each item is one utterance: a
single paragraph opening with a speaker tag, a space and text —
`- [GM] The bell rings.` — where the tag names the GM, the table, a character
(`[Esme]`, `[Darian — Martin]`) or an uncertain speaker (`[Player?]`, `[?]`).
After the tag, square brackets may appear only inside wikilinks. A long
utterance may wrap onto further lines of its item.

## Type

### Description

The definition of a record type. `Type.md` and `Status.md` are themselves
Type records.

### Location

`reference/types/`, named for the type.

### Frontmatter

| Field | Presence | Value |
| --- | --- | --- |
| `type` | required | `[[Type]]` |
| `directories` | required | a mapping of `shared` and/or `campaign` to a relative path without `..` or a leading `/`; every declared directory must exist |

### Body

Free Markdown, conventionally the type's documentation.
