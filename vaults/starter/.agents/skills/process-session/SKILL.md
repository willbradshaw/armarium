---
name: process-session
description: Takes one played Session in this Armarium vault from a recording, a Transcript or the GM's notes to a written-up Session and updated records, stopping for the GM's approval at each stage.
---

# Process a played Session

This procedure runs the whole of the work that follows a Session: the
Transcript, the write-up, and the records the Session touches. Each stage is a
procedure of its own, and this one puts them in order.

You need two things:

- the Session, which must already exist;
- a source: a recording, raw speech-to-text, the Session's Transcript, or the
  GM's notes.

Run the commands from the vault root, or add `--vault PATH`.

## Checkpoints

Stages 2, 3 and 5 each end by showing the GM something and stopping. Go on to
the next stage only when the GM says to, in so many words.

- An answer or a correction is not approval. Apply it, show what changed and
  wait again.
- Never set your own condition for going on, such as "once you answer this I
  will continue".
- What you write into a record is the text the GM last saw.

## 1. Work out where to start

```sh
armarium find "S-N-NNN"
armarium find "S-N-NNN Transcript"
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

## 4. List what the Session touches

Read `reference/types/Session.md` on what a played Session touches, then list
the Session's links:

```sh
armarium trace "campaigns/campaign_N/sessions/S-N-NNN.md" --outbound
```

The second field of each line says where the link sits. Sort the records into:

- **Touched:** linked from the Notes half, or a stub created in stage 3.
- **Prepared Clues:** every Clue in `prepared_clues`, touched or not.
- **Not touched:** linked only from Preparation. Leave these out.

For each touched record, read the lines of the Events that link it and the
part of its Type record that the Session's Type record points to, and note
what may need to change and why. Read enough of the record to see whether it
already holds this Session. For each prepared Clue, note what the Events show:
hinted, revealed or nothing, with the line.

Change nothing in this stage.

## 5. Show the GM and stop

Show the GM the list:

- each record you propose to update, with the reason in a clause;
- each record the Session links that you propose to leave, with the reason;
- each prepared Clue, with your reading of the Events and the status you would
  give it;
- what you cannot judge.

Then stop and wait. The GM may strike records, add some and settle each Clue.

## 6. Update the records

Take the approved list one record at a time:

- **An existing record:** follow `.agents/skills/refresh-record/SKILL.md`.
- **A stub from stage 3, or a Clue whose status the GM settled:** follow
  `.agents/skills/update-record/SKILL.md`, with the Session's Events and the
  GM's decision as the source. When a Clue is revealed, refresh each of its
  subjects afterwards, as its Type record describes.

Both procedures edit one record and report what they left alone. Keep those
reports.

If the GM corrects the Events at any point, change the Session first. Then
run stage 4 again and refresh each record that the corrected lines link.

## 7. Validate and report

```sh
armarium validate .
```

Fix every error your changes introduced. If the vault had errors before you
started, report them; do not fix them unasked.

Then report, record by record, what changed and which line of the Events
supports it. List what the record procedures left alone, the disagreements
they found, and what is still for the GM to decide.
