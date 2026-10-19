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
| `reference/` | Type records, templates, schemas, statuses, views, installed extensions and illustration styles |
| `bases/` | tables for browsing records, such as `Content.base`, `Sessions.base` and `Clues.base` |
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
| `armarium rename "PATH" "NAME"` | renames a record and rewrites every link to it; `--alias` keeps the old name |
| `armarium merge --from "SOURCE" --into "TARGET"` | merges a record into another and repoints its links, listing where the two disagree |
| `armarium delete "PATH"` | deletes a record, refusing while links to it remain; `--unlink` turns them into text |
| `armarium illustrate prompt "PATH"` | prints what an image model should be told to paint a record's picture |
| `armarium illustrate generate "PATH" --prompt FILE` | paints candidate pictures for a record with an image model, into `.scratch/illustrate/` |
| `armarium illustrate ingest "PATH" "PICTURE"` | takes a picture into `assets/` as a record's image and sets its `image` field |
| `armarium handout "PATH" ... -o FILE.pdf` | prints records as player handouts, a page each, with a callout's text and their picture |
| `armarium transcribe "FILE"` | turns a session recording, or raw speech-to-text, into text ready to clean into a Transcript |
| `armarium update` | brings the files Armarium copied into the vault, such as Type records, schemas, skills and this page, up to date, keeping the vault's edits; `--dry-run` lists the changes |
| `armarium validate .` | checks the whole vault; give a file to check one record |

## Rules to keep

- Every link must resolve to exactly one file.
- Rename, merge and delete records with the commands, never by hand.
- Validate before you commit; fix what it reports.
- Bring the files Armarium copied in up to date with `armarium update`,
  never by hand. Where it reports a conflict, resolve the file it names under
  `.scratch/armarium-update/`, removing the conflict markers, and run it again.
- Do not edit `.armarium/`. It holds the copies `armarium update` merges
  against.
- Do not edit the files under `reference/extensions/NAME/`. They are installed
  by Armarium and replaced by `armarium extension update`.
