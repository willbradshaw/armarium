# Running a campaign

A campaign in Armarium follows the cycle of play. You set it up once, then for
each Session you prepare, play, and record what happened in the Session and in
every record that play touched. The vault's views then show the next
preparation what is still open.

This page walks through that cycle with campaign 1 of the
[example vault](../vaults/example/), "The Third Bell", in which a ship's crew
fights the sale of their cutter in Port Briselle. Its first two Sessions have
been played, and the third is prepared but not yet played. The records below
are cut short with `…`; each links to the whole file. The rules for each
record are in [Types](type.md) and [Campaigns](campaign.md), and this page
links to them rather than repeating them.

## Setting up a campaign

[`armarium init`](init.md) creates a vault with campaign 1, and
[`armarium add campaign`](add.md#adding-a-campaign) adds another. A campaign
lives in `campaigns/campaign_N/`, laid out as [Campaigns](campaign.md#directory)
describes.

Each campaign has an overview, `reference/Campaign.md`, a free-form record for
you to write. Every Session links to it. The example's
[overview](../vaults/example/campaigns/campaign_1/reference/Campaign.md)
introduces the campaign and links its party, its ship and its setting:

```markdown
# The Third Bell

A swashbuckling campaign following the [[Glass Petrel Crew]] aboard [[Glass Petrel]]
on [[The Crownless Coast]]. It opens in [[Port Briselle]], where
[[Orlan Countinghouse]] is attempting to sell their cutter against a disputed
repair advance.
…
```

Each person at the table has a [Player](type.md#player) record, and each
character they play is PC [Content](type.md#content) linked back to them:

```sh
armarium add player "Ellis" --campaign 1
armarium add content "Esme Calder" --subtype PC --campaign 1 --frontmatter '{"player":"[[Ellis]]"}'
```

Then set the Player's `plays` to the PC, as
[Ellis](../vaults/example/campaigns/campaign_1/reference/players/Ellis.md)
does:

```yaml
type: "[[types/Player]]"
plays: ["[[Esme Calder]]"]
```

## Growing the setting

Every character, place, group, object, date and piece of lore is a Content
record with a [subtype](type.md#content). Before creating one, check with
[`armarium find`](find.md) that it has no record already under another name.

A record is shared, in `content/`, or belongs to one campaign, in
`campaigns/campaign_N/content/`. Share what keeps its identity outside any one
campaign: the city of
[Port Briselle](../vaults/example/content/Port%20Briselle.md) is shared, and
both of the example's campaigns have played there. Keep with its campaign
what matters only through that campaign's story, such as campaign 1's
[Quay Nine](../vaults/example/campaigns/campaign_1/content/Quay%20Nine.md):

```sh
armarium add content "Port Briselle" --subtype Location
armarium add content "Quay Nine" --subtype Location --campaign 1 --frontmatter '{"parent_location":"[[Port Briselle]]"}'
```

A record's `summary` says what the entity is, and leaves out what play will
change, such as where it is or who holds it. Its Notes hold what is
established about it. A record can start as a stub, with an empty summary and
`- N/A` in its Notes, and fill in as play gives it substance.

## Preparing a Session

[`armarium add session --campaign 1`](add.md#sessions) creates the next
Session, `S-1-003.md`, from the template. A [Session](type.md#session) has two
halves: Preparation, what you plan before play, and Notes, what happened at the
table. Before play you write only Preparation.

[S-1-003](../vaults/example/campaigns/campaign_1/sessions/S-1-003.md) is
prepared and not yet played:

```markdown
---
type: "[[types/Session]]"
date:
campaign: "[[campaign_1/reference/Campaign]]"
session_number: 3
…
prepared_clues: ["[[C-1-0003]]", "[[C-1-0004]]"]
prepared_locations: ["[[The Red Teeth]]", "[[Port Briselle]]"]
prepared_npcs: ["[[Captain Mara Vey]]"]
---
# Preparation

## Starting scene

At anchor beyond [[The Red Teeth]], [[Glass Petrel Crew|the crew]] sees a lantern flashing from [[Wake-lark]] where the chart marks deep water.

## Other scenes

- Compare the tide marks with the signal.
- Return to the [[Free Pilots Assembly]] for corroboration.
…

## Secrets & Clues

![[reference/views/prepared-clues.base]]

## Locations

![[reference/views/prepared-locations.base]]

## Important NPCs

![[reference/views/prepared-npcs.base]]

## Scene notes

- Carry forward the unexplained marks in [[C-1-0003]]. [[Captain Mara Vey]] may bargain over their meaning.
- Use [[C-1-0004]] if the party returns to the [[Free Pilots Assembly]] for corroboration.
…
```

Preparation has a Starting scene, Other scenes, Scene notes, Encounters and
Prepared rewards, written as you like. The three lists in the frontmatter
choose what the Session expects to use:

| Field | Lists | Shown under |
| --- | --- | --- |
| `prepared_clues` | Clues that could come up | Secrets & Clues |
| `prepared_locations` | Location Content | Locations |
| `prepared_npcs` | NPC Content | Important NPCs |

You write nothing under those three headings. Each holds one embedded Base,
from `reference/views/`, that shows the listed records in list order, each
with a Clue's `text` or a Content record's `summary`. Since the views read the
records as they are now, the Session shows the latest wording at the table,
including when you look back at a past Session.

Preparing a record writes nothing on it.
[The Red Teeth](../vaults/example/content/The%20Red%20Teeth.md) is prepared for
S-1-003, but has no `campaign_1` state, since campaign 1 has not been there
yet. A prepared Clue keeps its status. Preparation can only set its
`first_session`, as it did for
[C-1-0004](../vaults/example/campaigns/campaign_1/clues/C-1-0004.md), which
is still Pending:

```yaml
type: "[[types/Clue]]"
status: "[[Pending]]"
text: "The [[Free Pilots Assembly]] holds a second copy of [[Shoal Chart]], including its pencilled tide marks for a rendezvous beyond [[The Red Teeth]]."
subjects: ["[[Free Pilots Assembly]]", "[[Shoal Chart]]", "[[The Red Teeth]]"]
first_session: "[[S-1-003]]"
last_session:
```

A [Clue](type.md#clue) is a fact the players don't fully know yet and can
learn. Create one with [`armarium add clue`](add.md#clues); its `subjects` are
the Content its `text` links to. To choose what to prepare, look at what is
still open:

- each campaign's clue index, `reference/indexes/Clues.md`, lists its Clues as
  Active (Pending or Hinted) or Closed;
- each Content record's Active Clues lists the open Clues about it, so the
  [Shoal Chart](../vaults/example/campaigns/campaign_1/content/Shoal%20Chart.md)
  shows C-1-0003 and C-1-0004;
- the vault's `bases/` hold views of every Clue, Content record and Session.

## After play

### The write-up

After play you write the Session's Notes: a Preamble, the Events in order, and
the Rewards. Leave Preparation as you wrote it. In
[S-1-001](../vaults/example/campaigns/campaign_1/sessions/S-1-001.md), the
prepared tunnel route never came up, so it stays in Preparation and appears
nowhere in Events:

```markdown
## Events

- [[Orlan Countinghouse]]'s officer posted a notice proposing to sell [[Glass Petrel]] against an alleged unpaid repair advance.
…
- [[Captain Mara Vey]] explained that the stamped [[Brass Harbor Seal]] permitted a crossing at the third bell; [[C-1-0001]] was revealed.
- [[Talia Venn]] obtained the seal and passage papers. [[Glass Petrel Crew|The party]] boarded [[Glass Petrel]], where [[Esme Calder]] took [[Blue Signal Flare]] from its stores for a departure signal.
…

## Rewards

### Loot

| Item | Acquired by |
| --- | --- |
| [[Brass Harbor Seal]] | [[Talia Venn]] |
| [[Blue Signal Flare]] | [[Esme Calder]] |
```

Set `players_absent` and the in-game dates there too. Loot records who took
what on the night, and is not changed later.

### The records play touched

Then bring each record the Events touched up to date.
[`armarium trace`](trace.md#links-from-a-record) lists the records the Session
links to:

```sh
armarium trace campaigns/campaign_1/sessions/S-1-001.md --outbound
```

A record changes only if play reached it: a
character only spoken of has not appeared, and the
[Types](type.md#content) page says what counts as an appearance for each
subtype.

For each record that appeared, add a line to its Appearances and set its
[campaign state](campaign.md#state). After two Sessions, Captain Mara Vey's
record holds:

```markdown
---
…
campaign_1:
  first_session: "[[S-1-001]]"
  last_session: "[[S-1-002]]"
---
…
## Appearances

- [[S-1-001]]: Met [[Glass Petrel Crew|the crew]] at [[Quay Nine]] and explained how [[Brass Harbor Seal]] authorized a crossing through the night boom.
- [[S-1-002]]: Delivered [[Shoal Chart]] after the vote and declined to explain its pencilled tide marks.
```

Objects and Gear also say who holds them now, in `held_by`. The Shoal Chart
went to the whole crew, so it links their Faction; the Blue Signal Flare was
fired in S-1-002, so it is `GONE`:

```yaml
campaign_1:
  first_session: "[[S-1-001]]"
  last_session: "[[S-1-002]]"
  held_by: "GONE"
```

Add to a record's Notes only what is now established and lasting about it.

### Moving Clues

A Clue's status follows what the players have learned. Each status is a record
in `reference/statuses/` that says what it means:

| Status | Means |
| --- | --- |
| Pending | not yet introduced to the players |
| Hinted | partly introduced |
| Revealed | revealed in play |
| Abandoned | no longer pursued |
| Dormant | set aside, and may come back |
| Superseded | replaced by the Clue in its `superseded_by` |

Campaign 1 has one Clue in each of the first four:

| Clue | Status | How it got there |
| --- | --- | --- |
| [C-1-0001](../vaults/example/campaigns/campaign_1/clues/C-1-0001.md) | Revealed | Mara explained the seal in S-1-001. |
| [C-1-0002](../vaults/example/campaigns/campaign_1/clues/C-1-0002.md) | Abandoned | The GM cut the tunnel before S-1-001 was played. |
| [C-1-0003](../vaults/example/campaigns/campaign_1/clues/C-1-0003.md) | Hinted | The crew saw the chart's tide marks in S-1-002, and Mara would not explain them. |
| [C-1-0004](../vaults/example/campaigns/campaign_1/clues/C-1-0004.md) | Pending | Prepared for S-1-003, which has not been played. |

When play develops a Clue, set its `last_session` to that Session, whether or
not its status changes. A prepared Clue that never came up stays as it was.

A Clue is not canon until it is revealed. Once it is, it leaves its subjects'
Active Clues, and its fact goes into their Notes with a link back to the Clue.
C-1-0001 is Revealed, so
[Quay Nine](../vaults/example/campaigns/campaign_1/content/Quay%20Nine.md)'s
Notes now hold it:

```markdown
A stamped [[Brass Harbor Seal]] authorizes the watch to open the boom at the third bell; [[Glass Petrel Crew|the crew]] confirmed this procedure in [[S-1-001]] (see [[C-1-0001]]).
```

Finish with [`armarium validate`](validate.md), which checks every record and
the links between them. The next Session's preparation starts from what is
still open.

## Optional steps

None of these is needed to run a campaign.

- **Transcripts.** [`armarium transcribe`](transcribe.md) turns a recording into
  raw text on your own machine. Once that text is cleaned and attributed,
  [`armarium add transcript`](add.md#transcripts) stores it as the Session's
  [Transcript](type.md#transcript), and the Events can be written from it.
  Campaign 2 of the example vault has one,
  [S-2-001 Transcript](../vaults/example/campaigns/campaign_2/sessions/transcripts/S-2-001%20Transcript.md).
- **Handouts.** A Content record can hold the words the players are handed, in
  a `> [!handout]` callout, and Gear holds its rules in a `> [!rules]` callout.
  [`armarium handout`](handout.md) prints records as handouts in a PDF, such as
  a Session's loot.
- **Illustrations.** [`armarium illustrate`](illustrate.md) has an image model
  paint a record's picture and sets the record's `image` to it.

## With an agent

A vault carries [skills](agents.md) that let a coding agent do each step with
you. A skill that writes new text, such as a Session's Preparation or Events,
shows it to you and waits for your approval. A skill that brings records up to
date with the Events makes the clear changes and leaves the rest, such as a
Clue's new status, for you to decide.

| Step | Skill |
| --- | --- |
| Develop lore, characters or places by answering questions | `interview` |
| Create, change or update one record | `update-record`, `refresh-record` |
| Prepare the next Session | `prepare-session` |
| Turn a recording into a Transcript | `create-transcript` |
| Write up a played Session | `write-up-session` |
| Update the records a Session touched | `update-session-records` |
| Do all three of the steps above, in order | `process-session` |
| Print handouts | `make-handouts` |
| Illustrate a record | `illustrate-record` |

Each skill's procedure is in the vault's `.agents/skills/`, copied from the
[starter vault](../vaults/starter/.agents/skills/).
