# Validation

`armarium validate` is a read-only command which validates one or more paths against the rules defined in these documents, reporting each way they depart from expectations. See [Command line](cli.md) for invocation details.

## Scope

What is validated depends on the path given:

- Passing a single [record](record.md) validates that file alone, in the context of the [vault](vault.md) that contains it.
- Passing a directory inside a vault validates every record within it.
- Passing a vault root validates every record within it, as well as the vault's layout.
- Passing a directory that contains one or more vault roots validates each vault root within it, ignoring any files outside a vault.

Hidden files, symlinks, `__pycache__` and `node_modules` are never read.
Templates in `reference/templates/` are parsed but not validated, and are
counted as skipped.

## Order

Each record is first parsed, then checked for a valid [type](type.md), then validated against that type's schema, then given further checks. A record that fails at one stage does not go through later stages. A vault root's layout is checked once, after its records.

## Checks

Some checks are run for every record of every type:

- The record must have a valid type and validate against that type's schema
- The record must be placed correctly in the filetree given its type
- The record must have a valid filename for its type
- Every wikilink in the record must resolve uniquely, and any heading or block anchor it names must exist

Beyond this, some types of record undergo additional checks to ensure they obey the rules defined in their [Type documentation](type.md). For example, some frontmatter fields must link to valid records of a particular type.

## Output

Each finding is one line on standard error, with a standard format:

```text
[TIME] SEVERITY: PATH:FIELD:LINE - ID - MESSAGE
```

where:

- `TIME` is the logging time, with format `YYYY-MM-DD HH:MM:SS.SS UTC`
- `SEVERITY` is `ERROR`, `WARNING` or `INFO`
- `PATH` is the offending file's path, relative to the directory passed to `armarium validate`, or to the vault root when a single record is passed; `.` for a finding about the vault itself
- `FIELD` is the offending frontmatter field, if any, or blank otherwise
- `LINE` is the offending line number in the file body, if any, or blank otherwise
- `ID` is the rule identifier causing the finding, such as `link.missing`
- `MESSAGE` is the human-readable finding message

For example:

```text
[2026-09-25 19:35:32.83 UTC] ERROR: .:: - vault.required - required directory assets is missing
[2026-09-25 19:35:32.83 UTC] ERROR: campaigns/campaign_1/content/Quay Nine.md:parent_location: - link.missing - cannot uniquely resolve [[Port Brisele]]; use a vault-relative path
[2026-09-25 19:35:32.83 UTC] ERROR: campaigns/campaign_1/content/Quay Nine.md::11 - link.missing - cannot uniquely resolve [[The Bell Acord]]; use a vault-relative path
[2026-09-25 19:35:32.83 UTC] ERROR: campaigns/campaign_1/sessions/S-1-004.md:type: - record.type - type is required and must be a canonical wikilink
[2026-09-25 19:35:32.83 UTC] INFO: 66 checked, 6 skipped, 0 unsupported
```

Findings are sorted by path and rule, so runs are comparable. The final line
counts records: `N checked, N skipped, N unsupported` — validated, skipped
templates, and records whose type has no schema.

Only `ERROR` findings fail the run. The command exits with `0` when nothing
failed, `1` after reporting when any record has an error, ending with an
`ERROR: N files failed validation` line, and `2` for a usage error.

Rule identifiers group into families:

| Family | Reports | Rules on |
| --- | --- | --- |
| `parse.` | a file that cannot be read as frontmatter and body | [Records](record.md#anatomy) |
| `record.` | the `type` field, templates, placement and filename identity | [Records](record.md), [Types](type.md) |
| `schema.` | a record against its schema; missing, invalid or unmatched schemas | [Records](record.md#types-statuses-and-schemas) |
| `link.` | links that do not resolve, are malformed or ambiguous, lack their anchor, target the wrong kind of record, repeat, or form a cycle | [Records](record.md#links), [Types](type.md) |
| `campaign.` | campaign directories and `campaign_N` blocks, and a Session's campaign | [Campaigns](campaign.md) |
| `status.` | a `status` whose Status does not apply to the record's type | [Records](record.md#types-statuses-and-schemas) |
| `history.` | a Content record's Appearances and campaign blocks | [Campaigns](campaign.md#state), [Content](type.md#content) |
| `clue.` | a Clue's `subjects` against its `text` | [Clue](type.md#clue) |
| `transcript.` | the transcript grammar | [Transcript](type.md#transcript) |
| `vault.` | the vault skeleton, campaign layout, declared directories and stray entries | [Vault layout](vault.md) |
