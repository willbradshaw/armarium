# Vault layout

An Armarium vault is a folder of Markdown records with a fixed skeleton around
them. `armarium validate` recognises a vault by two markers, `reference/types/`
and `campaigns/`, and checks the whole skeleton below whenever it is pointed at
a vault root (or at a directory containing vault roots). Extra folders and files
are allowed anywhere; the requirements below are a floor, not a ceiling.

`vaults/starter/` in this repository is the smallest vault that passes; copy it
to start a new one. `vaults/example/` is a populated vault with two campaigns.

## Required skeleton

```text
assets/                       link targets that are not records (images, handouts)
campaigns/
  campaign_N/                 one or more; N is a positive integer
    clues/
    content/
    reference/
      Campaign.md             the campaign overview, a Reference record
      indexes/
        Clues.md              the campaign's clue index, a Reference record
      players/
    sessions/
      transcripts/
content/                      setting content shared by every campaign
reference/
  schemas/                    one <type>.schema.json per Type definition
  statuses/                   Abandoned, Dormant, Hinted, Pending, Revealed, Superseded
  templates/                  Clue, Content, Player, Session, Transcript
  types/                      Clue, Content, Player, Reference, Session, Status, Transcript, Type
  views/                      Bases views (.base files) embedded by records
```

Every directory shown must exist as a real directory, and every named file as a
real file; a symlink in place of either counts as missing. Empty directories are
fine (the starter keeps them with `.gitkeep`).

- `campaigns/` must hold at least one `campaign_N` directory and nothing else;
  each campaign carries the six directories and two files shown.
- `reference/types/` must define the eight built-in types and
  `reference/statuses/` the six built-in Clue statuses, by those filenames.
  Additional Type and Status definitions may be added beside them.
- `reference/schemas/` and `reference/types/` correspond one to one:
  `Clue.md` has `clue.schema.json`, and so on, with the schema named after the
  lowercased type. A type without a schema, a schema without a type, or another
  `.json` file in `schemas/` is reported. Each schema must load as a valid
  JSON Schema.
- `reference/templates/` must hold the five templates named above. Templates
  are parsed but not validated as records, so their placeholder values are
  allowed to break the rules.

## Where records live

A record's `type` decides where it may sit. Placement is checked by directory
prefix, so subfolders inside an expected directory are allowed
(`content/factions/Guild.md` is placed correctly).

| Type | Directory | Filename |
| --- | --- | --- |
| Content | `content/` (shared) or `campaigns/campaign_N/content/` | free |
| Session | `campaigns/campaign_N/sessions/`, not its `transcripts/` subfolder | `S-N-NNN.md`, three-digit ordinal, matching `session_number` |
| Transcript | `campaigns/campaign_N/sessions/transcripts/` | `S-N-NNN Transcript.md`, named after its Session |
| Clue | `campaigns/campaign_N/clues/` | `C-N-NNNN.md`, four-digit ordinal |
| Player | `campaigns/campaign_N/reference/players/` | free |
| Type | `reference/types/` | the type's name |
| Status | `reference/statuses/` | the status's name |
| Reference | anywhere | free |
| custom types | anywhere | free |

`N` in a filename is the number of the campaign directory that contains the
record. No filename may have leading, trailing or doubled whitespace, and
filenames are matched case-insensitively when links are resolved, so two files
whose names differ only by case make every link to them ambiguous.

## Campaigns and scope

`campaigns/campaign_N` is the unit of campaign scope. A record under it belongs
to that campaign; a record under `content/` or `reference/` is shared. Scope
governs which records may link to which: campaign records link to their own
campaign's records or to shared content, and a shared Content record's
`campaign_N` blocks must name campaigns that exist. Records placed directly
under `campaigns/` or under a non-`campaign_N` directory are reported.

## What is ignored

Discovery skips hidden entries (anything starting with `.`, so `.obsidian/` and
`.scratch/`), `__pycache__`, `node_modules`, and every symlink. Files with other
extensions (`assets/…`, `reference/views/*.base`) are not records but are
indexed as link targets, so `[[harbor-pass.txt]]` and
`![[reference/views/clue-index.base#Active]]` resolve. A directory without the
two markers is not a vault; `armarium validate` on such a directory descends
looking for vault roots and ignores loose Markdown outside them.
