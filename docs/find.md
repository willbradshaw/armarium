# Finding records

Two commands look things up in an existing [vault](vault.md):
[`armarium find`](#finding-a-record-by-name) lists the [records](record.md) with
a given name or alias, and [`armarium trace`](#tracing-links-to-a-record) lists
the records that link to a file. Both only read: nothing is validated or changed.

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

## Tracing links to a record

```sh
armarium trace "content/Quay Nine.md" --vault ../my-vault
```

`armarium trace PATH` lists every [link](record.md#links) to one file from the
vault's records, with where each link sits. Use it after changing a record, to
see which records refer to it and may need a matching change.

`PATH` is the path of the file to trace: a record, or an asset such as an image.
It is a file path, not a name; `armarium find` gives the path for a name:

```sh
$ armarium find "Quay Nine" --vault ../my-vault
campaigns/campaign_1/content/Quay Nine.md	Content/Location	name	A cramped customs quay.
$ armarium trace "campaigns/campaign_1/content/Quay Nine.md" --vault ../my-vault
```

Without `--vault`, `PATH` is absolute or relative to the current directory, and
the vault is the one containing the file, as for
[`armarium validate PATH`](validate.md#scope). With `--vault VAULT`, a relative
`PATH` is taken from the vault's root directory, so a path printed by
`armarium find` can be passed as it is; an absolute `PATH` must lie inside that
vault.

Each link is one line on standard output, with three tab-separated fields:

```text
campaigns/campaign_1/clues/C-1-0001.md	subjects
campaigns/campaign_1/sessions/S-1-002.md	prepared_locations
campaigns/campaign_1/sessions/S-1-002.md	Preparation > Scene notes	42
campaigns/campaign_1/sessions/S-1-002.md	Notes > Events	65
content/Captain Mara Vey.md	Appearances	22
```

1. The linking record's path, relative to the vault root.
2. Where the link sits. For a frontmatter link, the field, with nested fields
   joined by dots: `campaign_1.held_by`. For a body link, the headings above
   it, outermost first and joined by ` > `; empty for text before the first
   heading.
3. The link's line number in the file, for a body link; empty for frontmatter.

Lines are sorted by path, then line number. Links are followed as
[validation](validate.md) resolves them, whatever their spelling, alias or
anchor; embeds count as links, and a link written inside code counts too. Several
links to the record on one line, or in one field, are listed once. The record's
links to itself are left out, as are links from templates, hidden entries, the
`scripts/` directory and files that cannot be parsed.

The command reports the traced file and the number of links on standard error.
It exits with `0` whether or not anything links to the file, and `2` for a usage
error. It exits with `1`, with a one-line message, when `PATH` does not exist, is
a directory or a symlink, is a hidden entry or lies in a directory that vault
scans skip, or is not inside a vault or the vault given.
