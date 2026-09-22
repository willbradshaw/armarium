---
type: "[[Type]]"
---
Transcript pages contain cleaned, attributed speech from a session, grouped under
content headings. They live under the campaign's `sessions/transcripts/` directory
and link to their Session through the `session` field.

Use [[templates/Transcript]]. Name the file `S-1-001 Transcript.md` for
session `S-1-001`. Speaker labels can identify the GM, a character, or the table;
use `[Player?]` or `[?]` when attribution or hearing is uncertain.

## Schema

A Transcript’s frontmatter requires `type` and a Session link in `session`. The
body needs at least one level-two content heading followed by attributed speech,
such as `[GM] Speech.` Uncertain labels such as `[?]` are allowed. The schema
checks this minimum structure, not attribution throughout the body.

See the [Transcript schema](../schemas/transcript.schema.json).
