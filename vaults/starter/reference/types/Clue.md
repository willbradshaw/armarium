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

A Clue states a candidate fact about the world that the players do not yet
fully know and can come to learn. Three things mark one out:

- **It has a hidden state.** The players can learn it in part or in full. What
  happens openly in play, such as an NPC doing or saying something in front of
  the party, is known at once and is recorded in the Session's Events. When
  what is said is itself obscure, the Clue is what it means, and the saying is
  a hint.
- **It is about the world, not a moment of play.** It concerns a condition,
  an allegiance, a secret, a cause, or a past event that was concealed, such as
  "the warehouse fire was set deliberately". "The party met the harbourmaster
  on the quay" is a moment of play, recorded in the Session's Events.
- **It can span Sessions.** It can be hinted in one Session and revealed in a
  later one.

As a test, a fact that a Session's Events and its subjects' Notes would hold in
full without a Clue is not a Clue.

Until the players learn it, a Clue is not canon: the GM can change it or drop
it. It becomes established only once it is revealed in play.

## One fact, one Clue

A fact that a Clue already states is developed in that Clue, not stated again
in a new one. `armarium trace` on one of its subjects lists the Clues that link
to it.

## Status

Each status is a record in `reference/statuses/` that says what it means. A
Clue starts as Pending, and its status follows what the players have learned.
Preparing a Clue for a Session does not hint it.

`last_session` is the latest Session in which play developed the Clue, whether
or not its status changed then.

## When a Clue is revealed

A Revealed Clue no longer appears under its subjects' Active Clues, so its fact
belongs in the Notes of each subject it concerns, with a link back to the Clue.
A subject that the fact only touches in passing, or a bare stub, need not take
it. The Clue itself stays, Revealed.

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
