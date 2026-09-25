# Campaigns

A campaign is one group's play through the setting: its sessions, the clues
in play, the characters, places and things it has touched, and its players.
A vault holds one or more campaigns, each in its own directory
`campaigns/campaign_N/` with `N` a positive integer, alongside the setting
[records](record.md) they all share.

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

`Campaign.md` is a free-form overview: premise, cast, where things stand.
Every Session's `campaign` field links to it. `indexes/Clues.md` embeds the
clue views for this campaign; the views scope themselves by the folder they
are embedded from, so the same view files under `reference/views/` serve
every campaign. `N` appears in every Clue, Session and Transcript filename.

The starter vault ships `campaign_1`. To add a campaign, create
`campaign_N` with the directories and two files above; the example vault's
`campaign_2` shows a second campaign sharing the setting with the first.

## Scope

A record under `campaigns/campaign_N/` belongs to that campaign; a record
under `content/`, `notes/` or `reference/` is shared by every campaign.
Campaign records refer to their own campaign: a Session's absent players,
prepared clues and preparation lists, a Clue's subjects and sessions, a
Transcript's session, a Player's characters, and a PC's player all link
within the same campaign. Where a field may link to [Content](type.md#content)
(subjects, prepared locations and NPCs, members, parent locations, holders),
the target may be either the campaign's own Content or shared Content — a
shared place or faction can figure in every campaign, while a campaign's
own records stay its own.

## Campaign state on Content

Content records carry what has happened to them in each campaign in one
`campaign_N` block per campaign, and record their appearances in one
`## Appearances` list across campaigns.

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
campaign, and a record under `campaigns/campaign_N/` may carry only that
campaign's block; shared Content may carry a block for any campaign. An
Object's block also holds `held_by`, its current possession in that
campaign: null only before it enters play, then a holder, a non-empty list of
holders (split possession) or `GONE` (out of play), with `GONE` also allowed
inside a list; a holder is a link to PC, NPC or Faction Content in that
campaign or shared. Acquisition and transfer history belongs in Session
records.

The Appearances list is described under [Content](type.md#content); its
entries name Sessions, whose filenames carry the campaign number, so one list
serves every campaign.
