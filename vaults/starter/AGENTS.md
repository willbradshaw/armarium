# Agent instructions

This is an Armarium vault. Read [the vault guide](docs/armarium.md) first: it
covers the layout, the record types and the `armarium` commands.

## Before you change a record

Read its Type record in `reference/types/`. It says what the record must hold
and what belongs where, and it is the authority for this vault.

## While you work

- **Use the commands.** Create records with `armarium add`, look them up with
  `armarium find`, and list what links to one with `armarium trace`. Do not copy
  templates or search for names by hand when a command does it.
- **Record only what your source states.** A source is the user, a transcript
  or the GM's own notes. Never invent a fact to complete a record; ask.
- **Keep kinds of knowledge apart.** A Clue is a candidate fact, not an
  established one. What a Session prepares has not happened until its Events
  say so.
- **Leave every link resolving.** Where a link names no record, create the
  record.
- **Change only what the task needs.** Do not reword or reformat the rest.

## Before you finish

- Run `armarium validate .` and fix every error your change introduced.
- Report the records you created and changed, and anything left to decide.

## What to leave alone

- `reference/extensions/NAME/`: installed extension files, replaced by
  `armarium extension update`.
- `.obsidian/`: the Obsidian settings the records rely on.

## This vault

Add this vault's own rules below.
