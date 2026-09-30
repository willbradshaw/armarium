# Adding to a vault

`armarium add` creates [campaigns](#adding-a-campaign) and [records](#adding-a-record)
in an existing [vault](vault.md) using its local templates and conventions, then
[validates the result](#templates-and-validation). For example:

```sh
armarium add campaign --vault ../my-vault
armarium add content "Port Briselle" --subtype Location --vault ../my-vault
armarium add session --campaign 1 --vault ../my-vault
```

For a new vault, start with [`armarium init`](init.md).

## Shared behavior

All commands share rules for [vault selection](#choosing-a-vault-and-destination),
[campaign selection](#choosing-a-campaign) and [templates and
validation](#templates-and-validation).

### Choosing a vault and destination

Pass `--vault PATH` to select a vault's root directory, using an absolute path or a path
relative to your current directory. Omit it to discover the vault from your current
directory when running anywhere inside it.

Records go in the selected vault's [declared directory](vault.md#where-records-live) for
their type and [campaign scope](#choosing-a-campaign), rather than directly in the
current directory. Existing records and campaigns are never overwritten.

### Choosing a campaign

While inside a [campaign directory](campaign.md#directory) or any descendants, new
records created with `armarium add` are added to that campaign. Use `--campaign N` to
select another existing campaign. Selecting a different vault does not inherit the
current campaign.

Outside a campaign directory, [Content](#content) and [Notes](#notes) default to shared
scope; [Players](#players), [Sessions](#sessions) and [Clues](#clues) require
`--campaign`. [Transcripts](#transcripts) always take their campaign from the selected
Session. [`add campaign`](#adding-a-campaign) creates a new campaign.

### Templates and validation

Initial values come from the vault's local [templates](record.md#anatomy), and validation
uses its [schemas](record.md#types-statuses-and-schemas). Edit a template to change
defaults, or edit the new record afterward.

A new [record](record.md) must pass [schema, link and contextual
checks](validate.md#checks). Failed writes, interruptions and record-validation failures
remove the new record. Each command then [validates the whole vault](validate.md#scope);
failure exits with status 1 and retains the valid new record for inspection. Campaign
creation removes partial campaigns on write failure, but retains them on validation
failure.

## Adding a campaign

Add a [campaign](campaign.md):

```sh
armarium add campaign --vault ../my-vault
```

The new number is one greater than the largest existing campaign number; `--number N`
chooses an unused positive number explicitly.

Campaign and Clues templates supply the initial records. Their `campaign_1` and `C-1-`
clue ID placeholders are updated to the new number; other text is preserved. Players,
sessions and content are not copied from existing campaigns.

## Adding a record

[Content](#content), [Players](#players) and [Notes](#notes) take a name, which becomes
the filename. Names may contain spaces; omit `.md`.

[Sessions](#sessions) and [Clues](#clues) use numbered filenames. By default, the number
is one greater than the largest existing number of that type in the campaign, including
archives. Use `--number N` to choose an unused number within the type's range.

[References to existing records](record.md#links) must resolve uniquely; use
vault-relative paths when names are ambiguous.

### Content

```sh
armarium add content "Port Briselle" --subtype Location --vault ../my-vault
armarium add content "Mira" --subtype PC --campaign 1 --player Alex --vault ../my-vault
```

Use `--subtype NPC|PC|Location|Faction|Object|Lore|Date` to select the [Content
subtype](type.md#content). Required nullable subtype fields start empty unless set in
the template. PCs need an existing [Player](#players), supplied with `--player` or in
the template. Dates need `reckoning` and `scale`, supplied with `--reckoning` and
`--scale` or in the template. The reckoning must identify existing calendar Content.

```sh
armarium add content "Year 42" --subtype Date --reckoning "Royal Calendar" --scale year --vault ../my-vault
```

Shared records start without [campaign state](campaign.md#state). Campaign-specific
records get a `campaign_N` block, where `N` is the selected campaign number; Objects
also get `held_by` in that block.

### Sessions

```sh
armarium add session --campaign 1 --vault ../my-vault
```

Creates a [Session](type.md#session), `S-N-NNN.md`, with the campaign link and session
number filled in. Session numbers range from 1 to 999.

### Players

```sh
armarium add player "Alex" --campaign 1 --vault ../my-vault
```

The standard template creates an unassigned [Player](type.md#player) with `plays: []`.
Configured links must target shared or same-campaign PCs. Use [add content](#content) to
create a PC linked to the new Player; creating a Player does not change PCs or
backlinks.

### Notes

```sh
armarium add note "Working ideas" --vault ../my-vault
armarium add note "Session prep" --campaign 1 --vault ../my-vault
```

Copies the local [Note](type.md#note) template, including its metadata and body. An
empty body is valid.

### Clues

```sh
armarium add clue --campaign 1 --vault ../my-vault --text 'The gate is locked from within.'
```

Creates a [Clue](type.md#clue), `C-N-NNNN.md`. Clue numbers range from 1 to 9999.

Supply nonblank `--text`, or omit it to use nonblank text from the local template.
`armarium add clue --vault ../my-vault --help` shows the discovered default text, or
indicates that `--text` is required when the template text is blank.

Text goes in [frontmatter](record.md#anatomy). Its [wikilinks](record.md#links) must
target shared or same-campaign [Content](#content). `subjects` is derived from those
targets without duplicates, or `[]` for unlinked text. Template status, session fields
and the Sessions section/Base embed are preserved.

### Transcripts

```sh
armarium add transcript S-1-001 --body-file recorded-speech.md --vault ../my-vault
```

Select an existing [Session](#sessions) by name or vault-relative path. Its campaign and
identity determine the [Transcript](type.md#transcript) destination, `S-N-NNN
Transcript.md`. No Session is selected automatically.

`--body-file` is required and reads UTF-8 Markdown without frontmatter:

```markdown
## Arrival

- [GM] The door opens.
- [Player] Who is there?
```

Follow the [Transcript body format](type.md#body-7): titled level-two sections, each
containing one bullet list of attributed, single-paragraph utterances. The supplied body
replaces the template's instructional sample. The command imports already-formatted text
without transcribing audio, editing speech or changing the source file or Session. Body
grammar and the local schema are checked before creating the file; link and contextual
checks follow.
