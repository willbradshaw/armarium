# Armarium documentation

New to Armarium? Start with the [README](../README.md), then
[create a vault](init.md).

## Installing

```sh
uv tool install armarium
```

If `armarium` is not on your PATH afterwards, run `uv tool update-shell` and
restart your terminal. To move to a newer release, run
`uv tool upgrade armarium`, then [update your vault](update.md).

## The vault

| Guide | Covers |
| --- | --- |
| [Vault layout](vault.md) | the folders a vault holds and where each kind of record lives |
| [Records](record.md) | what every record shares: frontmatter, body, links and names |
| [Types](type.md) | the fields, body and rules of each record type |
| [Campaigns](campaign.md) | campaign folders and the state records keep for each campaign |
| [Extensions](extensions.md) | optional conventions for a game system, such as D&D 5.5 |
| [Agent instructions and skills](agents.md) | what a vault provides for coding agents working in it |

## Commands

| Command | Does | Guide |
| --- | --- | --- |
| `armarium init` | creates a vault | [Creating a vault](init.md) |
| `armarium update` | brings the files Armarium copied into a vault up to date | [Updating a vault](update.md) |
| `armarium add` | adds campaigns and records | [Adding to a vault](add.md) |
| `armarium find` | looks a record up by name or alias | [Finding records](find.md) |
| `armarium trace` | lists the records that link to a record, or the files it links to | [Tracing links to a record](trace.md) |
| `armarium rename` | renames a record and rewrites every link to it | [Renaming a record](rename.md) |
| `armarium merge` | merges a record into another and repoints the links to it | [Merging records](merge.md) |
| `armarium delete` | deletes a record, refusing while links to it remain | [Deleting a record](delete.md) |
| `armarium validate` | checks a record or a whole vault | [Validation](validate.md) |
| `armarium transcribe` | turns a session recording into raw transcript text | [Transcribing a recording](transcribe.md) |
| `armarium illustrate` | illustrates a record with a picture | [Illustrating a record](illustrate.md) |
| `armarium handout` | prints records as player handouts in a PDF | [Printing handouts](handout.md) |
| `armarium extension` | enables, updates and removes extensions | [Extensions](extensions.md) |

## Developing Armarium

| Guide | Covers |
| --- | --- |
| [Schema development](schemas.md) | how the JSON schemas are built, integrated and tested |
| [Releases](releases.md) | how a release is made |

To work on Armarium itself, install it from a checkout with
`uv tool install --reinstall-package armarium .`.
