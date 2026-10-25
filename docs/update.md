# Updating a vault

```sh
armarium update --dry-run
armarium update
```

After upgrading Armarium, run `armarium update` to bring the files Armarium
copied into the vault up to date: its schemas, Type and Status records,
templates, views, bases and styles, `docs/armarium.md`, `AGENTS.md`, Obsidian
settings and [agent skills](agents.md). `--vault` selects the vault; it defaults
to the vault containing the current directory. `--dry-run` reports the changes
without making them.

The command never changes records, `campaigns/`, `content/`, `notes/`,
`assets/`, the vault's own skill addenda, or files Armarium did not copy.
Extensions, and the addenda they install, change only with
[`--extensions`](#extensions).

## What changes

[`armarium init`](init.md) records each managed file as Armarium supplied it in
`.armarium/base/`. The update compares that copy with the vault's file and the
running Armarium's:

| Vault's file | Armarium's file | Result |
| --- | --- | --- |
| unchanged | changed | updated |
| changed | unchanged | kept |
| changed | changed | merged line by line |
| deleted | any | left out |
| missing | new | added |
| different | new | a [conflict](#conflicts) |
| unchanged | dropped | removed |
| changed | dropped | kept as the vault's own |

The report lists every file the update writes, and each file it leaves alone
that Armarium has changed or dropped. The update makes every change at once,
records the running Armarium's files in `.armarium/`, and validates the vault.
A failed or interrupted update restores the vault.

## Conflicts

Where the vault and Armarium changed the same lines, the update changes
nothing in the vault and exits with status 1. For each such file it writes the
merge to the same path under `.scratch/armarium-update/`, with both versions,
the vault's first:

```text
<<<<<<< vault
The vault's lines
=======
Armarium's lines
>>>>>>> armarium
```

Edit each such place in the `.scratch/` file to what the vault needs, delete the
marker lines, and run `armarium update` again. It then makes the whole update,
using each resolved file in place of the vault's, and deletes
`.scratch/armarium-update/`. The vault's files never hold conflict markers, and
`.scratch/` is not committed.

A file that still holds markers stays a conflict. If the vault's file or
Armarium's changes before the next run, the update writes that merge afresh.
`--dry-run` reports conflicts without writing anything.

## Validation

[Validation](validate.md) reports `vault.outdated` when the files recorded in
`.armarium/` differ from the running Armarium's, apart from `local` paths, or an
installed extension's files differ from those Armarium supplies. Upgrading
Armarium therefore fails validation until the vault is updated, including
while conflicts wait to be resolved.

## Keeping a file as the vault's own

To stop updates to a managed file, add its path to `local` in
`.armarium/vault.json`:

```json
{
  "armarium_version": "0.1.0",
  "local": ["reference/styles/Gear.md"]
}
```

To leave a file out of the vault, delete it; updates do not add it back. To
restore it, copy it from `.armarium/base/`.

## Versions

`.armarium/vault.json` records the `armarium_version` of the last update.
Updating with an older Armarium requires `--allow-downgrade`.

## Extensions

```sh
armarium update --extensions
```

`--extensions` also updates each installed [extension](extensions.md) whose
files differ from those the running Armarium supplies, after the vault's other
files. Each is replaced as [`armarium extension update`](extensions.md#updating)
replaces it: edits to its installed files are overwritten, not merged. A
failure restores the extension being updated; those updated before it stay
updated.
