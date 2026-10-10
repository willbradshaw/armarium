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

A Transcript is what was said at the table in one Session, cleaned enough to
read and search. A Session's Events are written from it, so it condenses the
speech and adds nothing: it does not summarise, interpret or tidy the story.

- **Kept:** what bears on the game. Decisions, the substance of dialogue, what
  the GM describes, dice results, abilities and spells used, loot and money,
  and signs of time passing such as a rest or nightfall.
- **Left out:** filler, false starts, repeated words and talk that is not about
  the game.
- **Table talk worth keeping**, such as a rules ruling or who is absent, is
  tagged `[Table]`. So is a recap of earlier Sessions: it describes earlier
  play, not this Session's.

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

An uncertain tag is better than a guess. A group deciding together often
cannot be attributed line by line, and `[Player?]` is the honest record of it.

## Names and doubt

Speech-to-text misspells the names of a setting. Write each name as its record
spells it, and link it where that helps a reader find the record. A name that
matches no record is kept as it was heard and followed by `(?)`. So is any word
or number the hearing leaves in doubt. Most unfamiliar names in raw text are
existing records misheard, so a name is new only once the vault has been
searched for it.

Where speech is lost, as when the recording drops out or speech-to-text
repeats one line over the audio, a `[?]` utterance says what is missing, such
as `- [?] (About two minutes lost here.)`. Nothing is invented to fill the gap,
and the text of a repeated run is not treated as speech.

The same mishearings recur from Session to Session. A campaign can keep them in
a Note named `Transcription reference`: a table of record names, each with the
misspellings seen so far, and any pair of names that is easily confused. It
lists only what has been confirmed, and grows with each Transcript.

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
