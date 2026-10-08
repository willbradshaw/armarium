# This vault and Armarium

This is an [Armarium](https://github.com/willbradshaw/armarium) vault: a folder
of Obsidian notes, called records, in a fixed layout that the `armarium` command
creates and checks. The
[Armarium documentation](https://github.com/willbradshaw/armarium/tree/main/docs)
is the full reference; this page is the short version.

## Layout

| Folder | Holds |
| --- | --- |
| `content/` | Content shared by every campaign: characters, places, groups, objects, dates and lore |
| `campaigns/campaign_N/` | one campaign: its own `content/`, `clues/`, `sessions/`, `notes/` and `reference/` |
| `notes/` | working notes shared by every campaign |
| `reference/` | Type records, templates, schemas, statuses, views and installed extensions |
| `assets/` | images, maps and handouts |
| `docs/` | documentation about the vault, such as this page |

## Records and types

Every record is a Markdown file whose frontmatter declares its type. Each type
has a Type record in `reference/types/` that describes its fields, its body and
what belongs in it. The Type records are the authority for this vault: read the
relevant one before writing a record of that type.

A record under `content/` or `notes/` is shared by every campaign. One under
`campaigns/campaign_N/` belongs to that campaign.

## Commands

Run these from the vault root, or add `--vault PATH`.

| Command | Does |
| --- | --- |
| `armarium add content "NAME" --subtype SUBTYPE` | creates a record from the vault's template; also `session`, `clue`, `note`, `player`, `transcript` and `campaign` |
| `armarium find "NAME"` | lists the records with that name or alias |
| `armarium trace "PATH"` | lists every link to a record, and where each one sits |
| `armarium validate .` | checks the whole vault; give a file to check one record |

## Rules to keep

- Every link must resolve to exactly one file.
- Validate before you commit; fix what it reports.
- Do not edit the files under `reference/extensions/NAME/`. They are installed
  by Armarium and replaced by `armarium extension update`.
