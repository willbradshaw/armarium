---
name: update-record
description: Creates, edits, renames, merges or deletes one record in this Armarium vault, then fixes validation errors. Creates stub records for introduced dangling links.
---

# Update a record

This procedure writes one record and keeps the vault valid. It does not update
the other records that the change may affect. To rename, merge or delete a
record, follow [Renaming, merging or deleting a record](#renaming-merging-or-deleting-a-record)
instead of steps 1 to 5.

You need three things:

- the name of the entity the record is for;
- the campaign the change belongs to, if it belongs to one;
- a source that says what to record, such as the user's request, a Session or
  the GM's notes.

Run the commands from the vault root, or add `--vault PATH`.

If `.agents/skills/update-record/addenda/` exists, read every file in it before you
start. Each adds to this procedure, for an extension the vault has enabled or
for the vault itself, and applies as if it were written here. Where an addendum
and this file disagree, follow the addendum; where two addenda disagree, follow
`vault.md`, the vault's own.

## 1. Find the record

```sh
armarium find "NAME" [--campaign N]
```

- If no match is returned, create the record at the appropriate location.
- If a single match is returned, edit that record.
- If multiple matches are returned, or if the `find` command encounters a
  problem, report the problem and terminate the skill.

## 2. Read the Type record

`reference/types/TYPE.md` says what a valid and meaningful record of that type
is: its fields, its body sections and what belongs in each. For a subtype that
an extension adds, also read `reference/extensions/NAME/README.md`.

Read it before you write. It is the authority for this vault, and this vault's
copy may differ from what you expect.

## 3. Write the record

**To create**, use
[`armarium add`](https://github.com/willbradshaw/armarium/blob/main/docs/add.md);
never copy a template or write the file by hand. The command chooses the
directory and filename, fills in the template's defaults and validates the
result. Then edit the new record's body.

**To edit**, read the whole record first, then change only what the source
calls for:

- Keep existing links. Do not turn `[[Name]]` into plain text.
- Do not reword, reorder or reformat text you are not changing.
- In frontmatter, quote links (`"[[Name]]"`) and leave an empty field bare
  (`field:`).

Write only what the source states, where the Type record says it belongs.
Where the source does not give a value, leave the field or section empty. Ask
the user if the source does not settle something the record requires.

## 4. Validate

```sh
armarium validate "PATH"
```

Fix every error your change introduced, apart from `link.missing`, which step 5
handles.

## 5. Create stubs for links that name no record

Validation reports each link you wrote that names no record as `link.missing`.
For each one, run `armarium find` on the name, as in step 1.

- **It is another record's alias:** link to that record's filename and keep
  your wording as display text: `[[Real Name|name used]]`.
- **There is no record:** create a stub with `armarium add`, under the name the
  link uses, with only the fields the command requires. Take its type and
  subtype from how the source describes the entity, and ask if that is unclear.

Do not fill the stub in, and do not run this procedure on it.

For `link.ambiguous`, two files share the name: spell enough of the path to
tell them apart, such as `[[campaign_1/content/Name]]`.

## 6. Validate the vault and report

```sh
armarium validate .
```

Fix any error your change introduced. If the vault had errors before you
started, report them; do not fix them unasked.

Then say which record you wrote, which stubs you created, and which existing
records you linked to. Those records and stubs may need updating from the same
source; that is for whoever asked for this change to decide.

## Renaming, merging or deleting a record

Never rename, move or delete a record's file by hand, in Obsidian or with
Git: every link to it would break. Use the commands below, which rewrite
those links. They are described in [Renaming a record](https://github.com/willbradshaw/armarium/blob/main/docs/rename.md),
[Merging records](https://github.com/willbradshaw/armarium/blob/main/docs/merge.md) and
[Deleting a record](https://github.com/willbradshaw/armarium/blob/main/docs/delete.md).

1. Find each record's path with `armarium find`, as in step 1.
2. Run the command with `--dry-run`, and show the user what it would change:
   - `armarium rename "PATH" "NEW NAME"` gives a record a new name. Add
     `--alias` when the entity still goes by the old name: it stays an alias,
     and prose keeps its wording.
   - `armarium merge --from "SOURCE" --into "TARGET"` combines two records
     that turn out to be one entity. `SOURCE` goes, and its links point at
     `TARGET`; make `TARGET` the record whose name the user wants to keep.
   - `armarium delete "PATH"` deletes a record. Delete only when the user
     asks for the record to go.
3. Run the command without `--dry-run` once the user agrees.

When `merge` lists conflicts, show each one to the user and ask which is
right; do not choose. Edit the records as the user decides, so that they
agree, then merge again. After the merge, the merged Notes may repeat
themselves; tidy them only if the user asks.

When `delete` lists the links that remain, show them to the user. Change
each one as the user decides or, if the user agrees that they should become
plain text, run `armarium delete "PATH" --unlink`.

Then validate the vault and report, as in step 6. Also report each warning
about a link the command left as written, for the user to check.
