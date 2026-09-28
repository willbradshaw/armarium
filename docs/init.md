# Creating a vault

```sh
armarium init "../My Setting"
```

`armarium init PATH` copies the bundled starter into a new directory. Its parent
must already exist. The command refuses existing files, directories (even empty
ones), and symlinks. If copying fails or is interrupted, it removes the partially
created vault so the command can be retried. Operational errors are logged and
exit with status 1; incorrect arguments exit with status 2. `--help` shows usage.

After copying, `init` runs full vault validation and reports its diagnostics and
coverage counts. It reports success only if validation passes. Validation failures
exit with status 1 and leave the vault available for inspection. To check it again
after editing, run `armarium validate PATH`.

The vault begins with one campaign, `campaign_1`, and includes the templates,
schemas, Bases views, Obsidian settings and hidden files from `vaults/starter/`.
Open the new folder in Obsidian, enable the plugins listed in the README, and edit
`campaigns/campaign_1/reference/Campaign.md` to describe your campaign.

The installed package supplies the starter; no source checkout, agent or network
access is needed to run `init`. The resulting files belong to you. The vault can
be moved or placed in its own Git repository. `init` does not initialize Git or
install Obsidian plugins.
