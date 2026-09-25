# Types

Each [record](record.md) has a type, declared in its `type` field, that
determines [where it lives](vault.md#where-records-live), which frontmatter
fields it has and what its body contains. A type is defined by a Type record
in `reference/types/` and its schema in `reference/schemas/`. The built-in
types follow, in alphabetical order. Throughout, "in this campaign" means
under the same `campaigns/campaign_N/` as the record, and Content may also be
shared under `content/`.

## Clue

### Description

A GM-known candidate fact tracked through a lifecycle; campaign-specific,
named `C-N-NNNN.md` with the campaign number and a four-digit ordinal.

### Frontmatter

| Field | Value |
| --- | --- |
| `type` | `[[types/Clue]]` |
| `status` | a link to a Status that applies to Clues: `[[Pending]]`, `[[Hinted]]`, `[[Revealed]]`, `[[Abandoned]]`, `[[Dormant]]` or `[[Superseded]]` |
| `text` | non-blank text; its links must be Content in this campaign or shared |
| `subjects` | null (unidentified), `[]` (none) or exactly the records linked in `text`, as a list of links |
| `first_session` | null or a link to the Session in this campaign the Clue was first prepared or used in |
| `last_session` | null or a link to the Session in this campaign of its latest introduction or development; requires `first_session` and may not precede it |
| `superseded_by` | a link to the replacing Clue in this campaign, required when `status` is `[[Superseded]]` and forbidden otherwise; following it from Clue to Clue must never return to the starting Clue |

### Body

Exactly `## Sessions` followed by one `.base` embed; nothing else.

## Content

### Description

A character, place, group, object or piece of setting lore, shared or
campaign-specific. `subtype` is one of `NPC`, `PC`, `Location`, `Faction`,
`Object`, `Lore`.

### Frontmatter

| Field | Value |
| --- | --- |
| `type` | `[[types/Content]]` |
| `subtype` | one of the six subtypes |
| `summary` | short text describing stable identity, or null for a stub |
| `aliases` | list of non-empty strings, `[]`, null or omitted |
| `stats` (NPC) | null, a link to a record, or an `http(s)://` URL |
| `player` (PC) | a link to a Player in this campaign; not null |
| `parent_location` (Location) | null or a link to Location Content, in this campaign or shared; following it from Location to Location must never return to the starting record |
| `members` (Faction) | null (unknown), `[]` (none recorded) or a list of links to PC or NPC Content, in this campaign or shared |
| `campaign_N` | one block per campaign the record has state in |

A `campaign_N` block is a mapping with `first_session` and `last_session`:
both null before any appearance, otherwise links to the earliest and latest
Session of campaign N in the record's Appearances. `N` must be an existing
campaign, and a record under `campaigns/campaign_N/` may only carry that
campaign's block. An Object's block also requires `held_by`: null before
entering play, then a holder, a list of holders (split possession) or `GONE`
(out of play), with `GONE` also allowed inside a list; a holder is a link to
PC, NPC or Faction Content, in campaign N or shared.

### Body

`## Notes`, `## Active Clues` and `## Appearances`, in that order. Active
Clues holds exactly one `.base` embed and nothing else. Appearances is one
list of `- [[S-N-NNN]]: what happened` items, or the single item `- N/A` when
there are none; no other blocks or subheadings. The list runs through
campaigns in ascending order and, within a campaign, in ascending session
order without repeats, and each campaign that appears must have a
`campaign_N` block whose `first_session` and `last_session` are that
campaign's earliest and latest entries.

## Note

### Description

A freeform document: working notes, design notes, session prep, ideas.
Shared or campaign-specific.

### Frontmatter

| Field | Value |
| --- | --- |
| `type` | `[[types/Note]]` |

### Body

Free Markdown.

## Player

### Description

A person at the table; campaign-specific.

### Frontmatter

| Field | Value |
| --- | --- |
| `type` | `[[types/Player]]` |
| `plays` | list of links to PC Content in this campaign; `[]` when unassigned; null and a single link are invalid |

### Body

Free Markdown, possibly empty.

## Reference

### Description

A structural, taxonomic or index record, such as a campaign overview or the
clue index; shared or campaign-specific.

### Frontmatter

| Field | Value |
| --- | --- |
| `type` | `[[Reference]]` |

### Body

Free Markdown, possibly empty.

## Session

### Description

One play session; campaign-specific, named `S-N-NNN.md` with the campaign
number and a three-digit ordinal.

### Frontmatter

| Field | Value |
| --- | --- |
| `type` | `[[types/Session]]` |
| `date` | `YYYY-MM-DD` or null |
| `campaign` | a link to the containing campaign's `reference/Campaign.md` |
| `session_number` | positive integer equal to the ordinal in the filename |
| `aliases` | list of non-blank strings, `[]`, null or omitted |
| `players_absent` | null or a list of links to Players in this campaign |
| `in_game_start_date`, `in_game_end_date` | non-blank text or null |
| `prepared_clues`, `prepared_locations`, `prepared_npcs` | ordered lists of links to Clues in this campaign, and to Location and NPC Content in this campaign or shared; `[]` or omitted selects nothing |

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

A lifecycle state for one type; named for the status. The six shipped
statuses apply to Clues.

### Frontmatter

| Field | Value |
| --- | --- |
| `type` | `[[Status]]` |
| `applies_to` | a link to the Type record the status applies to |

### Body

Free Markdown describing the status.

## Transcript

### Description

Cleaned, attributed speech from one Session; campaign-specific, named after
its Session: `S-N-NNN Transcript.md`.

### Frontmatter

| Field | Value |
| --- | --- |
| `type` | `[[types/Transcript]]` |
| `session` | a link to the Session in this campaign the transcript records, which the filename must match |

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

The definition of a record type; named for the type. `Type.md` and
`Status.md` are themselves Type records.

### Frontmatter

| Field | Value |
| --- | --- |
| `type` | `[[Type]]` |
| `directories` | mapping of `shared` and/or `campaign` to a relative path without `..` or a leading `/`; every declared directory must exist |

### Body

Free Markdown, conventionally the type's documentation.
