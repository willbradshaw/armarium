# Renaming and deleting records

```sh
armarium rename "content/Quay Nine.md" "Quay Ten" --vault ../my-vault
armarium delete "content/Quay Nine.md" --vault ../my-vault
```

`armarium rename` renames a [record](record.md) and rewrites every
[link](record.md#links) to it in the [vault](vault.md); `armarium delete`
deletes one, refusing while links to it remain. Rename and delete records this
way rather than in a file manager: a file renamed or deleted by hand leaves
every link to it broken.

## Choosing the record

`PATH` is the record's file path, chosen as for
[`armarium trace`](trace.md#choosing-the-file): without `--vault`, absolute or
relative to the current directory; with `--vault VAULT`, relative to the vault
root, so a path printed by [`armarium find`](find.md) can be passed as it is.

Neither command changes Types or Statuses, which define the vault, or each
campaign's `reference/Campaign.md` and `reference/indexes/Clues.md`.

## Renaming a record

`armarium rename PATH NAME` gives the record the filename `NAME.md` in the
same folder. As with [`armarium add`](add.md), the name may not be blank, start
or end with whitespace or a dot, hold doubled or non-space whitespace, end with
`.md`, or hold a control character or any of `# ^ [ ] | \ / : * ? " < >`. It
must be free among the records that can see the record, as
[names](record.md#names) require: no other record of the same campaign, or
shared, may have it as its filename or an alias. No other entry in the folder
may have it either, ignoring case and Unicode normalization. A name that
differs only in case is a rename.
Sessions, Clues and Transcripts are not renamed: the vault fixes their names.

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

### Keeping the old name

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

## Deleting a record

`armarium delete PATH` deletes the record when nothing links to it. While
links remain, it lists them on standard output as
[`armarium trace`](trace.md#output) does and changes nothing, so you can
change each one first.

With `--unlink`, it removes the links instead, then deletes the record:

- A body link becomes its display text: `[[Quay Nine|the quay]]` becomes
  `the quay`, and `![[Quay Nine]]` becomes `Quay Nine`.
- An item of a Content record's Appearances that opens with a link to a
  deleted Session is removed, and an emptied list becomes `- N/A`. The
  record's `first_session` and `last_session` are set to the earliest and
  latest Sessions that remain.
- A link that is a whole frontmatter value leaves its list, such as
  `subjects` or `prepared_npcs`, or becomes null, such as `held_by`. A link
  inside frontmatter text, such as a Clue's `text`, becomes its display text.

A required field left null, such as a PC's `player`, fails validation; fill
it in by hand. The record's `image` file is left in place, and the
command says so.

## Links left as written

Links outside records are left as written and reported as warnings, for you
to check: wikilinks in templates, `docs/`, `AGENTS.md`, `.base` and `.canvas`
files, and Markdown links such as `[map](Quay%20Nine.md)` anywhere.

## Nothing half done

Every change is worked out before any file is written. If a record that may
link to the record cannot be parsed, or its frontmatter cannot be rewritten to
hold the change, the command names it and changes nothing. If writing a
file fails or is interrupted, every file is put back as it was. A frontmatter
field is edited in place where it can be; otherwise it is written afresh,
double-quoted, and the rest of the frontmatter is kept.

## Output

Each change is one line on standard output, with four tab-separated fields:

```text
content/Quay Nine.md			renamed to content/Quay Ten.md
campaigns/campaign_1/clues/C-1-0001.md	subjects		[[Quay Nine]] → [[Quay Ten]]
campaigns/campaign_1/sessions/S-1-002.md	Notes > Events	65	[[Quay Nine|the quay]] → [[Quay Ten|the quay]]
```

1. The changed file's path, relative to the vault root, before the change.
2. Where the link sits, as [`armarium trace`](trace.md#output) gives it; empty
   for a change to the whole file.
3. The link's line number, for a body link; empty otherwise.
4. The change.

Standard error then lists each file the command changes, such as
`content/Quay Nine.md: moved to content/Quay Ten.md`, and how many.
`--dry-run` checks the change as a real run would and prints the same lines,
saying what would change, without changing anything.

The command exits with `0` once the change is made, `1` when the command
refuses, and `2` for a usage error. Run [`armarium validate`](validate.md) on
the vault afterwards.
