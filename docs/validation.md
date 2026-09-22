# Read-only validation

Install with `python -m pip install .`, then run `armarium validate PATH` from
any directory. Supply `--vault PATH` when vault context cannot be inferred.
Stage 1 checks one Markdown file's YAML and available schema; it does not resolve
links or traverse directories yet. It never writes to the target.

Exit codes: 0 means no errors, 1 means validation errors, 2 means invalid invocation.
Warnings do not fail; unsupported schema types explicitly report partial coverage.
Templates are reported as skipped forms, never completed records. Untyped reference
pages do not require frontmatter. Diagnostics include relative paths, stable rule
IDs and fields or lines where available.

Schemas come only from the selected vault's `reference/schemas/`. A canonical
`[[types/Content]]` type maps to `content.schema.json`; other types follow the same
lowercase mapping. Draft 2020-12, local references and URI format assertions are
supported; remote retrieval is forbidden. Input is `{frontmatter, body}`. YAML dates
and timestamps become ISO strings; duplicate keys, cycles, non-string mapping keys
and non-JSON values are errors. The currently shipped schema covers Content.
Additional schemas from #22 plug into this loader without a separate runtime.
View implementations from #25 must not become literal query validation rules.
