# Creating a vault

```sh
armarium init ../my-vault
```

`armarium init PATH` creates a new vault by copying the
[starter vault](../vaults/starter/) to `PATH`, which must not exist. It refuses
an existing file or directory, even an empty one, and a symbolic link. It
creates any missing parent directories. If copying fails or is interrupted, it
removes the partial vault. Once the copy is complete, it validates the new
vault before reporting success.

`armarium init ../my-vault --extension EXTENSION` also installs an
[extension](extensions.md), before validation. An extension applies to the
whole vault. Repeat `--extension` to install several. If installing an
extension fails, `init` undoes the whole setup.

`armarium init --force PATH` replaces an existing directory and **all its
contents** with the starter vault. It still refuses a file or a symbolic link.
It prepares the new vault, with any extensions, before removing the old
directory, so a failure during setup leaves the existing directory intact.

The copy includes `AGENTS.md`, `docs/` and the
[skills for coding agents](agents.md).

[`armarium update`](update.md) keeps the copied files up to date, except those
in `campaigns/`, `content/`, `notes/`, `assets/` and `.scratch/`, which only
start the vault off. `init` records these managed files in a hidden
`.armarium/` directory: a copy of each as Armarium supplied it in
`.armarium/base/`, and the supplying Armarium version in `.armarium/vault.json`.
Keep `.armarium/` with the vault, including in Git.

`init` does not set up Git or install Obsidian plugins. Before editing, open
the new vault in Obsidian and enable the plugins listed in
[the README](../README.md). You can move the vault afterwards, or make it its
own Git repository.
