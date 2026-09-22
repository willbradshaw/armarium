---
type: "[[Type]]"
---
# Type

A Type record defines a category of records and documents its metadata and body
conventions. Type definitions live in `reference/types/`.

## Fields

Every type definition declares `type: "[[Type]]"`. The filename supplies the type
name; no duplicate name field is required. Custom metadata is allowed, and the
body is free Markdown with no required headings.

`Type.md` is itself a Type record, as is `Status.md`. A Type record does not need
to duplicate its JSON schema in frontmatter. Schema selection uses the lowercase
type name, for example `type.schema.json` for Type records.

See the [Type schema](../schemas/type.schema.json).
