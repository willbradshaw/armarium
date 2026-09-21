Pages with `type: "[[types/Player]]"` are real players, with links to the PCs they play.

Use [[templates/Player]] in `campaign_1/players/`, named for the player. Fill
`plays` with a YAML list of quoted, vault-relative PC links, for example
`"[[campaign_1/pcs/Mira]]"`. The blank template leaves `plays` null, like other
unfilled starter properties; use `plays: []` for an explicitly empty list.
No biography or additional personal information is required.
