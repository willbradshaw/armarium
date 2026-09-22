# Note schemas

These standard JSON Schema Draft 2020-12 files validate a parsed record as
`{"frontmatter": {...}, "body": "Markdown after the closing YAML delimiter"}`.
The envelope requires exactly those two keys. Frontmatter permits custom fields;
only declared fields are constrained. Templates are unfinished forms, excluded
from completed-record validation even when a particular filled form would pass.

## Input and dispatch (integration contract for #24)

Parse YAML using a safe loader. Supply JSON objects with string keys, arrays,
strings, finite numbers, booleans and nulls only. Normalize YAML date scalars to
ISO `YYYY-MM-DD` strings and timestamps to ISO 8601 strings retaining any offset;
quoted strings remain strings. Reject duplicate keys, non-string mapping keys,
non-finite numbers, cyclic aliases and unsupported scalar types during parsing.
Do not stringify arbitrary YAML objects. Preserve body text (LF and CRLF work).
A timestamp is not a Session `date`: that field accepts a date-only string or null.

Dispatch on the exact frontmatter `type` value, using the selected vault's schema
directory. This is the proposed shared mapping for the #24 loader; schema files
use only fragment-local references and need no network retrieval.

| `type` | Schema |
| --- | --- |
| `[[types/Content]]` | `content.schema.json` |
| `[[types/Clue]]` | `clue.schema.json` |
| `[[types/Session]]` | `session.schema.json` |
| `[[types/Player]]` | `player.schema.json` |
| `[[types/Transcript]]` | `transcript.schema.json` |
| `[[Reference]]` | `reference.schema.json` |

A typed Reference record needs only `type`; its body and custom fields are free.
This modest dedicated schema covers the actual Campaign structure without
inventing required headings or taxonomy fields. Untyped type definitions,
indexes (including the Clues index), and status definitions with `applies_to`
are supporting documents, not typed Reference records. Do not add frontmatter
to every Markdown file or infer type from its folder. Unknown explicit types
need an unsupported-type diagnostic in the runtime, not a Reference fallback.

## Local checks and limits

Enable format assertions (`FormatChecker` in Python jsonschema) for Content URI
and Session date syntax. Required keys and nullable values are distinct: bare
YAML `field:` is null, `[]` is an empty list, and `""` is an empty string. See the
type pages for allowed stubs. Custom fields do not gain inferred constraints.

Session and Content body patterns check required heading order, not a Markdown
syntax tree: duplicate headings and matching lines inside fenced code can
satisfy them. Transcript checks one content heading followed by an attributed
speech line, not every line, every section, or speaker identity. Its regex also
accepts matching fenced examples. Clue requires only a Sessions heading and one
nonempty fenced view (three backticks or tildes), allowing arbitrary language and
query text. It rejects commentary outside that view but cannot establish whether
the fenced text executes a view. Embedded/four-character fences are not supported
by this basic contract. View changes in #25 may need a small schema amendment.

Wikilink patterns check canonical field syntax, without aliases or anchors.
They do not establish existence, uniqueness, target kinds, campaign identity,
filename identity, chronological order, reciprocal relationships or history
agreement. Session campaign links target campaign Reference records; absence
links target Players; Player `plays` links target PC Content; Transcript session
links and Clue session fields target Sessions; Clue subjects target Content and
`superseded_by` targets another Clue. Those checks belong to #24/#16. No schema
check establishes canon or link integrity.

## Standalone checks

From the repository root, without installing the Armarium package:

```sh
python3 -m venv /tmp/armarium-schema-venv
/tmp/armarium-schema-venv/bin/pip install -r tests/schemas/requirements.txt
/tmp/armarium-schema-venv/bin/python -m unittest discover -s tests/schemas -v
```

The test-only requirements are jsonschema with format support and PyYAML. Tests
check meta-schemas, offline references, positive/negative JSON fixtures, committed
records, and identical schema/type-reference copies. The small fixture loader
uses PyYAML for committed examples; it is not a production parser or vault CLI.
