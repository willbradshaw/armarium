---
name: update-record
description: Create or change any record in this Armarium vault (Content, Session, Clue, Note, Player, Transcript or Reference). This is the base procedure every record change follows, and the one other skills in this vault build on - find the record, read its Type record, create or edit it, validate, resolve new links, and check the records that link to it. Use it whenever a task adds, edits, renames, merges or deletes a record.
---

# Update a record

Follow these steps for every record you create or change. Run the commands from
the vault root, or add `--vault PATH`.

## 1. Find the record

```sh
armarium find "NAME"
```

This lists every record with that filename or alias, one per line: path, type,
`name` or `alias`, and summary. It exits with 1 when there is none.

- **One match:** that is the record. Edit it; do not create another.
- **Several matches:** read their summaries to pick the right one, and ask if
  it is not clear.
- **No match:** the entity may be filed under another name. Before creating
  anything, search the filenames for its most distinctive word, and try a
  fuller or shorter form of the name. If you find the record, use it, and add
  the name you were given to its `aliases` if people really use that name.

If you cannot tell whether an existing record is the same entity, ask.

## 2. Read the Type record

`reference/types/TYPE.md` says what a valid and meaningful record of that type
is: its fields, its body sections and what belongs in each. For a subtype that
an extension adds, also read `reference/extensions/NAME/README.md`.

Read it before you write. It is the authority for this vault, and this vault's
copy may differ from what you expect.

## 3. Create or edit

**To create**, use `armarium add`; never copy a template or write the file by
hand. The command chooses the directory and filename, fills in the template's
defaults and validates the result.

```sh
armarium add content "NAME" --subtype SUBTYPE --campaign N --frontmatter '{"summary": "..."}'
```

`armarium add --help` lists the record kinds, and `--frontmatter-file PATH`
takes the fields from a JSON file. Then edit the new record's body.

**To edit**, read the whole record first, then change only what the task needs:

- Keep existing links. Do not turn `[[Name]]` into plain text.
- Do not reword, reorder or reformat text you are not changing.
- In frontmatter, quote links (`"[[Name]]"`) and leave an empty field bare
  (`field:`).

Write only what your source states. Do not fill a record out with plausible
detail.

## 4. Validate

```sh
armarium validate "PATH"
armarium validate .
```

Validate each record after you change it, and the whole vault once at the end.
Fix every error your change introduced. If the vault had errors before you
started, report them; do not fix them unasked.

## 5. Resolve new links

Every link must resolve to exactly one file. For each link you added that does
not:

1. Look for the record as in step 1. If it exists under another name, link to
   that name and keep your wording as display text: `[[Real Name|name used]]`.
2. Otherwise create a stub with `armarium add`, holding only what your source
   states. A Content stub may have an empty summary.
3. If two files share the name, spell enough of the path to tell them apart:
   `[[campaign_1/content/Name]]`.

Never leave a link unresolved, and never remove a link to avoid making a stub.

## 6. Check the records that link to it

```sh
armarium trace "PATH"
```

This lists every link to the record, one per line: the linking record, the
frontmatter field or body headings where the link sits, and the line number.

Run it when your change could make other records wrong:

- **Renamed or moved:** a rename outside Obsidian updates no links. Fix each
  one listed.
- **Merged or deleted:** repoint or remove every link before deleting the file.
- **A fact other records repeat has changed:** read each place in context and
  update the ones that are now wrong.

A new record has nothing linking to it, so skip this step for one. Do not edit
a record only because it links to yours.

## 7. Ask, then report

Ask the user when:

- you cannot tell whether a record already exists for the entity;
- it is unclear whether a record is shared or belongs to one campaign;
- your source does not settle a fact the record needs;
- your change would contradict what another record says.

When you finish, say which records you created, which you changed, which stubs
you made, and what you left for the user to decide.
