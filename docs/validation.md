# Validation

`armarium validate PATH` reads a [vault](vault.md) and reports every way its
[records](record.md) and layout depart from the rules on these pages. It
reads only; nothing is modified. See [Command line](cli.md) for invocation.

## Scope

What is validated depends on the path given:

- **A record**: that file alone, against the vault that contains it. The
  vault is the nearest enclosing directory with `reference/types/` and
  `campaigns/`, or the one named with `--vault`.
- **A directory inside a vault**: every record beneath it.
- **A vault root**: every record beneath it, plus the vault's layout.
- **A directory that is not in a vault**: every vault root found beneath it,
  each as above. Markdown outside any vault is ignored.

Hidden entries, symlinks, `__pycache__` and `node_modules` are never read.
Templates in `reference/templates/` are parsed but not validated, and are
counted as skipped.

## Order

Each record is parsed first — the file, its frontmatter and its body — and a
record that cannot be parsed, or that has no canonical `type`, gets no
further checks. A parsed and typed record is validated against its type's
schema and then given the cross-record checks: its links, its placement and
filename, its campaign blocks, and the rules specific to its
[type](type.md). A vault root's layout is checked once, after its records.

## What runs where

Every record gets parsing, the `type` check, its schema, link resolution,
placement and the filename rules. Beyond those:

| Type | Further checks |
| --- | --- |
| Clue | `subjects` against `text`; `first_session`/`last_session` order; `superseded_by` chain |
| Content | `campaign_N` blocks; Appearances order and agreement with the blocks; `parent_location` chain |
| Note | none |
| Player | none |
| Reference | none |
| Session | `campaign` names the containing campaign; `session_number` matches the filename |
| Status | none |
| Transcript | `session` names the Session the filename names; the transcript grammar |
| Type | none |

The typed-link rules on the [type](type.md) page (what a field must link
to, and in which campaign) are part of link resolution and so apply
wherever those fields appear.

## Output

Each finding is one line on standard error:

```text
[2026-09-25 18:52:05.91 UTC] ERROR: campaigns/campaign_1/content/Quay Nine.md [parent_location]: link.missing: cannot uniquely resolve [[Port Brisele]]; use a vault-relative path
[2026-09-25 18:52:05.91 UTC] ERROR: campaigns/campaign_1/content/Quay Nine.md:11: link.missing: cannot uniquely resolve [[The Bell Acord]]; use a vault-relative path
[2026-09-25 18:52:05.91 UTC] INFO: 65 checked, 6 skipped, 0 unsupported
```

The location is the file's path relative to the directory given, with the
frontmatter field in brackets when the finding concerns one and a line
number when it lies in the body. Then the rule identifier, then the message.
Findings are sorted by location and rule, so runs are comparable. The final
line counts records: `N checked, N skipped, N unsupported` — validated,
templates, and records whose type has no schema.

Severities are `ERROR`, `WARNING` and `INFO`; only errors fail the run. The
command exits with `0` when nothing failed, `1` after reporting when any
record has an error (`N files failed validation`), and `2` for a usage error.

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

## Boundaries

- Bases views are not executed; an embed is checked only as a link.
- Anchors into files that are not records are not checked.
- Custom fields are not interpreted.
- Nothing is inferred from prose, and nothing is corrected.
