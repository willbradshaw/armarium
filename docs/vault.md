# Vault layout

An Armarium vault is a folder of Markdown [records](record.md) inside a fixed
skeleton. To Obsidian any folder is a vault, and it keeps its own settings in
`.obsidian/`; the starter ships one with the settings the records rely on. To
[`armarium validate`](cli.md) a folder is a vault when it contains
`reference/types/` and `campaigns/`, and the whole skeleton below is checked.

`vaults/starter/` in this repository is the smallest vault that passes; copy it
to start a new one. `vaults/example/` is a populated vault with two campaigns.

## Skeleton

```text
assets/                       files that are not records: images, handouts
campaigns/                    only campaign_N directories, at least one
  campaign_N/                 N is a positive integer
    clues/                    Clue records
    content/                  this campaign's Content records
    notes/                    this campaign's Note records
    reference/                this campaign's Reference records
      Campaign.md             the campaign overview
      indexes/
        Clues.md              the campaign's clue index
      players/                Player records
    sessions/                 Session records
      transcripts/            Transcript records
content/                      Content records shared by every campaign
notes/                        Note records shared by every campaign
reference/                    shared Reference records
  schemas/                    <type>.schema.json for every Type
  statuses/                   Status records: Abandoned, Dormant, Hinted, Pending, Revealed, Superseded
  templates/                  one template per authored type: Clue, Content, Note, Player, Session, Transcript
  types/                      Type records: Clue, Content, Note, Player, Reference, Session, Status, Transcript, Type
  views/                      Bases views (.base) embedded by records
```

Every entry shown is required, as a real directory or file rather than a
symlink. The vault root, `campaigns/`, each `campaign_N/` and each `reference/`
hold exactly the entries shown (plus Reference records in `reference/`); every
other directory may hold subfolders of your own. Every Markdown file in the
vault is a record and must follow the [record rules](record.md). Files that are
not Markdown belong in `assets/`; the only exceptions are the views in
`reference/views/` and the schemas in `reference/schemas/`.

`reference/types/` and `reference/schemas/` correspond one to one: `Clue.md`
has `clue.schema.json`, and so on, the schema named after the lowercased type.

## Where records live

Each Type record declares where its records live in a `directories` field:
`shared` is a path under the vault root, `campaign` a path under each
`campaigns/campaign_N/`. A record must sit in a directory its type declares or
in a subfolder of it, and a directory admits only the types that declare it.
Where one declared directory lies inside another (`sessions/transcripts/`
inside `sessions/`), the longer declaration claims its subtree.

| Type | `directories` | Filename | Example |
| --- | --- | --- | --- |
| Content | `{ shared: content, campaign: content }` | free | `content/Port Briselle.md`, `campaigns/campaign_1/content/Quay Nine.md` |
| Note | `{ shared: notes, campaign: notes }` | free | `notes/Coast design notes.md`, `campaigns/campaign_1/notes/Prep for the hearing.md` |
| Reference | `{ shared: reference, campaign: reference }` | free | `campaigns/campaign_1/reference/Campaign.md` |
| Clue | `{ campaign: clues }` | `C-`, the campaign number, `-`, a four-digit ordinal | `campaigns/campaign_1/clues/C-1-0001.md` |
| Session | `{ campaign: sessions }` | `S-`, the campaign number, `-`, a three-digit ordinal that matches `session_number` | `campaigns/campaign_1/sessions/S-1-001.md` |
| Transcript | `{ campaign: sessions/transcripts }` | its Session's filename plus ` Transcript` | `campaigns/campaign_1/sessions/transcripts/S-1-001 Transcript.md` |
| Player | `{ campaign: reference/players }` | free | `campaigns/campaign_1/reference/players/Ellis.md` |
| Type | `{ shared: reference/types }` | the type's name | `reference/types/Clue.md` |
| Status | `{ shared: reference/statuses }` | the status's name | `reference/statuses/Pending.md` |

A vault may add a type of its own: a Type record in `reference/types/` with a
`directories` declaration and a matching schema in `reference/schemas/`. Its
declared directories then join the skeleton and must exist.

No filename may have leading, trailing, doubled or non-space whitespace. Each
file path must be unique when compared case-insensitively.

## Other entries

Hidden entries (`.obsidian/`, `.scratch/`, anything starting with `.`) and
symlinks are not part of the vault. Files that are not records can still be
linked and embedded: `[[harbor-pass.txt]]` for `assets/harbor-pass.txt`,
`![[reference/views/clue-index.base#Active]]` for a view.
