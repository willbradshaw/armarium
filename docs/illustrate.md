# Illustrating a record

```sh
armarium illustrate ingest "content/Lucky Ring.md" ~/Downloads/ring.png
```

`armarium illustrate ingest RECORD PICTURE` takes a picture into a
[vault](vault.md) as a record's image. It writes the picture into `assets/` as a
small WebP and sets the record's `image` field to its path, then validates the
record. A [style](#styles) can say where each kind of art goes and how it is
stored.

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
| `--max-bytes N` | largest file, in bytes | the style's `max_bytes`, or 100000 |
| `--max-edge N` | largest long edge, in pixels | the style's `max_edge`, or 1200 |

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

The body says what the style looks like, for an image model to paint from. The
command does not paint, so the body does not change what it writes.

`--style NAME` uses the style in `reference/styles/NAME.md`. Without it, the
command uses the style whose `illustrates` names the record's type, or its type
and subtype, such as `Content/Gear`; if several do, it stops and asks for
`--style`, and if none does, the defaults above apply.

[Validation](validate.md) checks each style's fields, and holds every file in
its `directory` and the folders inside it to its budget: each must be a WebP or
PNG image within `max_bytes` and `max_edge`. A style that cannot be read stops
the command until it is fixed.
