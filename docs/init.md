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

Validation reports warnings and errors; otherwise, the only output is
`New vault successfully initialized and validated at PATH`. Validation failures
exit with status 1 and leave the vault available for inspection.

`init` does not initialize Git or install Obsidian plugins. After completion,
open the new vault in Obsidian and enable the plugins listed in
[the README](../README.md) before editing. After initialization, the vault can be
moved or placed in its own Git repository.
