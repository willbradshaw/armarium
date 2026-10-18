<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/armarium-banner-dark.svg">
    <img src="docs/assets/armarium-banner.svg" alt="Armarium" width="900">
  </picture>
</p>

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

| Command | Does | Guide |
| --- | --- | --- |
| `armarium add` | adds campaigns and records | [Adding to a vault](docs/add.md) |
| `armarium find` | looks a record up by name or alias | [Finding records](docs/find.md) |
| `armarium trace` | lists the records that link to a record, or the files it links to | [Tracing links to a record](docs/trace.md) |
| `armarium rename` | renames a record and rewrites every link to it | [Renaming a record](docs/rename.md) |
| `armarium merge` | merges a record into another and repoints the links to it | [Merging records](docs/merge.md) |
| `armarium delete` | deletes a record, refusing while links to it remain | [Deleting a record](docs/delete.md) |
| `armarium transcribe` | turns a session recording into raw transcript text | [Transcribing a recording](docs/transcribe.md) |
| `armarium illustrate` | illustrates a record with a picture | [Illustrating a record](docs/illustrate.md) |
| `armarium handout` | prints records as player handouts in a PDF | [Printing handouts](docs/handout.md) |

Optional [extensions](docs/extensions.md) add additional conventions. A new
vault also carries [instructions and skills for coding agents](docs/agents.md).

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

Use [`armarium add`](docs/add.md#adding-a-record) to create a record from the
vault's templates in `reference/templates/`. [Records](docs/record.md)
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
