# Printing handouts

```sh
armarium handout "content/Lucky Ring.md" "content/Rope of Climbing.md" -o loot.pdf
armarium handout "content/Harbourmaster's Letter.md" --layout Letter -o letter.pdf
```

`armarium handout RECORD... -o FILE` prints records as player handouts: each on
a page of its own, in the order given, in one PDF. A page holds the record's
name, the text of one of its callouts and its picture. The command prints the
PDF's path and changes no record.

A [layout](#layouts) chooses the callout, and sets the page, the font and how
much of the page the picture takes. Without one, a page prints the
`> [!rules]` callout, as for Gear.

## Choosing the records

Each `RECORD` is a record's file path, as for
[`armarium trace`](trace.md#choosing-the-file): without `--vault`, absolute or
relative to the current directory; with `--vault VAULT`, relative to the vault
root. Every record must be in the same vault.

A record prints only if it has a callout of its layout's type with text in it;
the command stops on a record without one.

`-o FILE` is the PDF to write, relative to the current directory. Missing
folders are created. The command replaces no file unless given `--overwrite`.

## What to print

The rules callout that opens Gear prints as an item card. Anything else the
players are handed, such as a letter, a map's legend or a page of scripture,
goes in a `> [!handout]` callout in its [Content](type.md#content) record,
before Notes, worded exactly as the players read it:

```markdown
> [!handout]
> Captain,
>
> The *Tern* sails at dawn. Bring the ledger, and come alone.
>
> — H.

## Notes
- The harbourmaster's summons, left at the inn for [[Captain Vey]].
```

A layout whose `callout` is `handout` prints it; see [Layouts](#layouts).

## What a page holds

- **The name**, the record's filename, at the top, unless the layout's `title`
  is `false`.
- **The text**, from the record's first callout of the layout's type.
  Paragraphs, lists, tables, bold and italic print as written. A link prints as
  its text: its display text, or else the name of the file it links to. An
  embedded file, such as `![[Ring.webp|500]]`, HTML and horizontal rules are
  left out.
- **The picture** the record's `image` field names, below the text and centred.
  Transparency is kept, so art stored as [black opacity](illustrate.md#black-opacity)
  prints as ink on the paper. Without an `image`, the page has no picture and
  the text has all of the space.

The text takes the largest font size, between the layout's smallest and
largest and to the nearest half point, at which it fits its share of the page.
The picture takes the room left, so short text leaves it more than its share.
Text too long to fit even at the smallest size shrinks to fit, the picture is
left out if no room remains, and the command warns of both.

The command logs each page's layout, text size and picture height.

## Layouts

A layout says how one kind of record prints. Each is a
[Reference](type.md#reference) record of subtype `Layout` in
`reference/layouts/`, named for the layout. `--layout NAME` prints every record
in `reference/layouts/NAME.md`. Without it, each record prints in the layout
whose `prints` names its type, or its type and subtype; if several do, the
command stops and asks for `--layout`, and if none does, the defaults below
apply.

An item card, with the record's name, a mark for items that need attunement,
and links underlined:

```markdown
---
type: "[[Reference]]"
subtype: Layout
prints: [Content/Gear]
font: assets/fonts/Lora-Regular.ttf
title_size: 48
min_text_size: 16
max_text_size: 36
mark: { field: attunement, text: A }
underline_links: true
---
```

A letter, in a handwriting font, with no name at the top:

```markdown
---
type: "[[Reference]]"
subtype: Layout
callout: handout
title: false
font: assets/fonts/HomemadeApple-Regular.ttf
margin: 1.5in
max_text_size: 18
line_spacing: 1.8
---
```

Every field is optional:

| Field | Holds | Default |
| --- | --- | --- |
| `prints` | the record types the layout applies to, each a type or `Type/Subtype` | none |
| `callout` | the type of the callout whose text prints, such as `rules` or `handout` | `rules` |
| `title` | `false` to leave the record's name off the page | `true` |
| `page` | the paper size: `letter` or `a4` | `letter` |
| `margin` | the margin on every side, as a length such as `0.7in`, `18mm`, `2cm` or `50pt` | `0.7in` |
| `font` | a standard PDF font, or the path of a TrueType font file | `Times-Roman` |
| `title_size` | the name's font size, in points | 36 |
| `min_text_size` | the text's smallest font size, in points | 12 |
| `max_text_size` | the text's largest font size, in points | 24 |
| `line_spacing` | the distance between lines, as a multiple of the font size | 1.2 |
| `image_share` | the share of the space below the name that the text leaves to the picture, between 0 and 1 | 0.5 |
| `mark` | a `field` and `text`: the text prints beside the name, in the page's top right corner, when the record's field is `true` | none |
| `underline_links` | `true` to underline link text | `false` |
| `lowercase_links` | `true` to print link text in lowercase | `false` |

The mark sits beside the name, so a layout without a title prints no mark. The
body is free Markdown, such as a note on what the layout is for.

The standard fonts are the Times, Helvetica and Courier families, such as
`Times-Roman` or `Helvetica`. A font file's path is absolute or relative to the
vault root; it must hold TrueType outlines, in a `.ttf` file or the first font
of a `.ttc` collection. A font file is one face, so bold and italic text in it
is underlined instead.

Every record in one PDF must share a page size and margin; print records whose
layouts differ in either to separate files.

The vault's Reference schema checks each layout's fields. A layout that cannot
be read or fails the schema stops the command until it is fixed.
