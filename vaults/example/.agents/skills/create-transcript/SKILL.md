---
name: create-transcript
description: Turns a session recording or raw speech-to-text into a cleaned, speaker-tagged Transcript record in this Armarium vault. Writes only the Transcript and the campaign's Transcription reference Note.
---

# Create a Transcript

This procedure turns what was recorded at the table into the Transcript record
of one Session. It does not write the Session's Events or update any other
record.

You need two things:

- the Session the recording belongs to, which must already exist;
- the source: a recording, or a text file of raw speech-to-text.

Run the commands from the vault root, or add `--vault PATH`. Keep working files
in `.scratch/`, which Git ignores. Never move, edit or delete the source.

## 1. Get the raw text

```sh
armarium find "S-N-NNN"
armarium transcribe "SOURCE" --output ".scratch/S-N-NNN.txt"
```

`find` gives the Session's path. If a Transcript for it already exists, stop
and ask.

[`armarium transcribe`](https://github.com/willbradshaw/armarium/blob/main/docs/transcribe.md)
takes a recording or a `.txt` file and prints the path of the text to work
from. In that text, a line starting `[ASR loop:` marks a run of repeated lines
that it collapsed.

If the command fails, report its message and stop. Do not install software or
choose another speech-to-text tool unasked.

## 2. Read the Type record and the Session

Read `reference/types/Transcript.md`. It says what a Transcript keeps and
leaves out, how speakers are tagged and how doubt is marked. It is the
authority for this vault.

Read the Session record. Its preparation names the characters, places and
Clues likely to be spoken of. It says nothing about what happened.

## 3. List the names

Build a list of the names to expect, each with its record's spelling:

- the campaign's Players and the characters they play, from the Player records
  in `campaigns/campaign_N/reference/players/`;
- the records the Session links to:

  ```sh
  armarium trace "campaigns/campaign_N/sessions/S-N-NNN.md" --outbound
  ```

- the misspellings in the campaign's `Transcription reference` Note, if
  `armarium find "Transcription reference" --campaign N` finds one.

Then look for the names the list misses. Count the capitalised words in the raw
text:

```sh
grep -oE "[A-Z][A-Za-z'-]{2,}" ".scratch/S-N-NNN.txt" | sort | uniq -c | sort -rn
```

For each word that is neither on the list nor ordinary English, read the lines
it appears in, then search for the record it could be: `armarium find` for an
exact name or alias, and a search of record names and aliases for near
spellings. Check the rare words as well as the frequent ones.

Add each confident match to the list. Keep the rest as a list of unresolved
names: they are marked in the Transcript and asked about in step 6, not
guessed.

## 4. Clean the text

Work through the raw text in order, in chunks of about 300 lines, applying the
Type record and the list of names. Start each chunk knowing how the previous
one ended. If you can hand chunks to sub-agents, give each one the Type record,
the list of names and the end of the previous chunk.

Add nothing the raw text does not say. Where you cannot tell who spoke or what
was said, use the uncertain tags and `(?)`; do not guess.

At each `[ASR loop:` marker, part of the Session is missing. Write the line the
Type record gives for that, and do not use the repeated text as speech.

Then read the whole result once for what a single chunk cannot show: a name
resolved two ways, or an action tagged to a character who could not have done
it. Do not make a second pass to attribute the lines left uncertain.

Divide the result into titled sections, as the Type record describes, and save
it without frontmatter as `.scratch/S-N-NNN Transcript.md`.

## 5. Create the record

```sh
armarium add transcript "S-N-NNN" --body-file ".scratch/S-N-NNN Transcript.md"
```

The command names and files the record and checks its body. If it reports
errors, fix the body file and run it again. Never write the record by hand.

Each link you wrote must name a record. Where validation reports
`link.missing`, write the name as plain text followed by `(?)` and add it to
the unresolved names. Do not create records from a Transcript.

## 6. Ask the GM

Show the GM, in one list:

- each unresolved name, with a line it appears in;
- each significant action whose speaker is uncertain;
- each stretch of lost speech, with what surrounds it;
- anything else that the record leaves in doubt.

Then stop and wait. Apply each answer to the Transcript, and to nothing else.
Answers are not approval: after applying them, show what changed and wait
again, until the GM says the Transcript is done.

## 7. Record what you learned

For each misspelling the GM confirmed or you matched with confidence, add it to
the campaign's `Transcription reference` Note, as the Type record describes. If
the campaign has none, create it:

```sh
armarium add note "Transcription reference" --campaign N
```

## 8. Validate and report

```sh
armarium validate .
```

Fix every error your change introduced. If the vault had errors before you
started, report them; do not fix them unasked.

Then say where the Transcript is, what you added to the Transcription
reference, which questions are still open, and where the source and working
files are. Leave them in place.
