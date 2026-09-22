# Schema development

For contributors changing and testing schemas. Record authoring rules
live in the vault's `reference/types/` pages.

## Input and schema selection

Draft 2020-12 schemas validate `{frontmatter, body}`: parsed frontmatter and the
Markdown body. Dates are represented as ISO date strings; Session `date` accepts
`YYYY-MM-DD` or null. Custom frontmatter fields are allowed.

Each supported `type` has a schema in the vault's `reference/schemas/` directory:

| `type` | Schema |
| --- | --- |
| `[[types/Content]]` | `content.schema.json` |
| `[[types/Clue]]` | `clue.schema.json` |
| `[[types/Session]]` | `session.schema.json` |
| `[[types/Player]]` | `player.schema.json` |
| `[[types/Transcript]]` | `transcript.schema.json` |
| `[[Reference]]` | `reference.schema.json` |

Schemas apply to typed records, not unfinished templates or untyped supporting
documents such as indexes, type definitions and `applies_to` status definitions.
References are local. The tests enable URI and date format assertions.

## Limits

Body regexes check basic structure. Duplicate headings and matching fenced text
can satisfy Content/Session heading checks; Transcript checks only one heading
and attributed entry. Clue requires Sessions plus one Base embed or triple-backtick view but
cannot establish that it executes or that an embedded Base exists. Link existence, target kinds, campaign and
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
