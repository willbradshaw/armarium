---
name: update-session-records
description: Brings the records that a played Session touches up to date with its Events in this Armarium vault. Lists them for the GM's approval, then updates each one.
---

# Update the records a Session touches

This procedure follows a Session's write-up. It finds the records that the
Session's Events bear on, such as the characters and places that appeared, the
objects that changed hands and the Clues that play developed, and brings each
up to date. It does not change the Session.

You need the Session, with Events that the GM has approved. The Events are the
source for everything here. Do not work from a draft of them, a Transcript or
your memory of either.

Run the commands from the vault root, or add `--vault PATH`. Keep working files
in `.scratch/`, which Git ignores.

## The rule: the GM approves the list

Change no record until the GM has approved the list of records to change.

- An answer or a correction is not approval. Apply it, show what changed and
  wait again.
- Never set your own condition for going on, such as "once you answer this I
  will continue".

## 1. List what the Session touches

A played Session touches the records its Notes half links to. List the
Session's links:

```sh
armarium trace "campaigns/campaign_N/sessions/S-N-NNN.md" --outbound
```

The second field of each line says where the link sits. Sort the records into:

- **Linked from Notes:** linked from the Preamble, Events or Loot.
- **Prepared Clues:** every Clue in `prepared_clues`, linked from Notes or not.
- **Prepared only:** linked only from Preparation or the `prepared_` lists.
  These were planned and not touched. Leave them out.

Then run the same command on each record linked from Notes that was created
for this Session's write-up. A record that a new record links to may have
something to gain from it.

A link is not proof that a record needs to change. For each record linked from
Notes, read the lines of the Events that link it, then read its Type record
for what follows from a Session. This is what usually follows:

| Record | What may follow |
| --- | --- |
| Content | an Appearances entry, and `first_session` and `last_session` in its campaign block, where the Events show an appearance as `reference/types/Content.md` defines one for its subtype. A character only spoken of has not appeared. |
| Object or Gear | its holder, where the Events or Loot show it changing hands. |
| Clue | its status and `last_session`, where play hinted or revealed it, as `reference/types/Clue.md` describes. Check the prepared Clues, and any Clue whose subjects the Events link. A prepared Clue that never came up is unchanged. |
| Date | an Appearances entry on each Date the Session's in-game dates link. |
| A stub created for the write-up | what the Events say about it, and nothing more. |

Read enough of each record to see whether it already holds this Session.

Write the list to `.scratch/S-N-NNN touched.md`, a line for each record: what
you propose, and the line of the Events it rests on. Sort it into:

- **appeared:** records you propose to update;
- **mentioned only:** records the Notes link that you propose to leave, such
  as a character who was spoken of;
- **Clues:** each prepared Clue and any other Clue in play, with what the
  Events show (hinted, revealed or nothing) and the status you would give it;
- **cannot judge:** records where the Events do not settle it.

Change no record in this step.

## 2. Show the GM and stop

Show the GM the list as it stands in the file.

Then stop and wait. The GM may strike records, add some, move one between
"appeared" and "mentioned only", and settle each Clue. Apply each change to the
file, show what changed and wait again.

## 3. Update the records

Take the approved list one record at a time, and mark each line in the file
when its record is done or the GM says to skip it:

- **An existing record:** follow `.agents/skills/refresh-record/SKILL.md`.
- **A stub created for the write-up, or a Clue whose status the GM settled:**
  follow `.agents/skills/update-record/SKILL.md`, with the Session's Events
  and the GM's decision as the source. When a Clue is revealed, refresh each
  of its subjects afterwards, as its Type record describes.

Both procedures edit one record and report what they left alone. Keep those
reports.

When you write an Appearances entry:

- Write it from the Session's Events as they now stand.
- Keep it to a clause or a short sentence on what this entity did, or what
  happened to it. It points to the Session; it does not retell it.
- Make it readable on its own. On a character's record the character is the
  one acting. On a place's record say who acted there: "The crew anchored
  here overnight", not "Anchored overnight".
- Add nothing the Events do not say.

A fact that only a Clue holds stays in the Clue until the Clue is revealed.
Do not copy it into the Notes of the Clue's subjects.

If the GM corrects the Events at any point, change the Session first. Then
run step 1 again, and check every entry you wrote for this Session against
the corrected lines.

## 4. Check, validate and report

Read each record you changed once more, beside the Events:

- Does each `last_session` you set have an Appearances entry for this Session?
- Does each entry say only what the Events say?
- Did anything go into a record's Notes that happened once, or that only a
  Clue holds?

```sh
armarium validate .
```

Fix every error your changes introduced. If the vault had errors before you
started, report them; do not fix them unasked.

Then report, record by record, what changed and which line of the Events
supports it. List what the record procedures left alone, the disagreements
they found, and what is still for the GM to decide. Leave the file in
`.scratch/`.
