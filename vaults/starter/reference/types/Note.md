---
type: "[[Type]]"
---
Records with `type: "[[types/Note]]"` are freeform working documents: GM
working notes, design notes, session prep, ideas and anything else that fits
no structured type. Nothing in a Note is established canon; move facts into
Content records once they are settled in play.

Shared notes live under `notes/`; campaign-specific notes live under
`campaigns/campaign_1/notes/` (or the corresponding campaign folder). Use
[[templates/Note]], name the file for its subject, and link the records the
note discusses so it can be found from them.

## Schema

A Note's frontmatter requires only `type`. Custom fields are allowed, and the
body is free Markdown with no required headings.

See the [Note schema](../schemas/note.schema.json).
