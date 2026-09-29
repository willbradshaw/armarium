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
`held_by` in that block.

The new record must pass the vault's schema and contextual checks; failures
remove it and report diagnostics. The command then validates the whole vault.

## Sessions

```sh
armarium add session --campaign 1 --vault ../my-vault
```

Inside a campaign directory or its subdirectories, omit `--campaign` to use that
campaign. When running outside a campaign directory, `--campaign` is required.
Omit `--vault` when inside the vault.

The command uses the vault's Session template and Type directory declaration.
It creates `S-N-NNN.md` with the campaign link and session number filled in;
dates and other initial values come from the template. The default number is
one greater than the largest existing session number in that campaign,
including sessions in subdirectories. Use `--number N` to choose an unused
number from 1 to 999. Existing records are never overwritten.

The new record must pass the vault's schema and contextual checks; failures
remove it and report diagnostics. The command then validates the whole vault.

## Players

```sh
armarium add player "Alex" --campaign 1 --vault ../my-vault
armarium add content "Mira" --subtype PC --campaign 1 --player Alex --vault ../my-vault
```

Inside a campaign directory or any descendant, omit `--campaign` to use that
campaign; otherwise it is required. `--campaign N` overrides inference.
Omit `--vault` when inside the vault. Names may contain spaces; omit `.md`.
Existing records are never overwritten.

The command uses the vault's Player template and declared campaign directory.
The standard template creates an unassigned Player with `plays: []`; local
initial values and body text are preserved, and configured links must target
shared or same-campaign PCs. No PCs or backlinks are changed. Use
[add content](#content) to create a PC linked to the new Player.

The new record must pass local schema and contextual checks; failures remove
it. Whole-vault validation follows; if that fails, the valid Player is retained
for inspection and the command exits with status 1.
