---
type: "[[Type]]"
directories: { campaign: sessions/transcripts }
---
Transcript records contain cleaned, attributed speech from a session, grouped under
content headings. They live under the campaign's `sessions/transcripts/` directory
and link to their Session through the `session` field.

Create a Transcript with `armarium add transcript SESSION --body-file FILE`,
which follows the structure of [[templates/Transcript]] and names the file
`S-1-001 Transcript.md` for session `S-1-001`. Speaker labels can identify the GM, a character, or the table;
use `[Player?]` or `[?]` when attribution or hearing is uncertain.

## What a Transcript holds

A Transcript is a readable record of what was said at the table in one
Session. It is the place to look up who said what, and a Session's Events can
be written from it. It follows the conversation closely, so it is shorter than
the recording but is not a summary of it.

- **Kept:** what bears on the game. Decisions, the substance of dialogue, what
  the GM describes, dice results, abilities and spells used, loot and money,
  and signs of time passing such as a rest or nightfall.
- **Left out:** filler, false starts, repeated words and talk that is not about
  the game.
- **Table talk worth keeping**, such as a rules ruling or who is absent, is
  tagged `[Table]`. So is a recap of earlier Sessions, since it describes
  earlier play.

Sections follow the scenes in order, each titled for what happens in it.

## Speakers

Each utterance is tagged with who said it:

| Tag | Speaker |
| --- | --- |
| `[GM]` | the GM, narrating or ruling |
| `[GM] (as Name)` | the GM speaking as a character, named at the start of the text |
| `[Esme]` | a player, speaking as or for the character of that name |
| `[Esme?]` | probably that character's player |
| `[Player?]` | a player, but not known which |
| `[Table]` | talk outside the game |
| `[?]` | not known who |

When a group talks a decision through, it is often unclear who said each line.
`[Player?]` is the usual tag there.

## Names and doubt

Names are spelled as their records spell them, and linked where that helps a
reader find the record. A recording, and speech-to-text most of all, often
gets a setting's names wrong, so an unfamiliar name is usually an existing
record misheard.

A name that matches no record is written as it was heard and followed by
`(?)`. So is any word or number that could not be made out for certain.

Where part of the Session is missing, as when the recording drops out, a `[?]`
line says so: `- [?] (About two minutes lost here.)`.

The same mishearings come back from Session to Session. A campaign can keep
them in a Note named `Transcription reference`: a table of record names, each
with the misspellings seen so far, and any names that are easily confused with
each other.

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
