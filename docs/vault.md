# Vault layout

An Armarium vault is a folder of [Markdown notes](notes.md) inside a fixed
skeleton. A folder is a vault when it contains `reference/types/` and
`campaigns/`; [`armarium validate`](cli.md) checks the whole skeleton below.

`vaults/starter/` in this repository is the smallest vault that passes; copy it
to start a new one. `vaults/example/` is a populated vault with two campaigns.

## Skeleton

```text
assets/                       files that are not notes: images, handouts
campaigns/                    only campaign_N directories, at least one
  campaign_N/                 N is a positive integer
    clues/                    Clue notes
    content/                  this campaign's Content notes
    reference/                this campaign's Reference notes
      Campaign.md             the campaign overview
      indexes/
        Clues.md              the campaign's clue index
      players/                Player notes
    sessions/                 Session notes
      transcripts/            Transcript notes
content/                      Content notes shared by every campaign
reference/                    shared Reference notes
  schemas/                    <type>.schema.json for every Type
  statuses/                   Status notes: Abandoned, Dormant, Hinted, Pending, Revealed, Superseded
  templates/                  one template per authored type: Clue, Content, Player, Session, Transcript
  types/                      Type notes: Clue, Content, Player, Reference, Session, Status, Transcript, Type
  views/                      Bases views (.base) embedded by notes
```

Every entry shown is required, as a real directory or file rather than a
symlink. Beyond the skeleton, further Type and Status notes may be added beside
the built-in ones, and further folders may be added anywhere; every Markdown
file in the vault is a note and must follow the [note rules](notes.md), while
files of other kinds are only link targets.

`reference/types/` and `reference/schemas/` correspond one to one: `Clue.md`
has `clue.schema.json`, and so on, the schema named after the lowercased type.
`reference/schemas/` holds nothing else.

## Where notes live

A note's type decides its directory. The reserved directories admit only their
own type; subfolders inside them are allowed (`content/factions/Guild.md`).
Reference notes and notes of custom types live outside the reserved
directories: under `reference/` or `campaigns/campaign_N/reference/`, or in
further folders of your own.

| Type | Directory | Filename |
| --- | --- | --- |
| Content | `content/` (shared) or `campaigns/campaign_N/content/` | free |
| Clue | `campaigns/campaign_N/clues/` | `C-`, the campaign number, `-`, a four-digit ordinal: `C-1-0001.md` |
| Session | `campaigns/campaign_N/sessions/`, excluding `transcripts/` | `S-`, the campaign number, `-`, a three-digit ordinal that matches `session_number`: `S-1-001.md` |
| Transcript | `campaigns/campaign_N/sessions/transcripts/` | its Session's filename plus ` Transcript`: `S-1-001 Transcript.md` |
| Player | `campaigns/campaign_N/reference/players/` | free |
| Type | `reference/types/` | the type's name |
| Status | `reference/statuses/` | the status's name |
| Reference, custom types | outside the reserved directories, as above | free |

No filename may have leading, trailing, doubled or non-space whitespace. Each
file path must be unique when compared case-insensitively.

## Other entries

Hidden entries (`.obsidian/`, `.scratch/`, anything starting with `.`) and
symlinks are not part of the vault. Files that are not Markdown, such as
`assets/harbor-pass.txt` or `reference/views/clue-index.base`, are not notes
but can be linked and embedded: `[[harbor-pass.txt]]`,
`![[reference/views/clue-index.base#Active]]`.
