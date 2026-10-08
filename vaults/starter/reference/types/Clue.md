---
type: "[[Type]]"
directories: { campaign: clues }
---
Records with `type: "[[types/Clue]]"` are persistent GM-known candidate facts not fully known to the players. A clue may be abandoned without revelation and never become canon. Its status tracks its lifecycle, and its subjects link to relevant entities.

Create a Clue with `armarium add clue --campaign N`, which starts from
[[templates/Clue]]. Clue text belongs in the `text` property. The body contains only the Sessions heading and its embedded view, with no
additional commentary.

Campaign 1's Clues live under `campaigns/campaign_1/clues/`, named `C-1-0001.md`,
`C-1-0002.md`, etc.; campaign 2's live under `campaigns/campaign_2/clues/`, named
`C-2-0001.md`, and so on. The Sessions view derives its scope from the containing
campaign folder.

## What counts as a Clue

A Clue is a fact about how the world is that the players do not yet fully know.
Make one only when the fact:

- **has a hidden state.** Something the players can learn in part or in full.
  A fact that is wholly known the moment it happens in play, such as an NPC
  openly doing or saying something, is an event: it belongs in the Session's
  Events. Where what is said is itself obscure, the Clue is what it means, and
  the saying is a hint.
- **lasts.** A condition, allegiance, secret or cause, not a single happening.
- **outlives one Session.** If the only way to state it is "this happened in
  that Session", it is Session content.

A test: if the Session's Events and the subjects' Notes would hold the fact
fully without the Clue, it should not be a Clue.

## Before creating one

Check whether a Clue already states the fact. `armarium trace` on its most
distinctive subject lists the Clues whose `text` links to that record. If one
states the same fact, update that Clue, for example its status or
`last_session`, and do not create another.

## Status

Each status is a record in `reference/statuses/` that says what it means. A
new Clue starts as Pending. Change the status only when the GM decides to, or
when a played Session's Events show the change; preparing a Clue for a Session
does not hint it.

Update `last_session` whenever play develops the Clue, even when its status
stays the same.

## When a Clue is revealed

A Revealed Clue no longer shows under its subjects' Active Clues, so the fact
moves into their records: add it to the Notes of each subject it concerns, with
a link back to the Clue. A subject that the fact only touches in passing, or
that is a bare stub, can be skipped. The Clue itself stays, Revealed.

## Schema

A Clue’s frontmatter requires `type`, `status`, nonblank `text`, `subjects`,
`first_session` and `last_session`. Status links to one of the six supplied
statuses. Every link in `text` must be a Content record in this campaign or in
shared `content/`, and `subjects` lists exactly those records: null means
unidentified, and `[]` means none recorded.

`first_session` links to the first Session for which the Clue was prepared or
used; `last_session` links to its latest introduction or development in play.
Both may be null. Preparation alone can set first; setting last requires first.
Superseded Clues also require a replacement Clue link in `superseded_by`;
Clues in any other status must not carry that field at all.

The body contains only `## Sessions` followed by one Base embed, as in the
template. No additional commentary or views belong here.

See the [Clue schema](../schemas/clue.schema.json).
