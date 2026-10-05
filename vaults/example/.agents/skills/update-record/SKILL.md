---
name: update-record
description: Create or edit a record in this Armarium vault. The base procedure for every record change, which other skills build on. Finds the record, reads its Type record, creates or edits it, validates it, resolves its links and checks the records that link to it.
---

# Update a record

Follow these steps to create or edit a record. Run the commands from the vault
root, or add `--vault PATH`.

## 1. Find the record

```sh
armarium find "NAME"
```

This lists every record with that filename or alias, one per line: path, type,
`name` or `alias`, and summary. It exits with 1 when there is none.

- **One match:** that is the record. Edit it; do not create another.
- **Several matches:** read their summaries to pick the right one, and ask if
  it is not clear.
- **No match:** if the task is to create this record, go on. If you expected
  it to exist, stop and ask the user; do not pick a record with a similar name
  yourself.

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

`armarium add --help` lists the record kinds and their options. Then edit the
new record's body.

**To edit**, read the whole record first, then change only what the task needs:

- Keep existing links. Do not turn `[[Name]]` into plain text.
- Do not reword, reorder or reformat text you are not changing.
- In frontmatter, quote links (`"[[Name]]"`) and leave an empty field bare
  (`field:`).

Write only what your source states. Where the source does not give a value,
leave the field or section empty.

## 4. Validate

```sh
armarium validate "PATH"
```

Validate each record after you change it, and fix every error your change
introduced. A link you added that names no record is reported as
`link.missing`; step 5 deals with those.

Run `armarium validate .` once at the end. If the vault had errors before you
started, report them; do not fix them unasked.

## 5. Create the records that links need

For each `link.missing` that validation reports, run `armarium find` on the
name.

- **It is another record's alias:** link to that record's filename and keep
  your wording as display text: `[[Real Name|name used]]`.
- **There is no record:** create it, under the name the link uses. Follow this
  whole procedure for the new record, so that it holds what your source says
  about that entity and not just a name. Take its type and subtype from how the
  source describes it, and ask only if that is unclear.

A record whose entity the source only names stays nearly empty. That is
allowed; list such records in your report.

For `link.ambiguous`, two files share the name: spell enough of the path to
tell them apart, such as `[[campaign_1/content/Name]]`.

## 6. Check the records that link to it

```sh
armarium trace "PATH"
```

This lists every link to the record, one per line: the linking record, the
frontmatter field or body headings where the link sits, and the line number.

Run it when you changed something other records may repeat or depend on, such
as a summary, who holds an object or where a place is. Read each listed place
in context. Most will need no change; where a linking record now says something
wrong, follow this procedure to correct it.

## 7. Ask, then report

Ask the user when:

- it is unclear whether a record is shared or belongs to one campaign;
- your source does not settle a fact the record needs;
- your change would contradict what another record says.

When you finish, say which records you created and which you changed, name any
you created with little or no content, and list what is left for the user to
decide.
