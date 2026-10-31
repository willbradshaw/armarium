# Changelog

## Unreleased

### Added

- Add `paragraph_spacing` and `title_spacing` layout fields, with matching
  `armarium handout` flags.
- Warn about wrong sums and carry-overs in the XP section of `dnd-5-5` Sessions.

## 1.0.0 (2026-10-25)

The first stable release. From here, versions follow semantic versioning; see
[What a version promises](https://github.com/willbradshaw/armarium/blob/main/docs/releases.md#what-a-version-promises).

### Breaking changes

- **`armarium update` cannot update vaults made with 0.1.0.** It needs the
  `.armarium/` record that `armarium init` now writes. To move such a vault to
  this release, create a new vault with `armarium init`, copy in `content/`,
  `notes/`, `campaigns/` and `assets/`, and redo any edits to its other files.
- Require a `bases/` directory in every vault.
- Require each record's filename and aliases to be unique among the records one
  campaign can see: its own and the shared ones.
- Require a Session's in-game dates, when set, to link to Date Content.
- Replace the `--player` and `--text` options of `armarium add` with JSON
  frontmatter.
- Refuse more characters in the record names `armarium add` accepts.
- Require PyYAML built with libyaml.

### Added

- Add `armarium update` to bring the files Armarium copied into a vault up to
  date, merging the vault's own changes to them.
- Add commands to find and trace records, and to rename, merge and delete them
  with every link kept.
- Add commands to illustrate records, print them as player handouts, and
  transcribe session recordings.
- Add instructions and skills for coding agents to every vault.
- Add extensions for game systems, starting with D&D 5.5.
- Add the Date and Gear Content subtypes, Reference subtypes, and folders per
  subtype.
- Add guides to running a campaign and to developing Armarium.

### Changed

- Speed up validation about fourfold.
- Rewrite the README and the documentation for new users.

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
