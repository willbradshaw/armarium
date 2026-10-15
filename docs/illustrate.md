# Illustrating a record

```sh
armarium illustrate prompt "content/Lucky Ring.md" > prompt.txt
armarium illustrate generate "content/Lucky Ring.md" --prompt prompt.txt
armarium illustrate ingest "content/Lucky Ring.md" ".scratch/illustrate/Lucky Ring-2.png"
```

`armarium illustrate prompt RECORD` prints what an image model should be told
to paint a record's picture; see [Prompts](#prompts).

`armarium illustrate generate RECORD --prompt FILE` sends that prompt to an
image model and writes the candidates it paints to `.scratch/illustrate/`; see
[Painting](#painting).

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
WebP, such as a candidate `generate` painted. It is a path relative to the
current directory, and is never changed.

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

Black art would vanish on Obsidian's dark theme, so a new vault enables the CSS
snippet `.obsidian/snippets/armarium-opacity-art.css`, which shows the art in
`assets/art/ink/` inverted, as white, on a dark theme; printing and PDF export
keep it black. Give a black-opacity style `directory: assets/art/ink`, or add a
selector for its own folder to the snippet.

## Styles

A style says how one kind of art is made and stored. Each is a
[Reference](type.md#reference) record in `reference/styles/`, named for the
style, and a new vault has one, `Gear`. Its `references` is empty until the
vault has Gear art to show the style:

```markdown
---
type: "[[Reference]]"
illustrates: [Content/Gear]
directory: assets/art/gear
references: []
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
| `references` | links to images that show the style, or to records whose `image` does | `--reference` | none |
| `sample` | how many references to send with each candidate | `--sample` | all of them |

The body says what the style looks like. [`prompt`](#prompts) puts it at the
start of the prompt for any record illustrated in that style, and
[`generate`](#painting) sends its references with the prompt.

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

## Painting

```sh
armarium illustrate prompt "content/Lucky Ring.md" | armarium illustrate generate "content/Lucky Ring.md" --prompt -
```

`armarium illustrate generate RECORD --prompt FILE` sends the prompt in `FILE`,
or on standard input for `--prompt -`, to an image model, and writes the
candidates it paints to `.scratch/illustrate/` as `NAME-1.png`, `NAME-2.png` and
so on, `NAME` the record's. It prints each candidate's path; pass the one you
choose to `ingest`. Nothing in the vault changes until then: a new vault keeps
`.scratch/` out of Git, and validation skips it.

| Option | Sets | Default |
| --- | --- | --- |
| `--count N` | how many candidates to paint | 2 |
| `--model NAME` | the image model; see [Image models](#image-models) | `gpt-image-2.5-sunburst` |
| `--reference IMAGE` | an image to send to show the style; repeatable | none |
| `--sample N` | how many references to draw at random for each candidate | all of them |
| `--overwrite` | replace the record's earlier candidates | off |

A [style](#styles) replaces the defaults of `--reference` and `--sample` with its
`references` and `sample`. `RECORD`, `--vault` and `--style NAME` work as for
`ingest`.

### References

Each request carries the reference images, to show the model the style. A
reference to a record sends the image its `image` names; a record without an
image file in the vault is left out, with a warning, as is the record being
illustrated. Sent all at once, many references average out into one middling
style, so `sample` draws a few at random for each candidate instead, one request
per candidate, and the command reports each candidate's draw. If there are more
references per request than the model takes, the command stops and asks for
`--sample`.

### Ground

Art is painted on a transparent ground. For a style stored as
[black opacity](#black-opacity), it is painted on the ground the prompt
describes, such as white, and the references are sent laid on white.

### Image models

A provider is a service that runs image models. Armarium offers one provider
for now, OpenAI; others may be added later. `--model` chooses the model, and
with it the provider that offers it. A provider offers only models that can
paint on a transparent ground, so a model that cannot is refused.

#### OpenAI

| Model | Paints |
| --- | --- |
| `gpt-image-2.5-sunburst` | with more precision, more slowly; the default |
| `gpt-image-2.5-flare` | faster and more loosely |

A dated snapshot of either, such as `gpt-image-2.5-flare-2026-09-08`, is offered
too. Older models, such as `gpt-image-2`, are not.

- **Key:** read from `OPENAI_API_KEY`.
- **References:** at most 16 per request.
- **Pictures:** 1024 by 1024 pixels, at high quality, as PNG.

## With an agent

A new vault ships the `illustrate-record` [skill](agents.md), which walks a
coding agent through the stages for one record: it builds the prompt, proposes
a `visual` line where the record needs one, paints candidates once the GM
agrees, and takes in the one the GM chooses.
