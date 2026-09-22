# Schema development

For contributors changing schemas or integrating a validator. Record authoring
rules live in the vault's `reference/types/` pages.

## Input and schema selection

Draft 2020-12 schemas validate exactly `{frontmatter, body}`: a parsed YAML object
and the Markdown after its closing delimiter. Custom frontmatter fields are
allowed. Supply JSON-compatible values: normalize YAML dates to `YYYY-MM-DD`
and timestamps to ISO 8601 strings preserving offsets; leave quoted strings
unchanged. Session `date` accepts date-only strings or null, not timestamps.
Use a safe YAML loader; reject duplicate/non-string keys, non-finite numbers,
cyclic aliases and unsupported scalar types. Preserve body text; LF and CRLF work.

Select from the target vault's `reference/schemas/` by exact `type`:

| `type` | Schema |
| --- | --- |
| `[[types/Content]]` | `content.schema.json` |
| `[[types/Clue]]` | `clue.schema.json` |
| `[[types/Session]]` | `session.schema.json` |
| `[[types/Player]]` | `player.schema.json` |
| `[[types/Transcript]]` | `transcript.schema.json` |
| `[[Reference]]` | `reference.schema.json` |

Exclude unfinished templates and untyped supporting documents, including indexes,
type definitions and `applies_to` status definitions. Report unknown explicit
types as unsupported. References resolve locally; enable URI and date format
assertions (`FormatChecker` in Python jsonschema).

## Limits

Body regexes check basic structure. Duplicate headings and matching fenced text
can satisfy Content/Session heading checks; Transcript checks only one heading
and attributed entry. Clue requires Sessions plus one triple-backtick view but
cannot establish that it executes. Link existence, target kinds, campaign and
filename identity, chronology, reciprocal relationships and history consistency
require vault-aware validation.

## Tests

From the repository root, without installing Armarium:

```sh
python3 -m venv /tmp/armarium-schema-venv
/tmp/armarium-schema-venv/bin/pip install -r tests/schemas/requirements.txt
/tmp/armarium-schema-venv/bin/python -m unittest discover -s tests/schemas -v
```

Tests cover meta-schemas, offline references, parsed JSON fixtures, committed
Markdown records and identical schema/type-reference copies in both vaults.
The PyYAML fixture loader is test support, not a production parser.
