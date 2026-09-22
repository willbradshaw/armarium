Transcript pages contain cleaned, attributed speech from a session, grouped under
content headings. They live under the campaign's `sessions/transcripts/` directory
and link to their Session through the `session` field.

Use [[templates/Transcript]]. Name the file `S-1-001 Transcript.md` for
session `S-1-001`. Speaker labels can identify the GM, a character, or the table;
use `[Player?]` or `[?]` when attribution or hearing is uncertain.

## Schema

The [Transcript schema](../schemas/transcript.schema.json) uses the shared
[parsed-note contract and standalone checks](../schemas/README.md).

Require `type` and a non-null Session wikilink in `session`. A completed
Transcript needs at least one level-two content heading followed by an attributed
speech line such as `[GM] Speech.` Additional sections and source notes are free
Markdown. An empty Transcript is still an unfinished form; uncertain speaker
labels such as `[?]` are permitted.
