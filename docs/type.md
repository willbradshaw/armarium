# Types

The built-in record types, one section each: the frontmatter fields, what
their values may be, the required body, and the rules that hold between
records. What every record shares is in [Records](record.md); where each
type's records live is in [Vault layout](vault.md). Links must be canonical;
"in this campaign" means under the same `campaigns/campaign_N/`, and Content
may also be shared under `content/`.

## Content

A character, place, group, object or piece of setting lore; shared under
`content/` or campaign-specific. `subtype` is one of `NPC`, `PC`, `Location`,
`Faction`, `Object`, `Lore`.

| Field | Value |
| --- | --- |
| `type` | `[[types/Content]]` |
| `subtype` | one of the six subtypes |
| `summary` | short text describing stable identity, or null for a stub |
| `aliases` | list of non-empty strings, `[]`, null or omitted |
| `stats` (NPC) | null, a link to a record, or an `http(s)://` URL |
| `player` (PC) | a link to a Player in this campaign; not null |
| `parent_location` (Location) | null or a link to Location Content, in this campaign or shared |
| `members` (Faction) | null (unknown), `[]` (none recorded) or a list of links to PC or NPC Content, in this campaign or shared |
| `campaign_N` | one block per campaign the record has state in; see below |

**Campaign blocks.** `campaign_N` is a mapping with `first_session` and
`last_session`: both null before any appearance, otherwise links to the
earliest and latest Session of campaign N in the record's Appearances. `N`
must be an existing campaign; a record under `campaigns/campaign_N/` may only
carry that campaign's block. An Object's block also requires `held_by`: null
before entering play, then a holder, a list of holders (split possession) or
`GONE` (out of play), with `GONE` also allowed inside a list; a holder is a
link to PC, NPC or Faction Content, in campaign N or shared.

**Body.** `## Notes`, `## Active Clues` and `## Appearances`, in that order.
Active Clues holds exactly one `.base` embed and nothing else. Appearances is
one list of `- [[S-N-NNN]]: what happened` items, or the single item `- N/A`
when there are none; no other blocks or subheadings. The list runs through
campaigns in ascending order and, within a campaign, in ascending session
order without repeats, and each campaign that appears must have a
`campaign_N` block whose `first_session`/`last_session` are that campaign's
earliest and latest entries.

**Chains.** Following `parent_location` from Location to Location must never
return to the starting record.

## Clue

A GM-known candidate fact tracked through a lifecycle; campaign-specific,
named `C-N-NNNN.md` with the campaign number and a four-digit ordinal.

| Field | Value |
| --- | --- |
| `type` | `[[types/Clue]]` |
| `status` | a link to a Status that applies to Clues: `[[Pending]]`, `[[Hinted]]`, `[[Revealed]]`, `[[Abandoned]]`, `[[Dormant]]` or `[[Superseded]]` |
| `text` | non-blank text; its links must be Content in this campaign or shared |
| `subjects` | null (unidentified), `[]` (none) or exactly the records linked in `text`, as a list of links |
| `first_session` | null or a link to the Session in this campaign the Clue was first prepared or used in |
| `last_session` | null or a link to the Session in this campaign of its latest introduction or development; requires `first_session` and may not precede it |
| `superseded_by` | a link to the replacing Clue in this campaign, required when `status` is `[[Superseded]]` and forbidden otherwise |

**Body.** Exactly `## Sessions` followed by one `.base` embed; nothing else.

**Chains.** Following `superseded_by` must never return to the starting Clue.

## Session

One play session; campaign-specific, named `S-N-NNN.md` with the campaign
number and a three-digit ordinal.

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

**Body.** The template's headings in order: `# Preparation` with
`## Starting scene`, `## Other scenes`, `## Secrets & Clues`, `## Locations`,
`## Important NPCs`, `## Scene notes`, `## Encounters`, `## Prepared rewards`;
then `# Notes` with `## Preamble`, `## Events`, `## Rewards`. Secrets & Clues,
Locations and Important NPCs each hold exactly one `.base` embed and nothing
else; the other sections are free Markdown, and subsections such as
`### Loot` are optional.

## Transcript

Cleaned, attributed speech from one Session; campaign-specific, named after
its Session: `S-N-NNN Transcript.md`.

| Field | Value |
| --- | --- |
| `type` | `[[types/Transcript]]` |
| `session` | a link to the Session in this campaign the transcript records; the filename is that Session's plus ` Transcript` |

**Body.** A run of titled `## ` sections and nothing before the first. Each
section holds exactly one bullet list and nothing else. Each item is one
utterance: a single paragraph opening with a speaker tag, a space and text —
`- [GM] The bell rings.` — where the tag names the GM, the table, a character
(`[Esme]`, `[Darian — Martin]`) or an uncertain speaker (`[Player?]`, `[?]`).
After the tag, square brackets may appear only inside wikilinks. A long
utterance may wrap onto further lines of its item.

## Player

A person at the table; campaign-specific, under `reference/players/`.

| Field | Value |
| --- | --- |
| `type` | `[[types/Player]]` |
| `plays` | list of links to PC Content in this campaign; `[]` when unassigned; null and a single link are invalid |

**Body.** Free Markdown, possibly empty.

## Note

A freeform document: working notes, design notes, session prep, ideas.
Shared under `notes/` or campaign-specific.

| Field | Value |
| --- | --- |
| `type` | `[[types/Note]]` |

**Body.** Free Markdown.

## Reference

A structural, taxonomic or index record, such as a campaign overview or the
clue index; under `reference/` or a campaign's `reference/`.

| Field | Value |
| --- | --- |
| `type` | `[[Reference]]` |

**Body.** Free Markdown, possibly empty.

## Type

Defines a record type; under `reference/types/`, named for the type. `Type.md`
and `Status.md` are themselves Type records.

| Field | Value |
| --- | --- |
| `type` | `[[Type]]` |
| `directories` | mapping of `shared` and/or `campaign` to a relative path without `..` or a leading `/`; every declared directory must exist |

**Body.** Free Markdown, conventionally the type's documentation.

## Status

Defines a lifecycle state for one type; under `reference/statuses/`, named
for the status.

| Field | Value |
| --- | --- |
| `type` | `[[Status]]` |
| `applies_to` | a link to the Type record the status applies to |

**Body.** Free Markdown describing the status.
