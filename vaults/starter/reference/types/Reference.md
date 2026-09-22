Pages with `type: "[[Reference]]"` are structural, taxonomic, or index pages, such as campaign overviews and language catalogues.

## Schema

The [Reference schema](../schemas/reference.schema.json) validates parsed
`{frontmatter, body}` records.

Only explicitly typed pages use this schema. Require `type: "[[Reference]]"`;
no other keys or body headings are required. Custom fields and an empty body are
permitted. Untyped type pages, indexes and status definitions (`applies_to`) are
supporting documents and do not acquire this type or require a separate schema.
