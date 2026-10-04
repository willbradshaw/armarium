# Finding records

`armarium find` looks a [record](record.md) up by name or alias in an existing
[vault](vault.md). It only reads: nothing is validated or changed.

## Finding a record by name

```sh
armarium find "Mara" --vault ../my-vault
```

`armarium find NAME` lists every record whose filename, without `.md`, or one of
whose `aliases` is `NAME`. Names compare as [links](record.md#links) do: case and
equivalent Unicode spellings are ignored, as is extra whitespace. The whole name
must match; a record whose name only contains `NAME` is not listed. Use it before
creating a record, to see whether the entity already has one.

`--vault PATH` names the vault's root directory. Omit it to use the vault
containing the current directory.

Each match is one line on standard output, with four tab-separated fields:

```text
content/Mara.md	Content/NPC	name	Harbour pilot who witnesses petitions.
campaigns/campaign_1/content/Quay Nine.md	Content/Location	alias	
```

1. The record's path, relative to the vault root.
2. Its [type](type.md), followed by `/` and its subtype when it has one. Empty for a file
   without a usable `type`.
3. How it matched: `name` when the filename is the name sought, `alias` when
   one of its aliases is.
4. Its `summary` on one line, or nothing when it has none.

Records with the name come first, then records with the alias, each group in
path order. A record with both is listed once, as `name`.

[Templates](record.md#anatomy), hidden entries, symlinks and the optional
`scripts/` directory are not searched. A file whose frontmatter cannot be parsed
is left out rather than reported; [`armarium validate`](validate.md) reports it.

The command exits with `0` when a record has the name or alias, `1` when none
does or the vault cannot be read, and `2` for a usage error. Messages go to
standard error, so standard output holds only matches.
