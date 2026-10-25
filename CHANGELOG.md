# Changelog

## Unreleased

- Point the vault layout page to `armarium init` for creating a vault, rather than to copying the starter vault.
- Rewrite the README for new users, and move the command reference into a documentation index at `docs/README.md`.
- Tell agents in the vault guide and `AGENTS.md` to bring Armarium's files up to date with `armarium update`, dry-running it first, and to leave `.armarium/` alone.
- Report each file `armarium update` merges on one line, count a merge or resolution that leaves the vault's file unchanged as kept, and name the conflicts folder relative to the vault.
- Add `armarium update --extensions` to also update every out-of-date installed extension.
- Report in validation a vault's copies of Armarium files or installed extensions that differ from the running Armarium's (`vault.outdated`).
- Add `armarium update` to bring the files Armarium copied into a vault up to date, merging the vault's own changes to them.
- Record in a new vault's `.armarium/` a copy of each starter file Armarium keeps up to date, and the Armarium version that supplied them.
- Make the `update-record` skill rename, merge and delete records with the commands, and list them in the vault guide.
- Add `armarium merge` to merge one record into another, repointing the links to it and listing where the two disagree.
- Add `armarium delete` to delete a record, refusing while links to it remain, and `--unlink` to turn those links into text.
- Add `armarium rename --alias` to keep the old name as an alias and as the wording of links to the record.
- Run the tests of how commands spell a path given in another case on every filesystem, rather than skipping them where names are case-sensitive.
- Refuse templates and files that are not records in `armarium illustrate`, `armarium handout` and `armarium trace --outbound`.
- Hold `armarium add` and `armarium rename` to the same rules for a record's name, refusing `^` in added names, and `* ? " < >`, control characters, a final dot and the name of another entry in the folder, in any case, in new names.
- Make `armarium illustrate ingest` write the `image` field double-quoted, as other commands write frontmatter.
- Add `armarium rename` to rename a record in its folder and rewrite every link to it.
- Add a shared way for commands to check, report and make their planned file changes, with a dry run that changes nothing, making them all or none and restoring the vault when a change fails or is interrupted.
- Speed up schema validation about tenfold by checking records with jsonschema-rs first, adding it as a dependency; jsonschema still reports each failure.
- Halve the time validation takes to index a vault, which speeds up validating a single record.
- Speed up validation by about a sixth, comparing paths by their parts rather than through each parent directory.
- Make `armarium validate` choose its worker processes when `--jobs` is not given, one per 500 records up to one per CPU.
- Add the Armarium logo, shown as a banner at the top of the README.
- Ship the `make-handouts` agent skill, point `prepare-session` to it, and let `illustrate-record` take in a picture the GM supplies.
- Add `armarium handout` to print records as handouts in a PDF, with a flag to set each field of their layouts.
- Add the renderer that prints records' callouts as handouts in a PDF, each in its handout layout, adding ReportLab as a dependency.
- Add `callout` and `title` to handout layouts, to print a callout other than `rules` and leave off the record's name, and let any Content hold a `> [!handout]` callout of the words players are given, such as a letter's.
- Add handout layouts, Reference records of subtype `Layout` in `reference/layouts/` that say how a kind of record prints as a handout.
- Allow in the shared `reference/` the subfolders the Reference Type record's `subtype_directories` declares, rather than `styles/` by name.
- Add `Sessions.base` and `Clues.base` to the starter vault's `bases/`, grouping every campaign's Sessions and Clues by campaign.
- Add Reference subtypes, starting with `Style`: styles now need `subtype: Style`, the Reference schema checks their fields, and the Reference Type record's `subtype_directories` keeps them in `reference/styles/`.
- Ship the `illustrate-record` agent skill, and a CSS snippet that shows black-opacity art in `assets/art/ink/` as white on Obsidian's dark theme.
- Make `armarium illustrate generate` paint three candidates by default.
- Add `armarium illustrate generate` to paint candidate pictures for a record with an image model from a prompt, and `references` and `sample` on illustration styles.
- Add `armarium transcribe --loose`, which loosens voice detection to keep quieter speech, and have the `create-transcript` skill use it when a pass loses quiet speech.
- Add `armarium illustrate prompt` to print the prompt for a record's picture, and optional `image` and `visual` fields, the latter for art direction, on all Content.
- Add illustration styles in `reference/styles/`, which say where `armarium illustrate ingest` puts each kind of art and how, and hold that art to a size budget in validation.
- Require a record's `image` path to name a file in the vault.
- Add a required `bases/` directory to the vault skeleton, with a `Content.base` of all Content and a table per core subtype.
- Add `armarium illustrate ingest` to take a picture into a vault as a record's image within a size budget, adding Pillow as a dependency.
- Make the `dnd-5-5` extension add encounter difficulty, XP and levels gained to the session skills, for campaigns with or without XP.
- Add Character Advancement, Combat Encounter Difficulty and Magic Item Values pages, with their SRD 5.2.1 tables, to the `dnd-5-5` extension.
- Let an extension, or a vault, add to a shipped agent skill through files in the skill's `addenda/` directory, which `armarium extension` installs and removes.
- Ship the `update-session-records` agent skill, which brings the records a played Session touches up to date, and the `process-session` skill, which runs the Transcript, write-up and record updates in order.
- Let the `create-transcript` and `write-up-session` skills create a Session that has no record yet.
- Stop the `write-up-session` skill writing a Session while a `(?)` remains, and make it ask separately before saving a style rule.
- Ship the `write-up-session` agent skill, and say in the Session Type record what Events and Loot hold.
- Ship the `prepare-session` agent skill, and say in the Session Type record what each field and section of a Session holds.
- Describe the Transcription reference Note in the `create-transcript` skill, not the Transcript Type record, and let it hold optional Cast and Traps sections.
- Ship the `create-transcript` agent skill, and say in the Transcript Type record what a Transcript keeps, how speakers are tagged and how doubt is marked.
- Add `armarium transcribe` to turn a session recording into raw transcript text with whisper.cpp and collapse repeated-line loops.
- Ship the `interview` agent skill, which questions the GM to develop part of the vault and records what is settled.
- Say in the Clue Type record what counts as a Clue, how its status follows play and what revealing it entails.
- Ship the `refresh-record` agent skill, which brings one record up to date with the records linked to and from it.
- Add `armarium trace --outbound` to list the files a record links to, and where.
- Stop `armarium find` inferring a campaign from the current directory; without `--campaign` it lists every campaign's records.
- Ship `AGENTS.md`, a vault guide and the `update-record` agent skill in the starter and example vaults.
- Require a record's filename and aliases to be its own among the records one campaign can see, and add `armarium find --campaign`.
- Allow an optional `docs/` directory and `AGENTS.md` at the vault root, neither holding records.
- List a file with the name sought in `armarium find` even when its frontmatter cannot be parsed.
- Add `armarium trace` to list the records that link to a record, and where.
- Add `armarium find` to list the records with a given name or alias.
- Let the Content Type record declare `subtype_directories`: a subfolder per subtype that `armarium add content` files into and validation enforces.
- Define appearances per Content subtype and what belongs in Notes; Type records point to `armarium add`.
- Check PC `class`, `subclass` and `level` in the `dnd-5-5` extension.
- Require Monster `spells` to link Spells and NPC `stats` links to name a Monster in `dnd-5-5`.
- Let extension rules declare which record types the wikilinks in a field must target.
- Meta-validate each distinct schema text once per process, not on every load.
- Add `armarium validate --jobs N` to validate a directory's records with several processes.
- Require PyYAML built with libyaml and parse YAML with it, keeping the Python parser's error messages.
- Speed up directory validation: read declared directories once, skip inline Markdown parsing and sort findings once.
- Add a bare Divine Sense class feature page to the `dnd-5-5` rules reference.
- Add bare rules reference pages (rules terms, a condition and feats) to the `dnd-5-5` extension.
- Load each schema and the extension set once per validation run, not once per record.
- Add a Monster Content subtype to the `dnd-5-5` extension.
- Let extension rules require named code blocks to hold YAML mappings.
- Require `requires_save` and `requires_attack` on `dnd-5-5` Spells.
- Add a Spell Content subtype to the `dnd-5-5` extension.
- Add optional `content_tags` to Content, replacing Gear's `item_tags` in `dnd-5-5`.
- Let extensions declare new Content subtypes, each with a template.
- Allow an optional vault `scripts/` directory for tooling and tests, excluding
  its contents from record validation during directory scans.
- Add the `dnd-5-5` extension with D&D 2024 Gear fields and a Gear template.
- Add JSON frontmatter input to all record-creation commands, replacing dedicated
  Player, Date and Clue field options.
- Add `armarium extension update` and record the supplying Armarium version;
  require `--allow-downgrade` when replacing an extension from a newer version.
- Add optional vault extensions with additive schema checks and subtype templates.
- Add extension selection during initialization and commands to enable and remove
  extensions in existing vaults.
- Demonstrate Location climate metadata with an extension enabled in the example vault.
- Add Gear Content with provenance, a rules callout, optional image/source URL,
  and campaign possession tracking.
- Clarify Date versus recurring calendar lore, and how brainstorming Notes become
  established Content or Session preparation.
- Add the Date Content subtype with required calendar and scale fields, validation,
  and `armarium add content` support.
- Require populated Session in-game dates to link to Date Content.
- Ignore local vaults other than starter and example, and exclude them from package
  builds and package-test setup.

## 0.1.0 (2026-09-30)

- Add `armarium init` for creating standalone vaults.
- Add `armarium add` subcommands for campaigns, Content, Clues, Sessions, Players,
  Notes, and Transcripts, using vault-local templates and conventions.
- Add `armarium validate` for records, directories, and vaults, with checks for
  schemas, Markdown structure, wikilinks, and relationships between records.
- Add shared setting content and campaign-specific records, with Obsidian Bases
  views for clues and session preparation.
- Add a starter vault and a two-campaign example vault.
- Add the MIT license and changelog-driven release automation.
