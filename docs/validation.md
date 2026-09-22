# Read-only validation

Install with `python -m pip install .`, then run `armarium validate PATH` from
any directory. Supply `--vault PATH` when vault context cannot be inferred.
Single-file checks include YAML, available schemas, canonical link resolution,
placement, identity, target kinds and campaign agreement. Directory traversal
is added in the next stage. It never writes to the target.

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

Full and shortest-unique suffix links, optional `.md`, display aliases, Unicode,
assets and escaped table pipes are supported. YAML aliases are display names, not
canonical identities. File targets of anchors are checked; actual heading/block
existence is deferred. Illustrative fences are ignored; Dataview blocks and inline
expressions remain link-bearing. Templates can be link targets but not records.

Malformed wikilink delimiters and empty targets produce `link.syntax` errors
with a metadata field or body line. Scanning continues to later links. The shared
`parse_wikilink()` utility raises `ValueError` for malformed input; file checks
convert it into a diagnostic. Illustrative code fences remain excluded.
