# Campaigns

Each [vault](vault.md) holds one or more **campaigns**, each in its own directory
`campaigns/campaign_N/` (with `N` a positive integer). Each campaign describes a series of TTRPG [sessions](type.md#session) in the vault's setting, along with their shared context and metadata.

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

The starter vault ships `campaign_1`. To add a campaign, create
`campaign_N` with the directories and two files above; the example vault's
`campaign_2` shows a second campaign sharing the setting with the first.

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

A Content record with the Object subtype has an additional field in its campaign blocks: `held_by`. This is null before the object enters play; then a link to a Content entry denoting the PC, NPC or Faction holding the object, or a list thereof for shared possession; then `GONE` if the object has left play.

In addition to the `campaign_N` blocks, a Content entry must also describe its subject's appearances in each campaign in its Appearances section; see [Content](type.md#content) for more details.
