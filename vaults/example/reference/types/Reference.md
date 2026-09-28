---
type: "[[Type]]"
directories: { shared: reference, campaign: reference }
---
Records with `type: "[[Reference]]"` are structural, taxonomic, or index records, such as campaign overviews and language catalogues.

Use [[templates/Campaign]] for a campaign overview and [[templates/Clues]] for
its clue index. Copy them to `reference/Campaign.md` and
`reference/indexes/Clues.md` within the campaign directory. In the clue index,
replace campaign 1 in the link, directory path and clue ID example with the
intended campaign number.

## Schema

A typed Reference record’s frontmatter requires only `type: "[[Reference]]"`.
Custom fields are allowed, and the body may be empty or contain free Markdown.
Type definitions declare `type: "[[Type]]"`; status definitions declare
`type: "[[Status]]"`. They have their own schemas. An index submitted as a
record should declare `type: "[[Reference]]"`.

See the [Reference schema](../schemas/reference.schema.json).
