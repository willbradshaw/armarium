# Running a campaign

A campaign follows the cycle of play: set it up once, then for each Session
prepare, play, and record what happened. This page walks through that cycle.
The rules for each record are in [Types](type.md) and [Campaigns](campaign.md);
campaign 1 of the [example vault](../vaults/example/) shows each step done.

Run the commands from inside the vault, or add `--vault PATH`.

## Setting up a campaign

[`armarium init`](init.md) creates a vault with campaign 1;
[`armarium add campaign`](add.md#adding-a-campaign) adds another. Describe the
campaign in its overview, `campaigns/campaign_N/reference/Campaign.md`.

Add a [Player](type.md#player) for each person at the table, and the PC they
play:

```sh
armarium add player "Ellis" --campaign 1
armarium add content "Esme Calder" --subtype PC --campaign 1 --frontmatter '{"player":"[[Ellis]]"}'
```

Then list the PC in the Player's `plays`.

## Growing the setting

Each character, place, group, object, date and piece of lore is a
[Content](type.md#content) record. Check that it has no record yet, then add
one, shared or for one campaign:

```sh
armarium find "Port Briselle"
armarium add content "Port Briselle" --subtype Location
armarium add content "Quay Nine" --subtype Location --campaign 1
```

A record can start as a stub and fill in as play gives it substance.

> [!TIP]
> With an agent, the `interview` skill asks you questions to develop lore,
> characters or places and records what you settle; `update-record` creates
> or changes one record.

## Preparing a Session

```sh
armarium add session --campaign 1
```

A [Session](type.md#session) has two halves: Preparation, what you plan, and
Notes, what happened at the table. Before play, write only Preparation: a
starting scene, other scenes, scene notes, encounters and rewards.

List the Clues, places and characters you expect to use in `prepared_clues`,
`prepared_locations` and `prepared_npcs`. The Session shows each with its
current text or summary, so you don't copy them in.

To choose Clues, look at what is open: the campaign's clue index,
`reference/indexes/Clues.md`, and each record's Active Clues. Add a new
[Clue](type.md#clue) with its text:

```sh
armarium add clue --campaign 1 --frontmatter '{"text":"The [[Free Pilots Assembly]] holds a second copy of [[Shoal Chart]]."}'
```

Preparing changes nothing else. A prepared Clue keeps its status, and a
prepared place or character records nothing until play reaches it. The example
vault's S-1-003 is prepared but not yet played.

> [!TIP]
> With an agent, the `prepare-session` skill creates the next Session, carries
> over what the last one left open, and asks before adding anything new.

## After play

Write the Session's Notes: who attended, the Events in order, and the loot.
Leave Preparation as it was, so a scene that never came up stays there and out
of the Events. Set `players_absent` and the in-game dates.

Then update each record play touched. List the Session's links:

```sh
armarium trace campaigns/campaign_1/sessions/S-1-003.md --outbound
```

For each record that [appeared](type.md#content), add a line to its
Appearances and set its [campaign state](campaign.md#state); for an object,
set who holds it now. A record only spoken of has not appeared.

Move each Clue that play developed. A Clue starts Pending, becomes Hinted when
the players learn part of it, and Revealed when they learn it all. It can also
be Abandoned, set aside as Dormant, or Superseded by another. Once a Clue is
Revealed, it leaves its subjects' Active Clues, and its fact goes into their
Notes with a link back to it.

Finish by checking the vault:

```sh
armarium validate .
```

S-1-001 and S-1-002 in the example vault are played and recorded, and the
records they touched are up to date.

> [!TIP]
> With an agent, the `write-up-session` skill drafts the Notes from a
> Transcript or your notes, and `update-session-records` updates the records
> the Session touched. `process-session` runs both, starting from a recording
> if you have one.

## Optional steps

**Transcripts.** [`armarium transcribe`](transcribe.md) turns a recording into
raw text. Once it is cleaned and attributed,
[`armarium add transcript`](add.md#transcripts) stores it as the Session's
[Transcript](type.md#transcript):

```sh
armarium transcribe recordings/s3.wav
armarium add transcript S-1-003 --body-file transcript.md
```

> [!TIP]
> With an agent, the `create-transcript` skill does both, from a recording or
> raw speech-to-text.

**Handouts.** [`armarium handout`](handout.md) prints records as player
handouts in a PDF, such as a Session's loot or a letter.

> [!TIP]
> With an agent, the `make-handouts` skill checks each record has what to
> print, then prints them.

**Illustrations.** [`armarium illustrate`](illustrate.md) has an image model
paint a record's picture and sets it as the record's image.

> [!TIP]
> With an agent, the `illustrate-record` skill paints candidates and sets the
> one you choose.

[Agent instructions and skills](agents.md) describes the skills a vault
carries.
