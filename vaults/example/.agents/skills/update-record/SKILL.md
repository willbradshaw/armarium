---
name: update-record
description: Creates or edits one record in this Armarium vault, then fixes validation errors. Creates stub records for introduced dangling links.
---

# Update a record

This procedure writes one record and keeps the vault valid. It does not update
the other records that the change may affect.

You need three things:

- the name of the entity the record is for;
- the campaign the change belongs to, if it belongs to one;
- a source that says what to record, such as the user's request, a Session or
  the GM's notes.

Run the commands from the vault root, or add `--vault PATH`.

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
