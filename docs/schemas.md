# Schema development

This page is for contributors who change and test the schemas. The rules for
writing records are in the vault's Type records, in `reference/types/`.

## Input and schema selection

The schemas are Draft 2020-12 and validate `{frontmatter, body}`: the parsed
frontmatter and the Markdown body. Dates are ISO date strings; Session `date`
takes `YYYY-MM-DD` or null. Custom frontmatter fields are allowed.

Each supported `type` has a schema in the vault's `reference/schemas/`
directory:

| `type` | Schema |
| --- | --- |
| `[[types/Content]]` | `content.schema.json` |
| `[[types/Clue]]` | `clue.schema.json` |
| `[[types/Note]]` | `note.schema.json` |
| `[[types/Session]]` | `session.schema.json` |
| `[[types/Player]]` | `player.schema.json` |
| `[[types/Transcript]]` | `transcript.schema.json` |
| `[[Reference]]` | `reference.schema.json` |
| `[[Type]]` | `type.schema.json` |
| `[[Status]]` | `status.schema.json` |

Enabled [extensions](extensions.md) add schemas to those selected by type. A
record must pass every schema that applies to it.

The schemas apply to typed records, not to unfinished templates. Their
references are local. The tests turn on URI and date format assertions.

## Limits

The body regexes check only the basic structure. Duplicate headings and
matching text in fenced code can satisfy the Content and Session heading
checks, and the Transcript check looks for only one heading and attributed
entry. The Clue schema requires a Sessions heading and one Base embed, but
cannot tell whether the Base exists or runs. Content's Active Clues and each
of a Session's preparation view sections also require exactly one Base embed;
the other sections hold free Markdown. Checking that links exist and target
the right kind of record, campaign and filename identity, chronology,
reciprocal relationships, consistent history and the structure of every
Transcript section and entry takes [vault-aware validation](validate.md).

## Tests

From the repository root, with the
[development environment](developing.md#setting-up) set up:

```sh
uv run python -m pytest tests/schemas -q
```

The tests cover the meta-schemas, offline references, parsed JSON fixtures,
committed Markdown records, and the identical copies of the schemas and Type
and Status records in both vaults. The PyYAML fixture loader supports the
tests; it is not the parser Armarium uses.
