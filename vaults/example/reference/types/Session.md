---
type: "[[Type]]"
directories: { campaign: sessions }
---
Records with `type: "[[types/Session]]"` are play-session records containing preparation and actual play notes, including events, interactions, and rewards.

Create a Session with `armarium add session --campaign N`, which starts from
[[templates/Session]] and fills in `session_number` and the campaign link.

Campaign 1's Sessions live under `campaigns/campaign_1/sessions/`, named
`S-1-001.md`, `S-1-002.md`, etc.; campaign 2's live under
`campaigns/campaign_2/sessions/`, named `S-2-001.md`, and so on.

`prepared_clues`, `prepared_locations` and `prepared_npcs` are ordered link lists
(use `[]` for none; omitted lists also select nothing). Clues must belong to this
campaign; Locations and NPCs must be matching Content subtypes, shared or in this
campaign. List order is display order. Preparation shows current Clue `text` and
Content `summary`, including in past Sessions. Put session-specific instructions
in Scene notes and actual play under Events. Secrets & Clues, Locations and
Important NPCs each contain exactly one Base embed and no additional text.

Always qualify campaign overview links, for example
`[[campaign_1/reference/Campaign]]`.

## Preparation and play

A Session has two halves. Preparation is what the GM plans before play: it
holds intent, not history, and nothing in it has happened until the Events
say so. Notes is what happened at the table, written afterwards.

The halves are kept apart. Preparation is not rewritten to match what was
played: a scene that never came up stays in Preparation and out of Events, and
something the players did unprompted appears in Events alone.

## What a Session holds

### Frontmatter

| Field | Holds |
| --- | --- |
| `campaign`, `session_number` | which Session of which campaign this is. |
| `aliases` | other names the Session goes by. |
| `date` | the real date of play. It is empty while the Session is unscheduled. |
| `in_game_start_date`, `in_game_end_date` | the Dates in the setting on which play began and ended. A Session usually begins on the Date the previous one ended, unless that one ended with a night's rest, in which case it begins on the next. It ends on a later Date only where the Events show time passing, such as a night's rest or a voyage. |
| `players_absent` | the Players who missed the Session, known once it is played. |
| `prepared_clues` | the Clues that could come up: open Clues whose subjects are within the party's reach. A prepared Clue keeps its status until play changes it. |
| `prepared_locations`, `prepared_npcs` | the places and characters the GM expects to use, whether or not play reaches them. |

### Preparation

| Section | Holds |
| --- | --- |
| Starting scene | the one scene the Session opens on. If the previous Session ended on a cliffhanger, it is usually picked up here. |
| Other scenes | other scenes that may come up, briefly summarized. |
| Secrets & Clues, Locations, Important NPCs | views of the three prepared lists. Nothing is written here. |
| Scene notes | what the GM needs to run this Session's scenes, such as how a Clue might surface. |
| Encounters | the fights and contests prepared. |
| Prepared rewards | what the party could gain. |

### Notes

| Section | Holds |
| --- | --- |
| Preamble | who attended, and anything else to know before the Events. |
| Events | what happened in play, in order. |
| Rewards | what the party gained. Loot lists each item and who acquired it. |

## Events and Loot

**Events** are the vault's account of what happened in play, and other records
follow them: an Appearances entry or a Clue's status rests on what the Events
say. Once the GM has reviewed them they are the authority. A later correction
is made to the Events first, and then to what follows from them.

- Each item is usually one beat of play, such as a scene, a conversation or a
  fight, told in the past tense. It says who did what and how it came out. A
  scene with many parts can take a sub-item for each.
- Only what happened at the table belongs. Something planned, expected,
  ordered or talked about has not happened. Neither has a prepared scene that
  was not played.
- Each item can be read on its own. It names what it speaks of and links it,
  so that `armarium trace` finds the Session from that record. Where something
  named has no record, a stub is created; a name is not left as plain text to
  avoid one.
- An item says what happened in the world, not the rules or dice that decided
  it.
- A fact is told once. An item refers to what earlier Events hold and does not
  tell it again. A discovery stays with the Session and the character that
  made it.
- A text read aloud at the table is quoted as a blockquote.
- Where play hinted or revealed a Clue, the item says so and links the Clue.
- Earlier Sessions' Events are the model for length and voice.

**Loot** is a snapshot of the table on the night. It is not updated when an
item later changes hands; the item's own record says who holds it now.
Acquired by is left empty for something the party holds in common. Something
the party passed straight on to someone else is an event, not loot.

## Schema

A Session’s frontmatter requires `type`, `date`, `campaign`, `session_number`,
`players_absent`, `in_game_start_date` and `in_game_end_date`. The campaign
links to its Reference record, and the session number is a positive integer. Date
is `YYYY-MM-DD` or null when unscheduled. In-game dates link to Content with subtype Date, shared or in the same campaign,
or are null when unrecorded.

`players_absent` is a list of Player links, `[]` for no absences, or null when
unrecorded. Optional `aliases` is a list of nonblank strings, an empty list, or
null. The body keeps the template's level-one and level-two headings in order
through Rewards. Sections may be empty; Loot and other subsections are optional.

See the [Session schema](../schemas/session.schema.json).
