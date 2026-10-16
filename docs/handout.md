# Handouts

A handout prints the text of one of a record's callouts. The rules callout that
opens Gear prints as an item card. Any Content may also hold a `> [!handout]`
callout before Notes: the words the players are given on a handout of it, such
as a letter's text, exactly as they read them.

## Layouts

A layout says how one kind of record prints as a player handout. Each is a
[Reference](type.md#reference) record of subtype `Layout` in
`reference/layouts/`, named for the layout.

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

The vault's Reference schema checks each layout's fields.
