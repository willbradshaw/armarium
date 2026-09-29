# Adding to a vault

`armarium add` uses the selected vault's templates, Type directory declarations
and schemas. Pass `--vault PATH`, or omit it when running inside the vault.
Existing records and campaigns are never overwritten.

## Choosing a campaign

Inside a campaign directory or any descendant, Content, Notes, Players, Sessions
and Clues default to that campaign. Use `--campaign N` to select another existing
campaign. Selecting a different vault does not inherit the current campaign.

Outside a campaign directory, Content and Notes default to shared scope; Players,
Sessions and Clues require `--campaign`. Transcripts take their campaign from the
selected Session. `add campaign` creates a new campaign.

## Templates and validation

Initial values come from the vault's local templates. Edit a template to change
defaults, or edit the new record afterward. Content, Player and Note names may
contain spaces; omit `.md`.

A new record must pass schema, link and contextual checks. Failed writes,
interruptions and record-validation failures remove the new record. Each command
then validates the whole vault; failure exits with status 1 and retains the valid
new record for inspection. Campaign creation removes partial campaigns on write
failure, but retains them on validation failure.

## Campaigns

Add a [campaign](campaign.md):

```sh
armarium add campaign --vault ../my-vault
```

The new number is one greater than the largest existing campaign number;
`--number N` chooses an unused positive number explicitly.

Campaign and Clues templates supply the initial records. Their `campaign_1` and
`C-1-` clue ID placeholders are updated to the new number; other text is preserved.
Players, sessions and content are not copied from existing campaigns.

## Content

```sh
armarium add content "Port Briselle" --subtype Location --vault ../my-vault
armarium add content "Mira" --subtype PC --campaign 1 --player Alex --vault ../my-vault
```

Use `--subtype NPC|PC|Location|Faction|Object|Lore`. Required nullable subtype
fields start empty unless set in the template. PCs need an existing Player,
supplied with `--player` or in the template; use a vault-relative Player path
when its name is ambiguous.

Shared records start without campaign state. Campaign-specific records get a
`campaign_N` block, where `N` is the selected campaign number; Objects also get
`held_by` in that block.

## Sessions

```sh
armarium add session --campaign 1 --vault ../my-vault
```

Creates `S-N-NNN.md` with the campaign link and session number filled in.
Numbering advances past the largest existing session number, including archives;
`--number N` chooses an unused number from 1 to 999.

## Players

```sh
armarium add player "Alex" --campaign 1 --vault ../my-vault
```

The standard template creates an unassigned Player with `plays: []`. Configured
links must target shared or same-campaign PCs. Use [add content](#content) to
create a PC linked to the new Player; creating a Player does not change PCs or
backlinks.

## Notes

```sh
armarium add note "Working ideas" --vault ../my-vault
armarium add note "Session prep" --campaign 1 --vault ../my-vault
```

Copies the local Note template, including its metadata and body. An empty body
is valid.

## Clues

```sh
armarium add clue --campaign 1 --vault ../my-vault --text 'The gate is locked from within.'
```

Creates `C-N-NNNN.md`. Numbering advances past the largest existing clue number,
including archives; `--number N` chooses an unused number from 1 to 9999.

Supply nonblank `--text`, or omit it to use nonblank text from the local template.
`armarium add clue --vault ../my-vault --help` shows the discovered default text,
or indicates that `--text` is required when the template text is blank.

Text goes in frontmatter. Its wikilinks must resolve uniquely to shared or
same-campaign Content; use qualified paths for ambiguous names. `subjects` is
derived from those targets without duplicates, or `[]` for unlinked text.
Template status, session fields and the Sessions section/Base embed are preserved.

## Transcripts

```sh
armarium add transcript S-1-001 --body-file recorded-speech.md --vault ../my-vault
```

Select an existing Session by unambiguous name or qualified vault-relative path.
Its campaign and identity determine the destination, `S-N-NNN Transcript.md`.
No Session is selected automatically.

`--body-file` is required and reads UTF-8 Markdown without frontmatter:

```markdown
## Arrival

- [GM] The door opens.
- [Player] Who is there?
```

Use titled level-two sections, each containing one bullet list of attributed,
single-paragraph utterances. The supplied body replaces the template's instructional
sample. The command imports already-formatted text without transcribing audio,
editing speech or changing the source file or Session. Body grammar and the local
schema are checked before creating the file; link and contextual checks follow.
