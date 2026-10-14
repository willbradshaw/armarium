# Illustrating a record

```sh
armarium illustrate ingest "content/Lucky Ring.md" ~/Downloads/ring.png
```

`armarium illustrate ingest RECORD PICTURE` takes a picture into a
[vault](vault.md) as a record's image. It writes the picture into `assets/` as a
small WebP and sets the record's `image` field to its path, then validates the
record.

## Choosing the record

`RECORD` is the record's file path, as for
[`armarium trace`](trace.md#choosing-the-file): without `--vault`, absolute or
relative to the current directory; with `--vault VAULT`, relative to the vault
root, so a path printed by [`armarium find`](find.md) can be passed as it is.

`PICTURE` is the picture to take in, in any common format, such as PNG, JPEG or
WebP. It is a path relative to the current directory, and is never changed.

## What it writes

For `content/Lucky Ring.md`, the command writes `assets/art/Lucky Ring.webp` and
sets the record's field to match:

```yaml
image: assets/art/Lucky Ring.webp
```

It prints the image's path on standard output and reports its size on standard
error. `--output PATH` names another `.webp` file inside `assets/`, relative to
the vault root. Missing directories are created.

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
laid on white.
