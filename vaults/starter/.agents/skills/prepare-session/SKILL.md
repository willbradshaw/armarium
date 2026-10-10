---
name: prepare-session
description: Prepares the next Session record in this Armarium vault before play. Carries over what earlier Sessions left open, then adds new material only as the GM confirms it.
---

# Prepare a Session

This procedure fills in the Preparation half of a Session before it is played.
It never writes a Session's Notes, and it changes no earlier Session.

You need the campaign. The GM may also give the date of play, or what they
want the Session to cover.

Run the commands from the vault root, or add `--vault PATH`.

## 1. Find the Session to prepare

List `campaigns/campaign_N/sessions/` and read the latest Session.

- **It has been played:** its Events say what happened. Create the next one:

  ```sh
  armarium add session --campaign N
  ```

- **It has not been played:** it is the Session to prepare. Do not create
  another. Keep what its Preparation already holds, and tell the GM what you
  found there.

Never copy the template or write the file by hand.

## 2. Read the Type record and the Session before

Read `reference/types/Session.md`. It says what each part of Preparation
holds and what carries over from earlier Sessions. It is the authority for
this vault.

Read the whole of the last played Session: its Preparation, to see what was
planned, and its Events, to see what happened. Read earlier Sessions only as
far as an open thread leads back to them.

## 3. Gather what carries over

Work through the Type record's list of what carries over, and note each item
with the Session it comes from. Find the open Clues from their records:

```sh
grep -lE "^status: .*(Pending|Hinted)" campaigns/campaign_N/clues/*.md
```

For each, read the Clue and decide from its subjects and the last Events
whether play is heading towards it. `reference/types/Clue.md` says what each
status means.

Note also what you are dropping and why. Do not change a Clue's status or any
other record in this step.

## 4. Write the carry-over

Fill the Session's Preparation from step 3, and from nothing else:

- Set the frontmatter the Type record says can be known before play. Ask the
  GM for the date of play if you were not given it; leave it empty if they do
  not know.
- Put each item where the Type record says it belongs. Copy a carried scene as
  it was written.
- Link every record you name. Add each prepared Clue, place and character to
  its list in the frontmatter, quoted: `"[[Name]]"`.
- Leave the embedded views and the Notes half as the template has them.
- Write only preparation. Your questions and doubts, such as a Clue that looks
  outdated, go to the GM in step 5, not into the record.

Then validate, and fix every error your change introduced:

```sh
armarium validate "campaigns/campaign_N/sessions/S-N-NNN.md"
```

## 5. Show the GM and stop

Tell the GM:

- what you carried over, and from which Session;
- what you dropped, and why;
- any Clue that looks outdated;
- which parts of Preparation are still empty.

Then stop and wait. Corrections to the carry-over are not a request for new
material.

## 6. Add what is new, as the GM confirms it

A new scene, Clue, character, place, encounter or reward is the GM's to
decide. You may suggest; write nothing new until the GM has confirmed that
item. One confirmation covers one item.

For each confirmed item:

- **A line of Preparation:** add it to the Session.
- **A new record, or a change to one:** follow
  `.agents/skills/update-record/SKILL.md`, then add the record to the Session
  where it belongs. Before creating a Clue, check that no existing Clue states
  the fact: `armarium trace` on one of its subjects lists the Clues that link
  to it.
- **An outdated Clue:** change its status as its Type record describes, only
  if the GM says to.

If the GM defers something, add it to Scene notes as a line beginning `To do:`,
so that it is not lost.

## 7. Validate and report

```sh
armarium validate .
```

Fix every error your change introduced. If the vault had errors before you
started, report them; do not fix them unasked.

Then say which Session you prepared, which records you created or changed, and
what is still to decide.
