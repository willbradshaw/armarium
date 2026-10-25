# Validation

`armarium validate` checks records, directories and vaults against the rules
these pages set out, and reports each way they depart from them. It changes
nothing.

## Usage

```text
armarium validate [--vault VAULT] [--jobs N] PATH
```

`PATH` is a record, a directory or a vault; [Scope](#scope) says what each
gets. The command recognises a vault by its `reference/types/` and
`campaigns/` directories, so it does not find a vault missing either: a
directory run passes over it as not a vault and reports nothing checked, and
the command refuses a single record inside it. `--vault VAULT` names the vault
directory explicitly, so that the command validates such a vault anyway and
reports what it lacks.

`--jobs N` validates a directory's records with `N` worker processes; the
findings and their order are the same as with one. Without it, a vault's
records get one worker per 500, up to one per CPU, so one process validates
fewer than 1,000: every worker indexes the vault first, which slows small
runs. `--help` prints the usage.

```sh
armarium validate .                                    # the vault in the current directory
armarium validate campaigns/campaign_1/clues           # every Clue of one campaign
armarium validate content/Port\ Briselle.md            # one record
armarium validate . --vault .                          # a vault missing part of its skeleton
armarium validate . --jobs 1                           # a large vault, in one process
```

## Scope

What the command validates depends on the path:

- A single [record](record.md): that file alone, in the context of the
  [vault](vault.md) that contains it.
- A directory inside a vault: every record in it.
- A vault root: every record in the vault, and the vault's layout.
- A directory that contains one or more vault roots: each of those vaults,
  ignoring files outside a vault.

The command never reads hidden files, symlinks, `__pycache__` or
`node_modules`. It parses templates in `reference/templates/` but does not
validate them, and counts them as skipped.

## Order

The command parses each record, then checks that it has a valid
[type](type.md), then validates it against that type's schema, then runs the
further checks. A record that fails one stage goes through no later stage. The
command checks a vault root's layout once, after its records.

## Checks

Every record of every type must:

- have a valid type and satisfy that type's schema;
- sit where its type places it in the vault;
- have a valid filename for its type;
- have every wikilink resolve to one file, and every heading or block anchor
  a link names exist.

Some types have further checks for the rules their [Type records](type.md)
set out. For example, some frontmatter fields must link to valid records of a
particular type.

## Output

Each finding is one line on standard error, in this format:

```text
[TIME] SEVERITY: PATH:FIELD:LINE - ID - MESSAGE
```

where:

- `TIME` is when the finding was logged, as `YYYY-MM-DD HH:MM:SS.SS UTC`;
- `SEVERITY` is `ERROR`, `WARNING` or `INFO`;
- `PATH` is the file's path, relative to the directory given to
  `armarium validate`, or to the vault root when it was given a single
  record; it is `.` for a finding about the vault itself;
- `FIELD` is the frontmatter field at fault, or blank;
- `LINE` is the line number in the file body at fault, or blank;
- `ID` is the identifier of the rule, such as `link.missing`;
- `MESSAGE` describes the finding.

For example:

```text
[2026-09-25 19:35:32.83 UTC] ERROR: .:: - vault.required - required directory assets is missing
[2026-09-25 19:35:32.83 UTC] ERROR: campaigns/campaign_1/content/Quay Nine.md:parent_location: - link.missing - cannot uniquely resolve [[Port Brisele]]; use a vault-relative path
[2026-09-25 19:35:32.83 UTC] ERROR: campaigns/campaign_1/content/Quay Nine.md::11 - link.missing - cannot uniquely resolve [[The Bell Acord]]; use a vault-relative path
[2026-09-25 19:35:32.83 UTC] ERROR: campaigns/campaign_1/sessions/S-1-004.md:type: - record.type - type is required and must be a canonical wikilink
[2026-09-25 19:35:32.83 UTC] INFO: 66 checked, 8 skipped, 0 unsupported
```

The command sorts findings by path and rule, so runs are comparable. The final
line counts records: `N checked, N skipped, N unsupported` — validated,
skipped templates, and records whose type has no schema.

Only `ERROR` findings fail the run. The command exits with `0` when nothing
failed, `1` after reporting when any record has an error, ending with an
`ERROR: N files failed validation` line, and `2` for a usage error.

Rule identifiers group into families:

| Family | Reports | Rules on |
| --- | --- | --- |
| `parse.` | a file that cannot be read as frontmatter and body | [Records](record.md#anatomy) |
| `record.` | the `type` field, a Content or Reference `subtype` the vault does not permit, templates, placement, the subfolder declared for a subtype, filename identity, a name or alias shared with another record, and an `image` path that names no file | [Records](record.md), [Types](type.md), [Extensions](extensions.md) |
| `schema.` | a record against its schema; missing, invalid or unmatched schemas | [Records](record.md#types-statuses-and-schemas) |
| `link.` | links that do not resolve, are malformed or ambiguous, lack their anchor, target the wrong kind of record, repeat, or form a cycle | [Records](record.md#links), [Types](type.md) |
| `campaign.` | campaign directories and `campaign_N` blocks, and a Session's campaign | [Campaigns](campaign.md) |
| `status.` | a `status` whose Status does not apply to the record's type | [Records](record.md#types-statuses-and-schemas) |
| `history.` | a Content record's Appearances and campaign blocks | [Campaigns](campaign.md#state), [Content](type.md#content) |
| `clue.` | a Clue's `subjects` against its `text` | [Clue](type.md#clue) |
| `transcript.` | the transcript grammar | [Transcript](type.md#transcript) |
| `style.` | art in an illustration style's directory over its size budget | [Illustrating a record](illustrate.md#styles) |
| `extension.` | enabled extension declarations, schemas and templates, and code blocks an extension requires to be YAML | [Extensions](extensions.md) |
| `vault.` | the vault skeleton, campaign layout, declared directories and stray entries; copies of Armarium files and extensions that are out of date | [Vault layout](vault.md), [Updating a vault](update.md) |
