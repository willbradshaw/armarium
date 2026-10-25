---
name: process-session
description: Takes one played Session in this Armarium vault from a recording, a Transcript or the GM's notes to a written-up Session and updated records, stopping for the GM's approval at each stage.
---

# Process a played Session

This procedure runs the whole of the work that follows a Session: the
Transcript, the write-up, and the records the Session touches. Each stage is a
procedure of its own, and this one puts them in order.

You need two things:

- the Session, or the campaign and number of one that has no record yet;
- a source: a recording, raw speech-to-text, the Session's Transcript, or the
  GM's notes.

Run the commands from the vault root, or add `--vault PATH`.

If `.agents/skills/process-session/addenda/` exists, read every file in it before you
start. Each adds to this procedure, for an extension the vault has enabled or
for the vault itself, and applies as if it were written here. Where an addendum
and this file disagree, follow the addendum; where two addenda disagree, follow
`vault.md`, the vault's own.

## Checkpoints

Stages 2 and 3 each show the GM something and stop, as their own procedures
describe. Go on from one only when the GM says to, in their own words.

- An answer or a correction is not approval. Apply it, show what changed and
  wait again.
- Never set your own condition for going on, such as "once you answer this I
  will continue".
- What you write into the Transcript or the Session is the text the GM last
  saw.

Stage 4 does not stop first. Once the write-up is approved and written, go
straight on to it.

## 1. Work out where to start

```sh
armarium find "S-N-NNN"
armarium find "S-N-NNN Transcript"
```

If `find` shows that the Session has no record, check its number with the GM
and create it:

```sh
armarium add session --campaign N --number NNN
```

Read the Session.

| You have | Start at |
| --- | --- |
| a recording or raw speech-to-text, and no Transcript | stage 2 |
| a Transcript, or the GM's notes | stage 3 |
| a Session whose Events the GM has already approved | stage 4 |

Tell the GM where you are starting and why.

## 2. The Transcript

Follow `.agents/skills/create-transcript/SKILL.md`. It ends when the GM says
the Transcript is done.

## 3. The write-up

Follow `.agents/skills/write-up-session/SKILL.md`. It ends with the approved
text written into the Session.

From here on, the Session's Events are the source for everything. Do not work
from the draft, the Transcript or your memory of them.

## 4. The records the Session touches

Follow `.agents/skills/update-session-records/SKILL.md`. It updates each
record where the Events make clear what should change, and reports the rest
for the GM to decide.

## 5. Report

Say which stages you ran, where the Transcript and the Session are, and which
working files you left in `.scratch/`. Repeat what the last stage reported as
still for the GM to decide.
