---
name: refresh-record
description: Brings one record in this Armarium vault up to date with the records it links to and the records that link to it. Edits only that record.
---

# Refresh a record

This procedure checks one record against the records around it and corrects
that record. It edits no other record.

You need the path of the record;
[`armarium find`](https://github.com/willbradshaw/armarium/blob/main/docs/find.md)
gives the path for a name. Run the commands from the vault root, or add
`--vault PATH`.

## 1. Read the record and its Type record

Read the whole record, then `reference/types/TYPE.md`. For a subtype that an
extension adds, also read `reference/extensions/NAME/README.md`.

Note which fields and sections the Type record says depend on other records.
For example, a Content record's Appearances and campaign blocks follow from
Sessions, and a Clue's `first_session` and `last_session` follow from the
Sessions that prepared or used it.

## 2. Read what links to it

```sh
armarium trace "PATH"
```

Each line gives a record that links to this one, the frontmatter field or body
headings where the link sits, and the line number.

Read each place: the lines around the link, not the whole record. Where the
link sits says what it means, and the linking record's Type record says how to
read that field or section. A Session's preparation is not play; its Events
are.

## 3. Read what it links to

```sh
armarium trace "PATH" --outbound
```

Each line gives a file this record links to, where the link sits in this
record, and the line number.

For each thing this record says about another record, such as who holds an
object, who belongs to a group or where a place lies, read enough of that
record to see whether it still holds.

## 4. Decide what to change

Change this record only where a linked record:

- establishes something this record should hold and does not; or
- shows that something this record says is wrong.

This record's Type record decides what counts. For Content, a mention or a
Session's preparation is not an appearance.

Add nothing that no linked record states. If nothing needs changing, change
nothing.

Where this record and another disagree, correct this record only if the other
is the authority on the point, as a Session's Events are on what happened in
play. If the other record is the one that is wrong, or you cannot tell, leave
both alone and report it.

## 5. Edit and validate

Read the whole record again before editing, then change only what step 4
calls for:

- Keep existing links. Do not turn `[[Name]]` into plain text.
- Do not reword, reorder or reformat text you are not changing.
- In frontmatter, quote links (`"[[Name]]"`) and leave an empty field bare
  (`field:`).

```sh
armarium validate "PATH"
```

Fix every error your change introduced. Every record you drew on exists, so
your change should add no link that names no record; if validation reports
`link.missing`, take that link out and report it.

## 6. Report

Say what you changed and which linked record supports each change. List the
disagreements you left alone, and any place you could not judge.
