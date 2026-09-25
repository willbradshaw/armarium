---
type: "[[Type]]"
directories: { shared: reference/types }
---
# Type

A Type record defines a category of records and documents its metadata and body
conventions. Type definitions live in `reference/types/`.

## Fields

Every type definition declares `type: "[[Type]]"` and `directories`. The filename
supplies the type name; no duplicate name field is required. Custom metadata is
allowed, and the body is free Markdown with no required headings.

`directories` declares where records of the type live: `shared` is a path
relative to the vault root, `campaign` a path relative to each
`campaigns/campaign_N`. Declare one or both, as relative paths without a leading
`/` or `..` segments, for example `{ shared: content, campaign: content }`. A
record must sit in a directory its type declares or in a subfolder of it. A
directory declared inside another type's, such as Transcript's
`sessions/transcripts` inside Session's `sessions`, belongs to the type declaring
the longest match. Every declared directory must exist.

`Type.md` is itself a Type record, as is `Status.md`. A Type record does not need
to duplicate its JSON schema in frontmatter. Schema selection uses the lowercase
type name, for example `type.schema.json` for Type records. A custom type needs
only a Type record with `directories` and its `<type>.schema.json`.

See the [Type schema](../schemas/type.schema.json).
