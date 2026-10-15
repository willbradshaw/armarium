# Illustrating a record

```sh
armarium illustrate prompt "content/Lucky Ring.md"
armarium illustrate ingest "content/Lucky Ring.md" ~/Downloads/ring.png
```

`armarium illustrate prompt RECORD` prints what an image model should be told
to paint a record's picture; see [Prompts](#prompts).

`armarium illustrate ingest RECORD PICTURE` takes a picture into a
[vault](vault.md) as a record's image. It writes the picture into `assets/` as a
small WebP and sets the record's `image` field to its path, then validates the
record.

A [style](#styles) says how each kind of art is painted, where it goes and how
it is stored.

## Choosing the record

`RECORD` is the record's file path, as for
[`armarium trace`](trace.md#choosing-the-file): without `--vault`, absolute or
relative to the current directory; with `--vault VAULT`, relative to the vault
root, so a path printed by [`armarium find`](find.md) can be passed as it is.

`PICTURE` is the picture to take in, in any common format, such as PNG, JPEG or
WebP. It is a path relative to the current directory, and is never changed.

## What it writes

The image is named after the record and goes in its style's `directory`, or in
`assets/art/` when no style applies. For the Gear record `content/Lucky Ring.md`
in a new vault, whose Gear style names `assets/art/gear`, the command writes
`assets/art/gear/Lucky Ring.webp` and sets the record's field to match:

```yaml
image: assets/art/gear/Lucky Ring.webp
```

It prints the image's path on standard output, and the style it used and the
image's size on standard error. `--directory DIR` names another folder inside
`assets/`, and `--output PATH` another `.webp` file there, each relative to the
vault root. Missing directories are created.

The command replaces no file unless given `--overwrite`: if the image file
exists it stops before writing anything. When the record's `image` already named
another file, that file is left in place, and the command says which it was.

Only the `image` line of the record's frontmatter changes; every other line is
kept as it was. If the field cannot be set that way, the command stops and
writes nothing, and the field must be set by hand. It does not add an image
embed to the record's body.

If the record then fails validation, the image and the changed field are kept
and the diagnostics are reported, and the command exits with status 1.

## Size

The picture is trimmed of plain borders, then shrunk until it fits the budget:

| Option | Limit | Default |
| --- | --- | --- |
| `--max-bytes N` | largest file, in bytes | 100000 |
| `--max-edge N` | largest long edge, in pixels | 1200 |

A [style](#styles) replaces these defaults, and those of `--directory` and
`--opacity`, with its own.

The long edge starts at `--max-edge` and shrinks by a tenth at a time until the
file fits, down to 350 pixels; at 450 pixels and below, lower WebP qualities are
tried before a smaller size. A picture is never enlarged. If it does not fit even at
the smallest size, the command stops and writes nothing.

Transparency is kept, and metadata such as camera details is dropped.

## Black opacity

`--opacity` is for monochrome drawings on white, such as ink art meant to sit on
a coloured page. It stores the drawing as black opacity on a transparent ground:
black throughout, and as opaque as the drawing is dark. White becomes clear, and
a grey wash lets the page show through. A picture with transparency is first
laid on white. A style with `opacity: true` stores its art this way;
`--no-opacity` stores a picture as it is.

## Styles

A style says how one kind of art is made and stored. Each is a
[Reference](type.md#reference) record in `reference/styles/`, named for the
style, and a new vault has one, `Gear`:

```markdown
---
type: "[[Reference]]"
illustrates: [Content/Gear]
directory: assets/art/gear
---
A single item of equipment, shown whole and on its own, as a plate in an
illustrated catalogue of adventuring gear. ...
```

Every field is optional, and each but `illustrates` has an option that
overrides it:

| Field | Holds | Option | Default |
| --- | --- | --- | --- |
| `illustrates` | the record types the style applies to, each a type or `Type/Subtype` | | none |
| `directory` | the folder inside `assets/` that its art goes in | `--directory` | `assets/art` |
| `opacity` | `true` to store its art as [black opacity](#black-opacity) | `--opacity` | `false` |
| `max_bytes` | the largest art file, in bytes | `--max-bytes` | 100000 |
| `max_edge` | the largest long edge, in pixels | `--max-edge` | 1200 |

The body says what the style looks like, and opens every [prompt](#prompts)
in the style.

`--style NAME` uses the style in `reference/styles/NAME.md`. Without it, the
command uses the style whose `illustrates` names the record's type, or its type
and subtype, such as `Content/Gear`; if several do, it stops and asks for
`--style`, and if none does, the defaults above apply.

[Validation](validate.md) checks each style's fields, and holds every file in
its `directory` and the folders inside it to its budget: each must be a WebP or
PNG image within `max_bytes` and `max_edge`. A style that cannot be read stops
the command until it is fixed.

## Prompts

`armarium illustrate prompt RECORD` prints the prompt for a record's picture. The
prompt is, in order:

1. a preamble, if any: the text of the `--preamble FILE`, or else the body of
   the record's style;
2. the record's name, as `<subject>NAME</subject>`;
3. the record's `> [!rules]` callout, if any, as `<rules>` … `</rules>`;
4. the record's `visual` field, if any, as `<visual>` … `</visual>`.

The rules text loses its quote markers, its links become their text and its
bold and italic markers are dropped.

`visual` is art direction: what the picture should show and how, when the rules
text alone would not get it right. It outranks the rules text. Any Content
record may set it:

```yaml
visual: A coil of rope on a brass reel, its hook worn bright.
```

`--visual TEXT` uses that text in place of the record's field, without changing
the record.

`RECORD` and `--vault` work as for `ingest`, and `--style NAME` chooses the
style as it does there. `--preamble FILE` is a UTF-8 text file, relative to the
current directory, that opens the prompt in place of a style's text; it cannot
be combined with `--style`. Without either, and with no style for the record's
type, the prompt opens with the record's name.
