---
name: write-up-session
description: Writes what happened in a played Session into its Session record in this Armarium vault, from a Transcript or the GM's notes. Drafts the text, checks it against the source, and writes it only after the GM approves it.
---

# Write up a Session

This procedure writes the Notes half of one Session after it is played: its
Preamble, its Events, its Loot and the frontmatter that play settles. It does
not update the other records the Session touches.

You need two things:

- the Session, which must already exist;
- a source that says what happened: the Session's Transcript, or the GM's
  notes, as a file or in their request.

Run the commands from the vault root, or add `--vault PATH`. Keep working files
in `.scratch/`, which Git ignores. Never move, edit or delete the source.

## The rule: the GM approves the exact text

Nothing taken from the source reaches the Session, or any other record, until
the GM has approved the text that will be written.

- An answer to a question is not approval. Apply it to the draft, show what
  changed, and wait again.
- Never set up a condition for going on, such as "once you answer this I will
  write it up". Going on needs the GM to say so in their own words.
- The text you write must be the text the GM last saw, word for word.

The reason is that other records follow the Events. A mistake approved by
nobody spreads to every character and place the Session touched.

## 1. Find the Session and the source

```sh
armarium find "S-N-NNN"
armarium find "S-N-NNN Transcript"
```

Read the whole Session. If its Events are already written, stop and ask
whether to replace them, add to them or leave them.

If there is a Transcript and the GM gave notes as well, use both, and ask
where they disagree.

## 2. Read what the draft depends on

- `reference/types/Session.md`. It says what each section of Notes holds and
  how Events are written. It is the authority for this vault.
- The Session's Preparation, and each Clue in its `prepared_clues`.
- The Events of the two or three Sessions before this one. They show how this
  vault's Events read, and what has already been told and should not be told
  again. When unsure how to write a scene, find one like it there and follow
  it.

## 3. Draft

Write the draft to `.scratch/S-N-NNN draft.md`, with these parts in order.

**Events.** Written as they will appear in the Session, in the form and at
the length the Type record and the earlier Sessions show. The GM reviews this
very text. In writing it:

- Write complete sentences in the past tense, one to three to an item.
- Give a scene with many parts, such as a negotiation, a parent item and one
  sub-item for each point. Do not put unrelated matters in one item.
- Make each item readable on its own. Do not write "the plan" or "the letter"
  where the reader would need the Session to know which: name it and link it.
- Where a record exists, link it. Do not describe around it.
- Leave out what was only planned, expected or talked about.
- Keep a discovery with the character who made it. Telling someone else a
  known fact is the telling, not a new discovery.
- Do not retell what earlier Events hold. Refer to it.
- Leave out rules, dice and numbers, and say what happened in the world: "the
  blast badly burned his hand", not the damage. Leave out talk about the game
  itself, or say at most what the party discussed.
- Fold the setting-up of a moment into the item where it pays off. Give a fight
  one item unless a turn of it mattered.
- Quote a text read aloud at the table word for word, as a blockquote. If the
  Preparation already holds the text, refer to it there.
- Avoid a label before a colon ("The upshot:"), a clause hung on the end of a
  sentence with "with", a passive that hides who acted, and a chain of three
  or more clauses. If shortening an item makes it unclear, put the words back.

**Preamble.** Who attended and who was absent, and any table business the
source shows.

**Clues.** First a table with a row for each Clue in `prepared_clues`: the
Clue, its status now, and the change you propose or "no change". Then one line
for each, saying whether the source shows it hinted, revealed or untouched,
with the line of the source that shows it. Add any other Clue that play
developed. Do not change a Clue.

**On stage.** The characters who appeared, with a line on what each did; then
the characters who were only mentioned. The places the party went; a place
only spoken of does not count.

**Loot.** A line for each item: where it came from and who took it. Say which
items belong in the Events and not in Loot, as the Type record describes.

**Frontmatter.** `players_absent`, `in_game_start_date` and
`in_game_end_date`, each with the line of the source that supports it, or "not
stated". Give an end Date later than the start only where the Events show time
passing. When in doubt, stay on the same Date and ask.

**Questions.** Number everything the source leaves unclear and the write-up
depends on: an outcome, whether a day ended, how to read a scene.

**GM's answers.** Empty for now. Step 5 fills it.

Mark any statement that rests on an uncertain part of the source with `(?)`,
and raise it under Questions.

## 4. Check the draft against the source

Read each item of the draft beside the lines of the source it comes from, not
from memory. A draft can embellish.

- Did it happen at the table? An order the party gave is not the scene of it
  being carried out.
- Is it who the source says it was, and did that character start it?
- Does it say more than the source does: a motive, a detail, an outcome?

Then read the draft beside the previous Session's Events. Does it contradict
them, or tell again what they hold?

Then run `armarium find` on each name in the draft. Link the names that have
records by their filenames. List the names that have none: they will become
stubs in step 6, so tell the GM what type you would give each.

## 5. Show the GM and stop

Show the GM the draft in full, exactly as it would be written, with the
questions and the list of new names.

Then stop and wait. For each answer or correction:

- apply it to the draft, and to nothing else;
- write it under GM's answers, against the number of its question, so that
  the draft holds what was decided;
- show the GM the changed text, or the exact change, and wait again.

Go on only when the GM approves the text in their own words.

## 6. Write the Session

Follow `.agents/skills/update-record/SKILL.md` for the Session, with the
approved draft as its source:

- Preamble, Events and Loot go in as approved, word for word.
- Set the frontmatter the GM confirmed, and leave the rest as it is. Where an
  in-game Date has no record yet, create it by following the same skill.
- Leave the Preparation half exactly as it is.
- Its step 5 creates a stub for each new name. Use the types the GM agreed.

Leave the draft in `.scratch/`. It is the account of what was decided.

## 7. Keep the GM's rulings on style

If the GM corrected how you wrote the Events, or what you counted as an event,
the same correction will be needed next time. Put each one as a general rule,
without quoting the text that prompted it, and propose adding it to the
Session Type record where it describes Events. Add it only if the GM agrees.

## 8. Report

Say that the Session is written, which stubs you created, and what the draft
said about each prepared Clue.

The records the Session touches are not yet updated: the characters and places
that appeared, the objects that changed hands and the Clues that play
developed. Say so. From here on the Session's Events are their source, not the
draft or the Transcript.
