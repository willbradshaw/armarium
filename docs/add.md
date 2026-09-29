# Adding to a vault

## Campaigns

Add a [campaign](campaign.md) to an existing vault:

```sh
armarium add campaign --vault ../my-vault
```

Omit `--vault` when running inside the vault. The new campaign number is one
greater than the largest existing number; use `--number N` to choose a positive
number explicitly. Existing campaigns are never overwritten.

The command uses the vault's Campaign and Clues templates and Type directory
declarations, then validates the whole vault. In the templates, `campaign_1`
and clue IDs beginning `C-1-` identify the new campaign and are updated to its
number. Other text is preserved. No players, sessions or content are copied from
existing campaigns. Failed writes remove the partial campaign; validation
failures leave it available for inspection.

## Content

```sh
armarium add content "Port Briselle" --subtype Location --vault ../my-vault
armarium add content "Mira" --subtype PC --campaign 1 --player Alex --vault ../my-vault
```

Use `--subtype NPC|PC|Location|Faction|Object|Lore`. Inside a campaign directory
or its subdirectories, Content defaults to that campaign; elsewhere it is shared.
`--campaign N` overrides this choice. Omit `--vault` when inside the vault.
Names may contain spaces; omit the `.md` extension. Existing records are never
overwritten.

The command uses the vault's Content template and Type directory declaration.
Initial values, including the summary, come from the template. Required nullable subtype fields
start empty unless set in the template. PCs need an existing Player, supplied
with `--player` or in the template; use a vault-relative Player path when its
name is ambiguous.

Shared records start without campaign state. Campaign-specific records get a
`campaign_N` block, where `N` is the selected campaign number; Objects also get
`held_by` in that block. Custom frontmatter values and the Markdown body are preserved, though
YAML formatting and comments are not.

The new record must pass the vault's schema and contextual checks; failures
remove it and report diagnostics. The command then validates the whole vault.
