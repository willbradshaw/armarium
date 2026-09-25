---
type: "[[Type]]"
---
Transcript records contain cleaned, attributed speech from a session, grouped under
content headings. They live under the campaign's `sessions/transcripts/` directory
and link to their Session through the `session` field.

Use [[templates/Transcript]]. Name the file `S-1-001 Transcript.md` for
session `S-1-001`. Speaker labels can identify the GM, a character, or the table;
use `[Player?]` or `[?]` when attribution or hearing is uncertain.

## Schema

A Transcript’s frontmatter requires `type` and a Session link in `session`. The
body needs at least one level-two content heading followed by a bullet item of
attributed speech, such as `- [GM] Speech.` Uncertain labels such as `[?]` are
allowed. The schema checks this minimum structure; the validator holds the
whole body to the grammar below.

See the [Transcript schema](../schemas/transcript.schema.json).

## Body grammar

After the frontmatter, the body is a run of level-two sections with titles
(`## The notice`); no other heading level, and nothing before the first
heading. Each section holds exactly one bullet list and nothing else. Each item
is one utterance: a single paragraph opening with a speaker tag, a space and
text, such as `[GM]`, `[Table]`, `[Esme]`, `[Darian — Martin]`, `[Player?]` or
`[?]`. A long utterance may wrap onto further lines of its item.

After the tag, square brackets may appear only inside double-bracketed
wikilinks. An item whose leading `- ` is missing is read as a continuation of
the previous utterance; its tag is what lets the validator report it.

```markdown
## The notice

- [GM] An officer of the countinghouse posts a sale notice.
- [Esme] We dispute that charge.
```
