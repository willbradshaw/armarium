# Renaming a record

```sh
armarium rename "content/Quay Nine.md" "Quay Ten" --vault ../my-vault
```

`armarium rename PATH NAME` renames a [record](record.md) in its folder and
rewrites every [link](record.md#links) to it in the
[vault](vault.md). Rename records this way rather than in a file manager: a
file renamed by hand leaves every link to it broken.

## Choosing the record and the name

`PATH` is the record's file path, chosen as for
[`armarium trace`](trace.md#choosing-the-file): without `--vault`, absolute or
relative to the current directory; with `--vault VAULT`, relative to the vault
root, so a path printed by [`armarium find`](find.md) can be passed as it is.

`NAME` is the new filename without `.md`. The record stays in its folder. As
with [`armarium add`](add.md), the name may not be blank, start or end with
whitespace or a dot, hold doubled or non-space whitespace, end with `.md`, or
hold a control character or any of `# ^ [ ] | \ / : * ? " < >`. It must be
free among the records that can see the record, as [names](record.md#names)
require: no other record of the same campaign, or shared, may have it as its
filename or an alias. No other entry in the folder may have it either, ignoring
case and Unicode normalization. A name that differs only in case is a rename.

The command refuses to rename Types, Statuses, Sessions, Clues and
Transcripts, whose names the vault fixes, and each campaign's
`reference/Campaign.md` and `reference/indexes/Clues.md`.

## How links are rewritten

Every link that resolves to the record is rewritten, as
[validation](validate.md) resolves them: whatever its spelling, in the
frontmatter or the body, embeds and links inside code included, and the
record's links to itself. Only the link's target changes; its folders, `.md`,
anchor and display alias stay as written:

| Before | After |
| --- | --- |
| `[[Quay Nine]]` | `[[Quay Ten]]` |
| `[[content/Quay Nine.md#Notes]]` | `[[content/Quay Ten.md#Notes]]` |
| `[[Quay Nine\|the quay]]` | `[[Quay Ten\|the quay]]` |
| `![[Quay Nine]]` | `![[Quay Ten]]` |

When the new name is also the name of a record in another campaign, a link
spelled with the name alone would name both files, so each link to either
record gets the shortest trailing path that names it alone, such as
`[[campaign_1/content/Quay Ten]]`.

## Keeping the old name

With `--alias`, the old name stays one of the record's names: it is added to
the record's `aliases`, and a body link with no display alias of its own
keeps the old name as its display text, so prose reads as before:

| Before | After |
| --- | --- |
| `[[Quay Nine]]` | `[[Quay Ten\|Quay Nine]]` |
| `[[Quay Nine\|the quay]]` | `[[Quay Ten\|the quay]]` |

Frontmatter links are always written plainly, as `"[[Quay Ten]]"`. Without
`--alias`, every link reads the new name. An empty or inline `aliases` field
gains the name in place; a record without one gains it after its `summary`.

## Links left as written

Links outside records are left as written and reported as warnings, for you
to check: wikilinks in templates, `docs/`, `AGENTS.md`, `.base` and `.canvas`
files, and Markdown links such as `[map](Quay%20Nine.md)` anywhere.

## Nothing half done

Every change is worked out before any file is written. If a record that may
link to the renamed one cannot be parsed, or its frontmatter cannot be
rewritten to hold the new link, the command names it and changes nothing. If
writing a file fails or is interrupted, every file is put back as it was. A
frontmatter field is edited in place where it can be; otherwise it is written
afresh, double-quoted, and the rest of the frontmatter is kept.

## Output

Each change is one line on standard output, with four tab-separated fields:

```text
content/Quay Nine.md			renamed to content/Quay Ten.md
campaigns/campaign_1/clues/C-1-0001.md	subjects		[[Quay Nine]] → [[Quay Ten]]
campaigns/campaign_1/sessions/S-1-002.md	Notes > Events	65	[[Quay Nine|the quay]] → [[Quay Ten|the quay]]
```

1. The changed file's path, relative to the vault root, before the rename.
2. Where the link sits, as [`armarium trace`](trace.md#output) gives it; empty
   for the rename itself.
3. The link's line number, for a body link; empty otherwise.
4. The change.

Standard error then lists each file the command changes, such as
`content/Quay Nine.md: moved to content/Quay Ten.md`, and how many.
`--dry-run` checks the change as a real run would and prints the same lines,
saying what would change, without changing anything.

The command exits with `0` once the record is renamed, `1` when it cannot
be renamed, and `2` for a usage error. Run [`armarium validate`](validate.md)
on the vault afterwards.
