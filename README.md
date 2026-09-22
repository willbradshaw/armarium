# Armarium

A system-general starter for tabletop roleplaying knowledge bases in Obsidian.

See [vaults/example](vaults/example) for a fleshed-out toy vault that follows and
demonstrates this repository's conventions.

## Create a vault

From this checkout, copy `vaults/starter/` to a new folder whose parent exists:

```sh
vault_path="../my-setting"
mkdir "$vault_path" && cp -R vaults/starter/. "$vault_path/"
```

Open the new folder in Obsidian and edit
`campaigns/campaign_1/reference/Campaign.md`. The copy includes hidden files;
`mkdir` prevents copying over an existing destination.

Requires Obsidian **1.13.7+** with **Bases** and
[Frontmatter Markdown Links](https://github.com/mnaoumov/obsidian-frontmatter-markdown-links)
enabled.

## Layout

| Folder | Purpose |
| --- | --- |
| `content/` | Shared setting content. |
| `campaigns/campaign_1/` | Campaign content, clues, sessions, and reference material. |
| `reference/` | Templates, type descriptions, schemas, statuses, and shared reference material. |
| `assets/` | Maps, images, and handouts. |

Copy a file from `reference/templates/` to create a record. See the corresponding
reference for its fields and conventions:
[Content](vaults/starter/reference/types/Content.md),
[Clue](vaults/starter/reference/types/Clue.md),
[Session](vaults/starter/reference/types/Session.md),
[Player](vaults/starter/reference/types/Player.md), or
[Transcript](vaults/starter/reference/types/Transcript.md).

The starter is preconfigured for a single campaign. The example includes two
campaigns sharing setting Content, with independent campaign state and combined
Clue and appearance lists.

`.scratch/` is ignored working space; `.gitkeep` files preserve empty directories
in Git. The copied vault can be its own Git repository.

For schema integration and testing, see [Schema development](docs/schemas.md).

Planned work is tracked in the [issues](https://github.com/willbradshaw/armarium/issues).

## Validate a record

With Python 3.14+, install from this checkout and validate a record:

```sh
python -m pip install .
armarium validate path/to/record.md
```

See `armarium validate --help` for options and exit codes.
