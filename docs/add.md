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

