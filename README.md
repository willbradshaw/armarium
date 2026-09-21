# Armarium

A system-general starter for tabletop roleplaying knowledge bases in Obsidian.

## Create a vault

From this checkout, copy `starter/` to a new folder whose parent exists:

```sh
vault_path="../my-setting"
mkdir "$vault_path" && cp -R starter/. "$vault_path/"
```

Open the new folder in Obsidian and edit
`campaigns/campaign_1/reference/Campaign.md`. The copy includes hidden files;
`mkdir` prevents copying over an existing destination.

## Layout

| Folder | Purpose |
| --- | --- |
| `content/` | Shared setting content. |
| `campaigns/campaign_1/` | Campaign content, clues, sessions, and reference material. |
| `reference/` | Templates, type descriptions, schemas, statuses, and shared reference material. |
| `assets/` | Maps, images, and handouts. |

Copy a file from `reference/templates/` to create a record. See the corresponding
reference for its fields and conventions:
[Content](starter/reference/types/Content.md),
[Clue](starter/reference/types/Clue.md),
[Session](starter/reference/types/Session.md),
[Player](starter/reference/types/Player.md), or
[Transcript](starter/reference/types/Transcript.md).

Enable Obsidian's Dataview community plugin to render the included Clue views.
The supplied links and queries target campaign 1.

`.scratch/` is ignored working space; `.gitkeep` files preserve empty directories
in Git. The copied vault can be its own Git repository.

Planned work is tracked in the [issues](https://github.com/willbradshaw/armarium/issues).
