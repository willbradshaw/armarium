---
type: "[[Type]]"
---
# Status

A Status record defines a status that another type of record can use. Status
definitions live in `reference/statuses/`.

## Fields

Every status definition requires:

- `type: "[[Status]]"`.
- `applies_to`: one canonical wikilink to a type definition, for example
  `"[[types/Clue]]"`. Display aliases and heading/block anchors are not allowed.

The filename supplies the status name. Custom metadata is allowed, and the body
is free Markdown describing the status. Existing Clue statuses retain their
meanings and their `applies_to` links.

The schema checks link syntax; checking that it resolves to a Type record requires
vault-aware validation. `Status.md` defines this type and therefore itself
declares `type: "[[Type]]"`.

See the [Status schema](../schemas/status.schema.json).
