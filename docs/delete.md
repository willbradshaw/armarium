# Deleting a record

```sh
armarium delete "content/Quay Nine.md" --vault ../my-vault
```

`armarium delete PATH` deletes a [record](record.md), refusing while
[links](record.md#links) to it remain in the [vault](vault.md). Delete records
this way rather than in a file manager: a file deleted by hand leaves every
link to it broken.

## Choosing the record

`PATH` is the record's file path, chosen as for
[`armarium trace`](trace.md#choosing-the-file): without `--vault`, absolute or
relative to the current directory; with `--vault VAULT`, relative to the vault
root, so a path printed by [`armarium find`](find.md) can be passed as it is.

The command refuses to delete Types and Statuses, which define the vault, and
each campaign's `reference/Campaign.md` and `reference/indexes/Clues.md`.

## Links to the record

While links to the record remain, the command lists them on standard output as
[`armarium trace`](trace.md#output) does and changes nothing, so you can
change each one first. With no links, it deletes the file.

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
it in by hand. The record's `image` file is left in place, and the command
says so.

Links outside records, and Markdown links, are left as written and reported as
warnings, as [`armarium rename`](rename.md#links-left-as-written) reports
them. As with rename, [nothing is half done](rename.md#nothing-half-done):
every change is worked out before any file is written, and every file is put
back if writing one fails.

## Output

Each change is one line on standard output, with the four tab-separated fields
that [`armarium rename`](rename.md#output) prints:

```text
content/Quay Nine.md			deleted
campaigns/campaign_1/clues/C-1-0001.md	subjects		[[Quay Nine]] removed
campaigns/campaign_1/sessions/S-1-002.md	Notes > Events	65	[[Quay Nine|the quay]] → the quay
```

Standard error then lists each file the command changes, and how many.
`--dry-run` checks the deletion as a real run would and prints the same lines,
saying what would change, without changing anything.

The command exits with `0` once the record is deleted, `1` when links remain
or it cannot be deleted, and `2` for a usage error. Run
[`armarium validate`](validate.md) on the vault afterwards.
