# Changelog

## Unreleased

- Let extension rules declare the records a field's links must name.
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
