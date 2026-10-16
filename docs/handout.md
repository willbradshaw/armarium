# Handouts

## Layouts

A layout says how one kind of record prints as a player handout. Each is a
[Reference](type.md#reference) record of subtype `Layout` in
`reference/layouts/`, named for the layout.

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

Every field is optional:

| Field | Holds | Default |
| --- | --- | --- |
| `prints` | the record types the layout applies to, each a type or `Type/Subtype` | none |
| `page` | the paper size: `letter` or `a4` | `letter` |
| `margin` | the margin on every side, as a length such as `0.7in`, `18mm`, `2cm` or `50pt` | `0.7in` |
| `font` | a standard PDF font, or the path of a TrueType font file | `Times-Roman` |
| `title_size` | the name's font size, in points | 36 |
| `min_text_size` | the rules text's smallest font size, in points | 12 |
| `max_text_size` | the rules text's largest font size, in points | 24 |
| `line_spacing` | the distance between lines, as a multiple of the font size | 1.2 |
| `image_share` | the share of the space below the name that the text leaves to the picture, between 0 and 1 | 0.5 |
| `mark` | a `field` and `text`: the text prints in the page's top right corner when the record's field is `true` | none |
| `underline_links` | `true` to underline link text | `false` |
| `lowercase_links` | `true` to print link text in lowercase | `false` |

The body is free Markdown, such as a note on what the layout is for.

The standard fonts are the Times, Helvetica and Courier families, such as
`Times-Roman` or `Helvetica`. A font file's path is absolute or relative to the
vault root; it must hold TrueType outlines, in a `.ttf` file or the first font
of a `.ttc` collection. A font file is one face, so bold and italic text in it
is underlined instead.

The vault's Reference schema checks each layout's fields.
