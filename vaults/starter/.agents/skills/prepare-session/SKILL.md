---
name: prepare-session
description: Prepares the next Session record in this Armarium vault before play. Carries over open content from previous Sessions, proposes new material for GM review, and works with the GM to finish preparation.
---

# Prepare a Session

This procedure fills in the Preparation half of a Session before it is played.
It never writes a Session's Notes, and it changes no earlier Session.

It has two phases:

- **Carry-over** (steps 1 to 6) is mechanical. It creates the Session, reads
  the Sessions before it for what they left open, and writes that down. It
  invents nothing.
- **New material** (step 7) is done with the GM. You point out what the vault
  already implies, the GM decides what to add, and you write only the text
  they confirmed.

You need the campaign. The GM may also give the date of play, or what they
want the Session to cover.

Run the commands from the vault root, or add `--vault PATH`.

## The rule: ask before adding anything new

Never write a new scene, Clue, character, place, encounter or reward without
first proposing it to the GM and getting an explicit yes.

Carry-over is allowed to copy forward what earlier Sessions and existing
records already hold: that is reproduction, not invention. The moment you
would write a fact, a character's motive or a detail of an encounter that no
record holds, stop and ask.

The reason is that preparation hardens into canon. A rival you made up for a
character, a line of doctrine you put in a priest's mouth or an innkeeper you
named will be read later as something the GM established.

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

Read `reference/types/Session.md`. It says what each field and section of a
Session holds. It is the authority for this vault.

Read the whole of the last played Session: its Preparation, to see what was
planned, and its Notes, to see what happened.

## 3. Settle the frontmatter

| Field | What to do |
| --- | --- |
| `type`, `campaign`, `session_number` | Leave as `armarium add session` set them. |
| `aliases` | Leave empty unless the GM gives the Session a name. |
| `date` | Ask the GM for the date of play if you were not given it, and write it as `"YYYY-MM-DD"`. Leave it empty if they do not know. |
| `in_game_start_date` | By default, link the previous Session's `in_game_end_date`, or the Date after it if that Session's Events end with a night's rest. This is an assumption: report it in step 6. If the GM has said how much time has passed, use the Date that gives. If the end date is empty, ask the GM for the Date. |
| `in_game_end_date`, `players_absent` | Leave empty. They are filled in after play. |
| `prepared_clues`, `prepared_locations`, `prepared_npcs` | Filled in steps 5 and 7. |

Where the Type record says what is usual, treat it as a default and not a
rule. Write the usual case, and report it to the GM in step 6 as an
assumption they can change.

An in-game date links a Date record. If the one you need does not exist,
create it by following `.agents/skills/update-record/SKILL.md`.

When a thread sets a date ahead, such as a deadline "in three days", work the
date out from the setting's calendar as the vault describes it. Do not assume
the calendar counts as ours does. If the vault does not say, ask the GM.

## 4. Work through the carry-over checklist

Work through every item below, in order. For each thing you find, note the
Session it comes from. Note also what you are dropping and why. Change no
record in this step.

- **Cliffhangers.** Did the previous Session end on something due to land at
  the start of this one, such as a question left unanswered, a door opened on
  a room not yet described, or a character about to arrive? By default
  these go in the Starting scene.
- **Unfinished fights.** Did the previous Session end with an encounter
  unresolved? The same encounter carries over in the state play left it, with
  what was already defeated. By default the Starting scene continues it.
- **Unplayed scenes.** Compare the previous Session's Other scenes with its
  Events. A scene that did not happen and still could carries over as it was
  written. Drop one whose moment has passed, as when the character it turned
  on has died.
- **Unplayed encounters.** Do the same for its Encounters. One the party may
  still walk into carries over.
- **Unclaimed rewards and unseen characters.** A prepared reward the party did
  not gain, or a prepared character who never appeared and still may, carries
  over.
- **Deadlines.** Search the earlier Sessions' Events for dated threads: "it
  happens in three days", "she arrives tomorrow", "the deadline is the
  festival". Compare each with this Session's `in_game_start_date`. One that
  falls on or before it is due. By default it goes in the Starting scene or
  Other scenes; the GM may prefer to hold it back.
- **Commitments.** Did a character promise or threaten something: a visit, a
  courier, a meeting? Check its date in the same way.
- **Open Clues.** List the campaign's open Clues and read each one:

  ```sh
  grep -lE "^status: .*(Pending|Hinted)" campaigns/campaign_N/clues/*.md
  ```

  - **Pending:** is one of its subjects within the party's reach this
    Session? If so it is a candidate for `prepared_clues`.
  - **Hinted:** did the previous Session move towards it, so that it may be
    revealed in this one? If so it is a candidate.
  - **Any other status:** do not prepare it. `reference/types/Clue.md` says
    what each status means. If a Dormant Clue has a subject within the
    party's reach, ask the GM in step 6 whether they want it back.
  - **Outdated:** a candidate whose text no longer fits what play has
    established, such as a room the party has since searched. Never edit its
    text or subjects. Leave it out, and raise it with the GM in step 6.
- **Places and characters in play.** List the records the previous Session
  links to:

  ```sh
  armarium trace "campaigns/campaign_N/sessions/S-N-NNN.md" --outbound
  ```

  The places and characters its Events name, and that the party is likely to
  keep dealing with, are candidates for `prepared_locations` and
  `prepared_npcs`.

Read earlier Sessions only as far as one of these threads leads back to them.

## 5. Write the carry-over

Fill the Session's Preparation from step 4, and from nothing else:

- Put each item in the section the Type record gives for it. Copy a carried
  scene as it was written.
- Write each new scene line as one line that points at the scene, unless
  the GM's own scenes run longer. It is not a description of the scene.
- Link every record you name. Add each prepared Clue, place and character to
  its list in the frontmatter, quoted: `"[[Name]]"`.
- Leave the embedded views and the Notes half as the template has them.
- Write only preparation. Your questions and doubts, such as a Clue that looks
  outdated, go to the GM in step 6, not into the Session.

Then validate, and fix every error your change introduced:

```sh
armarium validate "campaigns/campaign_N/sessions/S-N-NNN.md"
```

## 6. Show the GM and stop

Give the GM a summary under these headings, leaving out any that are empty:

- what you assumed: the in-game start date, and where you placed each
  cliffhanger, unfinished fight and due deadline;
- cliffhangers, and how you framed the Starting scene;
- unfinished and unplayed encounters;
- scenes carried over;
- deadlines and commitments that fall due;
- Clues prepared, any that look outdated, and any Dormant Clue within
  reach;
- places and characters prepared;
- what you dropped, and why;
- which parts of Preparation are still empty.

Then stop and wait. Corrections to the carry-over are not a request for new
material.

## 7. Add what is new, with the GM

Take the kinds of material in the order below. Scenes come first because the
rest mostly follows from them. For each kind, go round this loop.

**a. Say what is there.** Tell the GM what Preparation already holds for this
kind.

**b. Propose what the vault implies.** List what existing records point to
and Preparation does not yet hold: a thread the carry-over left unplaced, a
Clue whose subject a confirmed scene brings within reach, a character or place
a confirmed scene needs. Give each with the records it rests on. Propose
nothing here that no record supports.

**c. Ask.** Ask the GM what else they want for this kind, and whether they
would like ideas. Offer ideas of your own only if they say yes: three at most,
each saying which parts of it would be new facts.

**d. Show the exact text.** For each item the GM wants, show exactly what you
will write: the line for the Session, and for a new or changed record, its
fields and body. Write nothing yet.

**e. Write on a yes.** When the GM confirms that text, write it as shown:

- a line of Preparation goes into the Session;
- a new record, or a change to one, is made by following
  `.agents/skills/update-record/SKILL.md`, and the record is then added to the
  Session where it belongs, including its `prepared_*` list.

One confirmation covers one item. A change to the text needs a new
confirmation.

**f. Note what follows.** A confirmed item often needs others: a new scene may
need a character, a place or a Clue. Do not write them. Raise each under its
own kind, at step b.

**g. Close the kind.** Validate the Session and tell the GM what you wrote. If
the GM defers something, such as a handout to write later or what a search of
some room turns up, add it to Scene notes as a line beginning `To do:`, so
that it is not lost. Then go on to the next kind.

The GM may give you several things at once, or out of order. Take what they
give, run d to f on each, then return to the kinds you have not covered.

The kinds, and what is particular to each:

1. **Starting scene.** If the carry-over supplies it, confirm its text.
2. **Other scenes.** The threads the GM wants to press this Session that the
   carry-over did not supply.
3. **Characters and places.** Those the scenes need that are not yet in
   `prepared_npcs` or `prepared_locations`, with or without a record.
4. **Clues.** A Session usually has about ten in `prepared_clues`. If it has
   fewer, say how many, list at step b any open Clues that could join them,
   and ask whether the GM wants new ones suggested. Do not pad the list with
   Clues that have little to do with the Session: fewer good Clues are better
   than ten strained ones. Before showing the text of a new Clue, check that no
   existing Clue states the fact: `armarium trace` on one of its subjects
   lists the Clues that link to it. Change the status of an outdated Clue as
   its Type record describes, only if the GM says to.
5. **Encounters.** Agree the opposition and the stakes with the GM before
   showing the text. Take statistics and rules from the vault's records or from
   the GM, never from memory. Where an opponent has no record, say in the
   encounter that it is a sketch.
6. **Rewards.** When the GM names an item, use its record. When they want
   options, such as "something for this character", search the vault's Content
   for candidates and offer a short list with a line on each; the GM picks. A
   new item needs its rules text from the GM. Never write that from memory, and
   never leave a placeholder for it.

After the last kind, read the whole of Preparation and check that it holds
together:

- every record a scene names is in its `prepared_*` list, where it has one;
- every prepared Clue has some way to come up in a scene;
- no section is empty that the GM meant to fill.

Tell the GM what you found, and ask whether the preparation is complete. This
step ends when they say it is.

## 8. Validate and report

```sh
armarium validate .
```

Fix every error your change introduced. If the vault had errors before you
started, report them; do not fix them unasked.

Then say which Session you prepared, which records you created or changed, and
what is still to decide.
