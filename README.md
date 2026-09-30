# Armarium

A system-general starter for tabletop roleplaying knowledge bases in Obsidian.

See [vaults/example](vaults/example) for a fleshed-out toy vault that follows and
demonstrates this repository's conventions.

## Create a vault

With Python 3.14+ and [uv](https://docs.astral.sh/uv/guides/tools/), install
Armarium from this checkout and create a vault:

```sh
uv tool install .
armarium init ../my-vault
```

If `armarium` is not on your PATH, run `uv tool update-shell` and restart your
terminal. To reinstall after updating this checkout, use
`uv tool install --reinstall-package armarium .`.

Open the new folder in Obsidian and edit
`campaigns/campaign_1/reference/Campaign.md`. See [Creating a vault](docs/init.md)
for details.

Add campaigns and records with `armarium add`; see
[Adding to a vault](docs/add.md).

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

Use [`armarium add`](docs/add.md#adding-a-record) or copy a file from
`reference/templates/` to create a record. [Records](docs/record.md)
describes what every record shares and [Types](docs/type.md) the fields, body
and rules of each type.

The starter is preconfigured for a single campaign. The example includes two
campaigns sharing setting Content, with independent campaign state and combined
Clue and appearance lists. [Vault layout](docs/vault.md) states the full required
skeleton and where each record type lives.

`.obsidian/` holds the settings the records rely on and is part of the vault;
only Obsidian's workspace files are ignored. `.scratch/` is ignored working
space; `.gitkeep` files preserve empty directories in Git. The copied vault can
be its own Git repository.

For schema integration and testing, see [Schema development](docs/schemas.md).

Planned work is tracked in the [issues](https://github.com/willbradshaw/armarium/issues).

MIT licensed. See the [changelog](CHANGELOG.md) and [release process](docs/releases.md).

## Validate records

Validate a record or a whole vault:

```sh
armarium validate path/to/record.md
armarium validate ../my-vault
```

See [Validation](docs/validate.md) for the command's options, what is checked
and how findings are reported.
