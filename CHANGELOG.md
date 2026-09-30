# Changelog

## Unreleased

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
