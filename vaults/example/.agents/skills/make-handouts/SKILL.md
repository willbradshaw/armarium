---
name: make-handouts
description: Prints records in this Armarium vault as player handouts in a PDF, such as a Session's loot or a letter, after checking each has the text and picture to print. Edits a record only to add text or a picture the GM supplies.
---

# Make handouts

This procedure prints records as handouts for the players: each on a page of
its own, in one PDF. It checks that every record has something to print, fills
any gap from the GM, and prints with `armarium handout`.

Run the commands from the vault root, or add `--vault PATH`.
[Handouts](https://github.com/willbradshaw/armarium/blob/main/docs/handout.md)
describes the command, layouts and what a page holds.

If `.agents/skills/make-handouts/addenda/` exists, read every file in it
before you start. Each adds to this procedure, for an extension the vault has
enabled or for the vault itself, and applies as if it were written here. Where
an addendum and this file disagree, follow the addendum; where two addenda
disagree, follow `vault.md`, the vault's own.

## 1. List what to print

Take the list from the GM, or from a Session's Preparation when the GM names
one, such as its rewards. Find each record's path with
[`armarium find`](https://github.com/willbradshaw/armarium/blob/main/docs/find.md).
Where something to hand out has no record, ask the GM whether to create one;
leave it out if not.

Show the GM the list, in print order, and the layout each record will print in:
the one in `reference/layouts/` whose `prints` names its type, or its type and
subtype, or the defaults. Ask for any change.

## 2. Check each record

Read each record whole. A page prints the record's first callout of its
layout's type: `> [!rules]` unless the layout names another.

- **No text.** Ask the GM for the words, and write them into the callout
  exactly as given. Gear's rules text goes in its `> [!rules]` callout;
  anything else the players read, such as a letter, goes in a `> [!handout]`
  callout before Notes. Never write the text yourself, from memory or
  otherwise, and never leave a placeholder.
- **No picture.** The page prints without one. Ask the GM whether to add one
  first: with the `illustrate-record` skill, or from a picture file the GM
  gives you, taken in as that skill's step 5 describes.

Validate each record you changed, and fix every error your change introduced.

## 3. Print

```sh
armarium handout "PATH" "PATH" ... -o ".scratch/handouts/NAME.pdf"
```

Print to the file the GM names, or else to `.scratch/handouts/`. Add
`--layout NAME` where the GM chose a layout other than the record's own, such
as a letter's, printing those records in a PDF of their own. Records whose
layouts differ in page size or margin also print to separate files.

The command logs each page's text size and picture height, and warns when text
shrinks below the layout's smallest size or the picture is left out. Pass
those warnings on. To fix one for this print only, use a flag, such as
`--image-share 0.4` to give the text more room; to fix it for every print,
propose the change to the layout, and make it only when the GM agrees.

## 4. Report

Give the PDF's path and its pages in order, with any warnings, and list the
records you changed and how.
