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
records intent, not history, and nothing in it has happened until the Events
say so. Notes is what happened at the table, written afterwards.

The halves are kept apart. Preparation is not rewritten to match what was
played: a scene that never came up stays in Preparation and out of Events, and
something the players did unprompted appears in Events alone.

## What Preparation holds

| Part | Holds |
| --- | --- |
| Starting scene | the one scene the Session opens on. A cliffhanger from the previous Session belongs here. |
| Other scenes | the scenes that may come up, one line each. They are a menu, not a sequence. |
| `prepared_clues` | the Clues that could come up: open Clues whose subjects are within the party's reach. Preparing a Clue does not hint it. |
| `prepared_locations`, `prepared_npcs` | the places and characters the GM expects to use, whether or not play reaches them. |
| Scene notes | what the GM needs to run this Session's scenes, such as how a Clue might surface. |
| Encounters | the fights and contests prepared. |
| Prepared rewards | what the party could gain. What they took is recorded under Rewards. |

`date` is the real date of play. `in_game_start_date` is usually the previous
Session's `in_game_end_date`; time passes between Sessions only when the GM
says so. `players_absent` and `in_game_end_date` are not known until the
Session is played.

## What carries over

Much of a Session's preparation follows from the Sessions before it:

- how the previous Session ended, when it left something unresolved;
- scenes, encounters and rewards that were prepared, not played, and could
  still happen;
- Clues that are still Pending or Hinted, where play is heading towards their
  subjects;
- what characters promised or threatened, and deadlines that now fall due;
- the places and characters the party is in the middle of dealing with.

What play has overtaken is dropped: a scene whose moment has passed, or a Clue
that no longer fits what was established. An outdated Clue is not reworded;
its status changes, as [[types/Clue]] describes.

Carrying over copies what earlier Sessions already hold. Anything else in
Preparation is new, and what is new is the GM's to decide.

## What Notes holds

| Part | Holds |
| --- | --- |
| Preamble | table business: who attended, and anything said before play began. |
| Events | what happened in play, in order. |
| Loot | what the party took this Session, and who took it. |

**Events** are the vault's record of what happened, and other records follow
them: an Appearances entry or a Clue's status rests on what the Events say.

- Each item is one beat of play, such as a scene, a conversation or a fight.
  It says who did what and how it came out.
- Only what happened at the table belongs. Something planned, expected,
  ordered or talked about has not happened. Neither has a prepared scene that
  was not played.
- Every record named is linked, so that `armarium trace` finds the Session
  from it. Where something named has no record, a stub is created; a name is
  not left as plain text to avoid one.
- An item says what happened in the world, not the rules or dice that decided
  it.
- Where play hinted or revealed a Clue, the item says so and links the Clue.
- Earlier Sessions' Events are the model for length and voice.

The Events are written from a source, such as a Transcript or the GM's notes,
and state nothing the source does not. Once the GM has reviewed them they are
the authority: a later correction is made to the Events first, and then to
the records that follow from them.

**Loot** is a snapshot of the table on the night. It is not updated when an
item later changes hands; the item's own record says who holds it now.
Something the party passed straight on to someone else is an event, not loot.

`players_absent` lists the Players who were not there. `in_game_end_date`
moves on from the start date only where the Events show time passing, such as
a night's rest or a voyage.

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
