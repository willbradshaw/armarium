---
name: illustrate-record
description: Paints a picture for one record in this Armarium vault with an image model and sets it as the record's image, with the GM choosing the picture. Edits only that record.
---

# Illustrate a record

This procedure gives one record a picture: it builds the prompt, has an image
model paint candidates, and takes in the one the GM chooses. It edits no other
record.

You need the path of the record;
[`armarium find`](https://github.com/willbradshaw/armarium/blob/main/docs/find.md)
gives the path for a name. Run the commands from the vault root, or add
`--vault PATH`. [Illustrating a record](https://github.com/willbradshaw/armarium/blob/main/docs/illustrate.md)
describes every command and option used here.

If `.agents/skills/illustrate-record/addenda/` exists, read every file in it
before you start. Each adds to this procedure, for an extension the vault has
enabled or for the vault itself, and applies as if it were written here. Where
an addendum and this file disagree, follow the addendum; where two addenda
disagree, follow `vault.md`, the vault's own.

## 1. Read the record and its style

Read the whole record. If its `image` already names a picture, tell the GM and
ask whether to replace it; stop if not.

```sh
armarium illustrate prompt "PATH" > ".scratch/RECORD.prompt.txt"
```

`RECORD` is the record's filename without `.md`. If the command stops because
several styles apply, ask the GM which to use and pass `--style NAME` here and
in step 3. Read the style in `reference/styles/` that applies, and the prompt.

## 2. Settle the art direction

The prompt describes the subject through the record's rules text and its
`visual` field. If they do not say what the picture should show, such as its
form, material or colours, propose a `visual` line to the GM: one or two
sentences, drawn only from what the record states. Set it only when the GM
agrees, then build the prompt again.

## 3. Paint candidates

The image model charges for every candidate. Tell the GM how many you will
paint, two unless they say otherwise, and paint only when they agree.

```sh
armarium illustrate generate "PATH" --prompt ".scratch/RECORD.prompt.txt"
```

Add `--count N` for another number, and `--overwrite` to replace candidates
from an earlier run. The command prints each candidate's path, and warns of any
style reference it left out; pass those warnings on.

## 4. Have the GM choose

Give the GM the candidates' paths, and say briefly how each differs. The GM
chooses; do not choose for them. If none will do, ask what to change, adjust
`visual` with their agreement, and return to step 3.

## 5. Take the picture in

```sh
armarium illustrate ingest "PATH" "CANDIDATE"
```

Add `--overwrite` only if the GM agreed in step 1 to replace an existing
picture file. The command writes the image within the style's size budget, sets
the record's `image` and validates the record. Fix every error your change
introduced, by changing this record only.

## 6. Report

Say which candidate the GM chose, where the image was written, and any `visual`
line you set. Leave the other candidates in `.scratch/illustrate/`; the GM may
delete them.
