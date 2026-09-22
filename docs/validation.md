# Read-only validation

Install with `python -m pip install .`, then run `armarium validate PATH` from
any directory. Supply `--vault PATH` when vault context cannot be inferred.
Single-file checks include YAML, available schemas, canonical link resolution,
placement, identity, target kinds and campaign agreement. Directory targets check
Markdown descendants with whole-vault context. Validation never writes to the target.

Scans continue after malformed files and sort diagnostics by relative location/rule.
Counts distinguish checked records, skipped forms/untyped pages and unsupported
schema types (a subset of checked). Untyped pages still receive link checks.
Hidden/configuration/scratch folders, caches, node_modules and symlinks are excluded;
assets and `.base` files are indexed as targets but not parsed as records.

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

A vault-root scan additionally requires shared reference infrastructure and at
least one numeric `campaign_N` folder with the documented content/clues/sessions/
reference layout. Additional user folders are allowed. The empty starter is valid;
forms need not be filled. `.git` alone never identifies a vault. CI discovers every
direct child of `vaults/` and validates it independently with explicit context.

Content Appearances use `- [[Session]]: description`, optionally grouped under
`### campaign_N`. Checks reconcile each campaign block's first/last Sessions with
actual recorded bullets, chronological order, duplicates and campaign agreement.
Empty histories are valid. Clue subjects must equal canonical Content targets in
`text`; display aliases do not change identity. Clue first/last Sessions track
preparation/introduction, so they are not reconciled with Content appearances.
Preparation-only and abandoned Clues remain valid. Mentions and PC attendance never
create appearances. The advisory Session review report remains separate (#16).


The [source coverage audit](validation-audit.md) records each source rule, its
implementation or exclusion, and remaining gaps. Comprehensive schemas for other
types remain in [#22](https://github.com/willbradshaw/armarium/issues/22); anchor
existence in [#37](https://github.com/willbradshaw/armarium/issues/37); Transcript
attribution and Clue view/text/lifecycle decisions in
[#36](https://github.com/willbradshaw/armarium/issues/36). Non-Content records receive
template-key and selected structural checks alongside context, with partial schema
coverage reported explicitly. Session/Clue/Transcript identity, canonical ledgers,
replacement and Location cycles, campaign isolation and table link escaping are
checked without imposing game-system or prose rules.
