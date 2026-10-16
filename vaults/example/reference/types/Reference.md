---
type: "[[Type]]"
directories: { shared: reference, campaign: reference }
subtype_directories: { Style: styles }
---
Records with `type: "[[Reference]]"` are structural, taxonomic, or index records, such as campaign overviews and language catalogues.

## Schema

A typed Reference record’s frontmatter requires only `type: "[[Reference]]"`.
Custom fields are allowed, and the body may be empty or contain free Markdown.
An optional `subtype` marks a record that a command reads: `Style`, an
illustration style, which sits in `styles/` and whose fields the schema
checks.
Type definitions declare `type: "[[Type]]"`; status definitions declare
`type: "[[Status]]"`. They have their own schemas. An index submitted as a
record should declare `type: "[[Reference]]"`.

See the [Reference schema](../schemas/reference.schema.json).
