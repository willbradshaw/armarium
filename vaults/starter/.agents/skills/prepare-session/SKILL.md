---
name: prepare-session
description: Prepares the next Session record in this Armarium vault before play. Carries over what earlier Sessions left open, then adds new material only as the GM confirms it.
---

# Prepare a Session

This procedure fills in the Preparation half of a Session before it is played.
It never writes a Session's Notes, and it changes no earlier Session.

It has two phases:

- **Carry-over** (steps 1 to 6) is mechanical. It creates the Session, reads
  the Sessions before it for what they left open, and writes that down. It
  invents nothing.
- **New material** (step 7) is done with the GM. You propose, the GM decides,
  and you write only what they confirmed.

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
| `in_game_start_date` | Link the previous Session's `in_game_end_date`, or the Date after it if that Session's Events end with a night's rest. If the end date is empty, or the GM says more time has passed, ask the GM for the Date. |
| `in_game_end_date`, `players_absent` | Leave empty. They are filled in after play. |
| `prepared_clues`, `prepared_locations`, `prepared_npcs` | Filled in steps 5 and 7. |

An in-game date links a Date record. If the one you need does not exist,
create it by following `.agents/skills/update-record/SKILL.md`.

When a thread sets a date ahead, such as a deadline "in three days", work the
date out from the setting's calendar as the vault records it. Do not assume
the calendar counts as ours does. If the vault does not say, ask the GM.

## 4. Work through the carry-over checklist

Work through every item below, in order. For each thing you find, note the
Session it comes from. Note also what you are dropping and why. Change no
record in this step.

- **Cliffhangers.** Did the previous Session end on something due to land at
  the start of this one, such as a question left unanswered, a door opened on
  a room not yet described, or a character about to arrive? These go in the
  Starting scene.
- **Unfinished fights.** Did the previous Session end with an encounter
  unresolved? The same encounter carries over in the state play left it, with
  what was already defeated, and the Starting scene continues it.
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
  falls on or before it is due, and belongs in the Starting scene or Other
  scenes.
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
  - Skip Clues with any other status. `reference/types/Clue.md` says what
    each status means.
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
- Keep each scene to one line that points at the scene. It is not a
  description of it.
- Link every record you name. Add each prepared Clue, place and character to
  its list in the frontmatter, quoted: `"[[Name]]"`.
- Leave the embedded views and the Notes half as the template has them.
- Write only preparation. Your questions and doubts, such as a Clue that looks
  outdated, go to the GM in step 6, not into the record.

Then validate, and fix every error your change introduced:

```sh
armarium validate "campaigns/campaign_N/sessions/S-N-NNN.md"
```

## 6. Show the GM and stop

Give the GM a summary under these headings, leaving out any that are empty:

- cliffhangers, and how you framed the Starting scene;
- unfinished and unplayed encounters;
- scenes carried over;
- deadlines and commitments that fall due;
- Clues prepared, and any that look outdated;
- places and characters prepared;
- what you dropped, and why;
- which parts of Preparation are still empty.

Then stop and wait. Corrections to the carry-over are not a request for new
material.

## 7. Add what is new, as the GM confirms it

Go through each kind of material below with the GM. For each, either confirm
that nothing new is wanted or work out the additions together. You may
suggest; write nothing until the GM has confirmed that item. One confirmation
covers one item.

- **Starting scene.** If the carry-over supplies it, confirm it. Otherwise
  propose alternatives.
- **Scenes.** Which threads does the GM want to press this Session that the
  carry-over did not supply?
- **Clues.** Aim for about ten in `prepared_clues`. If the carry-over leaves
  it short, propose new ones to fill the gap. Do not pad it with Clues that
  have little to do with the Session: fewer good Clues are better than ten
  strained ones. Confirm each fact with the GM before creating its Clue, and
  check first that no existing Clue states it: `armarium trace` on one of its
  subjects lists the Clues that link to it.
- **Characters and places.** Any the GM wants ready that have no record yet?
- **Encounters.** Agree the opposition and the stakes with the GM first, then
  write the encounter under Encounters. Take statistics and rules from the
  vault's records or from the GM, never from memory. Where an opponent has no
  record, say in the encounter that it is a sketch.
- **Rewards.** When the GM names an item, use its record. When they want
  options, such as "something for this character", search the vault's Content
  for candidates and offer a short list with a line on each; the GM picks. A
  new item needs its rules text from the GM. Never write that from memory, and
  never leave a placeholder for it.

For each confirmed item:

- **A line of Preparation:** add it to the Session.
- **A new record, or a change to one:** follow
  `.agents/skills/update-record/SKILL.md`, then add the record to the Session
  where it belongs.
- **An outdated Clue:** change its status as its Type record describes, only
  if the GM says to.

This step ends when the GM says the preparation is complete.

If the GM defers something, such as a handout to write later or what a search
of some room turns up, add it to Scene notes as a line beginning `To do:`, so
that it is not lost.

## 8. Validate and report

```sh
armarium validate .
```

Fix every error your change introduced. If the vault had errors before you
started, report them; do not fix them unasked.

Then say which Session you prepared, which records you created or changed, and
what is still to decide.
