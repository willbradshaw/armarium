# Campaigns

Each [vault](vault.md) holds one or more **campaigns**, each in its own directory
`campaigns/campaign_N/` (with `N` a positive integer). Each campaign describes a series of TTRPG [sessions](type.md#session) in the vault's setting, along with their shared context and metadata.

This page summarises what the [Type records](type.md) and their schemas say
about campaigns. Where records live and what a campaign block holds are set by
those records, which are the authority.

## Directory

```text
campaigns/campaign_N/
  clues/                  Clue records, C-N-NNNN.md
  content/                Content records specific to this campaign
  notes/                  Note records specific to this campaign
  reference/
    Campaign.md           the campaign overview, a Reference record
    indexes/
      Clues.md            the clue index, a Reference record
    players/              Player records
  sessions/               Session records, S-N-NNN.md
    transcripts/          Transcript records, S-N-NNN Transcript.md
```

The starter vault ships `campaign_1`. Use [`armarium add campaign`](add.md#adding-a-campaign)
to add another.

## State

[Content](type.md#content) records carry `campaign_N` blocks in their frontmatter describing their campaign-related state:

```yaml
campaign_1:
  first_session: "[[S-1-001]]"
  last_session: "[[S-1-002]]"
campaign_2:
  first_session:
  last_session:
```

A block's `first_session` and `last_session` are both null until the record
first appears in that campaign, and then both link to the earliest and latest
Session of that campaign in the record's Appearances. `N` must be an existing
campaign, and a record under `campaigns/campaign_N/content` may carry only that
campaign's block; shared Content may carry a block for any campaign.

An Object or Gear record's campaign blocks have one more field, `held_by`,
which records who holds the object now:

- null, allowed only before the object enters play in that campaign;
- a link to the PC, NPC or Faction Content that holds it. When the party holds
  it together, link to the party's Faction;
- a list of such links when the object is a set split between holders. A
  list item may be `GONE` for a part that has left play;
- `GONE` once the whole object has left play, for example through sale, loss,
  destruction or consumption.

Once the object has entered play, `held_by` must name a holder or `GONE`. The
Sessions record how it was acquired and passed on.

In addition to the `campaign_N` blocks, a Content entry must also describe its subject's appearances in each campaign in its Appearances section; see [Content](type.md#content) for more details.
