---
type: "[[Type]]"
directories: { shared: notes, campaign: notes }
---
Records with `type: "[[types/Note]]"` are freeform documents that do not fit
the rest of the type hierarchy, such as GM working notes, design notes, session
prep and ideas.

Brainstorming Notes contain proposals, not established setting facts. When an
idea is adopted, incorporate it into the relevant Content record or Session
preparation.

Shared notes live under `notes/`; campaign-specific notes live under
`campaigns/campaign_1/notes/` (or the corresponding campaign folder). Create a
Note with `armarium add note NAME`, adding `--campaign N` for a campaign-specific
one; it starts from [[templates/Note]].

## Schema

A Note's frontmatter requires only `type`. Custom fields are allowed, and the
body is free Markdown with no required headings.

See the [Note schema](../schemas/note.schema.json).
