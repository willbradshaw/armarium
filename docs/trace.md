# Tracing links to a record

```sh
armarium trace "content/Quay Nine.md" --vault ../my-vault
```

`armarium trace PATH` lists every [link](record.md#links) to one file from the
records of an existing [vault](vault.md), with where each link sits. Use it after
changing a record, to see which records refer to it and may need a matching
change. With `--outbound` it lists the links
[from a record](#links-from-a-record) instead. It only reads: nothing is
validated or changed.

## Choosing the file

`PATH` is the path of the file to trace: a [record](record.md), or an asset such
as an image. It is a file path, not a name;
[`armarium find`](find.md) gives the path for a name:

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

## Output

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
links to the file on one line, or in one field, are listed once. The file's
links to itself are left out, as are links from templates, hidden entries, the
vault's [optional root entries](vault.md#other-entries) and files that cannot be
parsed.

The command reports the traced file and the number of links on standard error.
It exits with `0` whether or not anything links to the file, and `2` for a usage
error. It exits with `1`, with a one-line message, when `PATH` does not exist, is
a directory or a symlink, is a hidden entry or lies in a directory that vault
scans skip, or is not inside a vault or the vault given.

## Links from a record

```sh
armarium trace "campaigns/campaign_1/sessions/S-1-002.md" --outbound --vault ../my-vault
```

`armarium trace PATH --outbound` lists every file that one record links to.
`PATH` is chosen as above and must be a Markdown record. The output has the
same three fields, with the linked file's path first; the location and line are
those of the link in the traced record:

```text
content/Captain Mara Vey.md	prepared_npcs
campaigns/campaign_1/content/Quay Nine.md	Preparation > Scene notes	42
campaigns/campaign_1/content/Quay Nine.md	Notes > Events	65
campaigns/campaign_1/content/Shoal Chart.md	Notes > Rewards > Loot	74
```

Lines follow the order of the links in the record, frontmatter first. Links to
assets and embeds are included; several links to one file on a line, or in a
field, are listed once, and the record's links to itself are left out.

A link that is malformed, or names no file or several, is not listed. Each is
reported on standard error as a warning; [`armarium validate`](validate.md)
gives the full finding. The command still exits with `0`. It exits with `1`
when the record cannot be parsed or `PATH` is not a Markdown file.
