# Creating a vault

```sh
armarium init ../my-vault
```

`armarium init PATH` initializes a new vault in a fresh directory by copying the
[starter vault](../vaults/starter/). `PATH` must be a nonexistent directory;
existing files and directories (even empty ones) are refused, as are symbolic
links. Missing parent directories are automatically created. If copying fails or
is interrupted, the partially created vault is removed safely. After copying
completes, the new vault undergoes validation before success is reported.

The command reports progress:

```text
Initializing new vault at PATH
New vault successfully initialized; validating
Validation completed successfully
```

Validation also reports warnings and errors. Validation failures exit with
status 1 and leave the vault available for inspection, without reporting success.

`init` does not initialize Git or install Obsidian plugins. After completion,
open the new vault in Obsidian and enable the plugins listed in
[the README](../README.md) before editing. After initialization, the vault can be
moved or placed in its own Git repository.
