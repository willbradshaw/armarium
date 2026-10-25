# Adding to a vault

`armarium add` creates [campaigns](#adding-a-campaign) and
[records](#adding-a-record) in an existing [vault](vault.md) from the vault's
own templates, then [validates the result](#templates-and-validation). For
example:

```sh
armarium add campaign --vault ../my-vault
armarium add content "Port Briselle" --subtype Location --vault ../my-vault
armarium add session --campaign 1 --vault ../my-vault
```

For a new vault, start with [`armarium init`](init.md).

## Shared behavior

Every `add` command follows the same rules for
[choosing a vault](#choosing-a-vault-and-destination),
[choosing a campaign](#choosing-a-campaign) and
[templates and validation](#templates-and-validation).

### Choosing a vault and destination

`--vault PATH` names the vault's root directory, as an absolute path or one
relative to the current directory. Without it, the command finds the vault
that contains the current directory.

A new record goes in the vault's
[declared directory](vault.md#where-records-live) for its type and
[campaign](#choosing-a-campaign), not in the current directory. The commands
never overwrite an existing record or campaign, and refuse a record whose
[name](record.md#names) another record already holds.

### Choosing a campaign

Inside a [campaign directory](campaign.md#directory), at any depth, `add`
puts new records in that campaign. `--campaign N` chooses another existing
campaign. With `--vault` naming a different vault, the current campaign does
not carry over.

Outside a campaign directory, [Content](#content) and [Notes](#notes) are
shared by default, and [Players](#players), [Sessions](#sessions) and
[Clues](#clues) need `--campaign`. A [Transcript](#transcripts) always takes
its campaign from its Session. [`add campaign`](#adding-a-campaign) creates a
new campaign.

### Templates and validation

A new record starts from the vault's own [template](record.md#anatomy) and is
validated against the vault's [schemas](record.md#types-statuses-and-schemas).
To change the starting values, edit the template,
[supply frontmatter](#supplying-frontmatter), or edit the record afterwards.
Enabled [extensions](extensions.md) can supply templates for particular types
or subtypes and add validation rules.

A new [record](record.md) must pass
[schema, link and contextual checks](validate.md#checks). If writing fails, is
interrupted or produces a record that fails validation, the command removes
the new record. The command then [validates the whole vault](validate.md#scope).
If that fails, it exits with status 1 and keeps the new record, which is
valid, for inspection. `add campaign` removes a partial campaign when writing
fails, but keeps it when validation fails.

## Adding a campaign

Add a [campaign](campaign.md):

```sh
armarium add campaign --vault ../my-vault
```

The new campaign's number is one greater than the largest existing one.
`--number N` chooses an unused positive number instead.

The Campaign and Clues templates supply the new campaign's first records. The
command changes their `campaign_1` and `C-1-` clue ID placeholders to the new
number and keeps the rest of their text. It copies no Players, Sessions or
Content from other campaigns.

## Adding a record

[Content](#content), [Players](#players) and [Notes](#notes) take a name,
which becomes the filename. A name may contain spaces; leave out `.md`.

[Sessions](#sessions) and [Clues](#clues) use numbered filenames. By default,
the number is one greater than the largest existing number of that type in the
campaign, including records in subfolders. Use `--number N` to choose an unused
number within the type's range.

A [reference to an existing record](record.md#links) must resolve to one
record; where a name is ambiguous, use the record's vault-relative path.

### Supplying frontmatter

Every record command accepts frontmatter as an inline JSON object or a UTF-8
JSON file:

```sh
armarium add content "Port Briselle" --subtype Location --frontmatter '{"summary":"A busy harbor"}'
armarium add content "Port Briselle" --subtype Location --frontmatter-file ../location.json
```

Supplied fields override the template's values, including fields that
[extensions](extensions.md) require. Nested objects merge; a list, a scalar or
null replaces the previous value. A campaign block uses its actual number,
such as `campaign_2`. A file path is relative to the current directory. Use
one option or the other, not both.

Give link fields as [wikilinks](record.md#links), such as
`"player": "[[Alex]]"`. The command sets some values itself, and frontmatter
cannot change them: `type`, Content `subtype`, Session `campaign` and
`session_number`, Transcript `session`, and Clue `subjects`, which it derives.
A missing required field or an invalid value fails
[validation](#templates-and-validation), and the command keeps no invalid new
record.

### Content

```sh
armarium add content "Port Briselle" --subtype Location --vault ../my-vault
armarium add content "Mira" --subtype PC --campaign 1 --frontmatter '{"player":"[[Alex]]"}' --vault ../my-vault
```

`--subtype` sets the [Content subtype](type.md#content): a core subtype, or
one an enabled [extension](extensions.md#declaring-subtypes) declares.
`armarium add content --help` lists those the vault permits. Supply each
subtype's required fields, such as a PC's `player`, as
[frontmatter](#supplying-frontmatter).

```sh
armarium add content "Year 42" --subtype Date --frontmatter '{"reckoning":"[[Royal Calendar]]","scale":"year"}' --vault ../my-vault
```

Where the vault's Content Type record declares
[`subtype_directories`](vault.md#where-records-live), the record goes in the
subfolder declared for its subtype, which the command creates if it is
missing:

```sh
armarium add content "Mara" --subtype NPC --campaign 1    # campaigns/campaign_1/content/npcs/Mara.md
armarium add content "Port Briselle" --subtype Location   # content/locations/Port Briselle.md
```

Other subtypes go directly in the Content directory.

A shared record starts with no [campaign state](campaign.md#state). A
campaign's record gets a `campaign_N` block for its campaign, and an Object or
Gear also gets `held_by` in that block.

Gear starts with an empty `source` unless the template supplies one. Its body
starts with a rules callout: the command keeps the template's callout if it
has one, and otherwise adds an empty one before the template's body.

### Sessions

```sh
armarium add session --campaign 1 --vault ../my-vault
```

`add session` creates a [Session](type.md#session), `S-N-NNN.md`, with its
campaign link and session number filled in. Session numbers run from 1 to 999.

### Players

```sh
armarium add player "Alex" --campaign 1 --vault ../my-vault
```

The starter template creates an unassigned [Player](type.md#player), with
`plays: []`. Any PCs it links to must be shared or in the same campaign. To
create a PC linked to the new Player, use [`add content`](#content); adding a
Player changes no PCs or backlinks.

### Notes

```sh
armarium add note "Working ideas" --vault ../my-vault
armarium add note "Session prep" --campaign 1 --vault ../my-vault
```

`add note` copies the vault's [Note](type.md#note) template, with its
frontmatter and body. An empty body is valid.

### Clues

```sh
armarium add clue --campaign 1 --vault ../my-vault --frontmatter '{"text":"The gate is locked from within."}'
```

`add clue` creates a [Clue](type.md#clue), `C-N-NNNN.md`. Clue numbers run
from 1 to 9999.

Supply nonblank `text`, in frontmatter or through the vault's template. The
text goes in the Clue's [frontmatter](record.md#anatomy), and its
[wikilinks](record.md#links) must link to shared or same-campaign
[Content](#content). The command sets `subjects` to those records, without
duplicates, or to `[]` when the text links to none. It keeps the template's
status, session fields, and Sessions section with its Base embed.

### Transcripts

```sh
armarium add transcript S-1-001 --body-file recorded-speech.md --vault ../my-vault
```

Name an existing [Session](#sessions) by its name or vault-relative path. Its
campaign and filename decide where the [Transcript](type.md#transcript) goes
and what it is called: `S-N-NNN Transcript.md`. The command never chooses a
Session itself.

`--body-file` is required. It names a UTF-8 Markdown file without
frontmatter:

```markdown
## Arrival

- [GM] The door opens.
- [Player] Who is there?
```

Follow the body format of a [Transcript](type.md#transcript): titled
level-two sections, each holding one bullet list of attributed,
single-paragraph utterances. The body replaces the template's sample. The
command imports text that is already formatted: it does not transcribe audio,
edit the speech, or change the source file or the Session. It checks the
body's grammar and the vault's schema before creating the file, and runs the
link and contextual checks after.
