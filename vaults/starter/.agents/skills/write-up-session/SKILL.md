---
name: write-up-session
description: Writes what happened in a played Session into its Session record in this Armarium vault, from a Transcript or the GM's notes, after the GM approves the text. Edits only the Session and creates stubs for new names.
---

# Write up a Session

This procedure writes the Notes half of one Session after it is played: its
Events, its Loot and the frontmatter that play settles. It does not update the
other records the Session touches.

You need two things:

- the Session, which must already exist;
- a source that says what happened: the Session's Transcript, or the GM's
  notes, as a file or in their request.

Run the commands from the vault root, or add `--vault PATH`. Keep working files
in `.scratch/`, which Git ignores. Never move, edit or delete the source.

## 1. Find the Session and the source

```sh
armarium find "S-N-NNN"
armarium find "S-N-NNN Transcript"
```

Read the whole Session. If its Events are already written, stop and ask
whether to replace them, add to them or leave them.

If there is a Transcript and the GM gave notes as well, use both, and ask
where they disagree.

## 2. Read the Type record and the Session before

Read `reference/types/Session.md`. It says what Events, Loot and the
frontmatter hold, and what does not count as having happened. It is the
authority for this vault.

Read the previous Session's Events. They show how this vault writes Events,
and what is already recorded and need not be told again.

## 3. Draft

Write a draft to `.scratch/S-N-NNN draft.md` with these parts:

- **Events**, as they would appear in the Session;
- **Loot**, as rows of the Session's table;
- **Frontmatter**: `players_absent`, `in_game_start_date` and
  `in_game_end_date`, each with the line of the source that supports it, or
  "not stated";
- **Clues**: for each Clue in `prepared_clues`, whether the source shows it
  hinted, revealed or untouched, with the supporting line. Do not change the
  Clue;
- **Questions**: whatever the source leaves unclear and the write-up depends
  on.

Mark any statement that rests on an uncertain part of the source with `(?)`,
and raise it under Questions.

## 4. Check the draft against the source

Read each item of the draft beside the lines of the source it comes from, not
from memory:

- Did it happen at the table, as the Type record defines that?
- Is it who the source says it was?
- Does it say more than the source does?

Then run `armarium find` on each name in the draft. Link the names that have
records by their filenames. List the names that have none: they will become
stubs in step 6, so tell the GM what type you would give each.

## 5. Show the GM and stop

Show the GM the draft in full, exactly as it would be written, with the
questions and the list of new names.

Then stop and wait. Apply each answer or correction to the draft, and to
nothing else. Answers are not approval: after applying them, show what changed
and wait again. Go on only when the GM approves the text in so many words.

## 6. Write the Session

Follow `.agents/skills/update-record/SKILL.md` for the Session, with the
approved draft as its source:

- Events and Loot go in as approved, word for word.
- Set the frontmatter the GM confirmed, and leave the rest as it is.
- Leave the Preparation half exactly as it is.
- Its step 5 creates a stub for each new name. Use the types the GM agreed.

## 7. Report

Say that the Session is written, which stubs you created, and what the draft
said about each prepared Clue.

The records the Session touches are not yet updated: the characters and places
that appeared, the objects that changed hands and the Clues that play
developed. Say so. From here on the Session's Events are their source, not the
draft or the Transcript.
