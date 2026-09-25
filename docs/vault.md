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
symlink, and nothing else belongs at the top level. Further Type and Status
notes may be added beside the built-in ones. Subfolders may be added inside
`assets/`, `content/`, `reference/` and their campaign counterparts. Every
Markdown file in the vault is a note and must follow the [note rules](notes.md).
Files that are not Markdown belong in `assets/`; the only exceptions are the
views in `reference/views/` and the schemas in `reference/schemas/`.

`reference/types/` and `reference/schemas/` correspond one to one: `Clue.md`
has `clue.schema.json`, and so on, the schema named after the lowercased type.

## Where notes live

A note's type decides its directory. Each directory admits only its own type;
subfolders inside a directory are allowed (`content/factions/Guild.md`).

| Type | Directory | Filename |
| --- | --- | --- |
| Content | `content/` (shared) or `campaigns/campaign_N/content/` | free |
| Clue | `campaigns/campaign_N/clues/` | `C-`, the campaign number, `-`, a four-digit ordinal: `C-1-0001.md` |
| Session | `campaigns/campaign_N/sessions/`, excluding `transcripts/` | `S-`, the campaign number, `-`, a three-digit ordinal that matches `session_number`: `S-1-001.md` |
| Transcript | `campaigns/campaign_N/sessions/transcripts/` | its Session's filename plus ` Transcript`: `S-1-001 Transcript.md` |
| Player | `campaigns/campaign_N/reference/players/` | free |
| Type | `reference/types/` | the type's name |
| Status | `reference/statuses/` | the status's name |
| Reference | `reference/` (shared) or `campaigns/campaign_N/reference/`, outside the subdirectories above | free |
| custom types | a subfolder of `reference/` or `campaigns/campaign_N/reference/` of your own, such as `reference/calendar/` | free |

No filename may have leading, trailing, doubled or non-space whitespace. Each
file path must be unique when compared case-insensitively.

## Other entries

Hidden entries (`.obsidian/`, `.scratch/`, anything starting with `.`) and
symlinks are not part of the vault. Files that are not notes can still be
linked and embedded: `[[harbor-pass.txt]]` for `assets/harbor-pass.txt`,
`![[reference/views/clue-index.base#Active]]` for a view.
