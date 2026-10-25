# Changelog

## Unreleased

### Breaking changes

These change what 0.1.0 accepted:

- Require a `bases/` directory in the vault skeleton, holding `Content.base`,
  `Sessions.base` and `Clues.base`.
- Require each record's filename and aliases to be its own among the records
  one campaign can see.
- Require a Session's in-game dates, when set, to link to Date Content.
- Replace `armarium add content --player` and `armarium add clue --text` with
  JSON frontmatter, through `--frontmatter` or `--frontmatter-file`.
- Refuse more record names in `armarium add`: `^`, `* ? " < >`, control
  characters, a final dot, and the name of another entry in the folder, in any
  case.
- Require PyYAML built with libyaml.
- Leave vaults made with 0.1.0 out of `armarium update`, which needs the
  `.armarium/` record that `armarium init` now writes.

### Added

- Add `armarium update` to bring the files Armarium copied into a vault up to
  date, merging the vault's own changes to them:
  - `armarium init` records a copy of each managed file, and the Armarium
    version, in `.armarium/`;
  - conflicts wait in `.scratch/armarium-update/` to be resolved;
  - `--extensions` also updates out-of-date installed extensions;
  - validation reports copies that differ from the running Armarium's
    (`vault.outdated`).
- Add commands to find, trace and change records with every link kept:
  - `armarium find` lists the records with a name or alias;
  - `armarium trace` lists the links to a record, and `--outbound` those from
    it;
  - `armarium rename` renames a record and rewrites every link to it, and
    `--alias` keeps the old name;
  - `armarium merge` merges one record into another, listing where the two
    disagree;
  - `armarium delete` deletes a record, refusing while links to it remain,
    and `--unlink` turns them into text;
  - each change is all or nothing, with a dry run.
- Add `armarium illustrate` to make a record's picture:
  - `prompt` prints the prompt, from the record and its style;
  - `generate` paints candidates with an image model;
  - `ingest` takes a picture into `assets/` within a size budget;
  - illustration styles in `reference/styles/` say how each kind of art is
    painted and stored, and validation holds the art to its budget;
  - optional `image` and `visual` fields on all Content, and a CSS snippet
    that shows black-opacity art as white on a dark theme.
- Add `armarium handout` to print records as player handouts in a PDF, with
  handout layouts in `reference/layouts/` and a `> [!handout]` callout for
  the words players are given.
- Add `armarium transcribe` to turn a session recording into raw transcript
  text with whisper.cpp, collapsing repeated-line loops, with `--loose` for
  quiet speech.
- Ship instructions and skills for coding agents in every vault: `AGENTS.md`,
  a vault guide, and the `interview`, `update-record`, `refresh-record`,
  `prepare-session`, `create-transcript`, `write-up-session`,
  `update-session-records`, `process-session`, `illustrate-record` and
  `make-handouts` skills. Extensions and vaults can add to a skill through its
  `addenda/` directory.
- Add to the record types:
  - the Date and Gear Content subtypes;
  - optional `content_tags` on Content;
  - Reference subtypes, `Style` and `Layout`;
  - `subtype_directories` on the Content and Reference Type records, a
    subfolder per subtype;
  - optional `docs/`, `scripts/` and `AGENTS.md` at the vault root;
  - fuller guidance in the Type records on what each field and section holds.
- Extend extensions:
  - add `armarium extension enable`, `remove` and `update`, and
    `armarium init --extension`;
  - let an extension declare Content subtypes, the record types a field's links
    must target, and code blocks that must hold YAML;
  - add the `dnd-5-5` extension, with Gear fields, Spell and Monster subtypes,
    rules reference pages with SRD 5.2.1 tables, and encounter difficulty and
    XP in the session skills;
  - add the `example` extension, enabled in the example vault.
- Add `armarium validate --jobs N`, which by default uses one worker per 500
  records, up to one per CPU.
- Add guides to running a campaign and to developing Armarium, a
  documentation index, a rewritten README with the Armarium logo, and a
  statement of what a version promises.

### Changed

- Speed up validation about fourfold, checking schemas with jsonschema-rs
  first and indexing the vault once: a vault of 10,000 records takes about 8
  seconds rather than 33.
- Make `armarium illustrate generate` paint three candidates by default.
- Reword the documentation in plain, active sentences, and say that the Type
  records are the authority on each type.

### Fixed

- List a file with the name sought in `armarium find` even when its
  frontmatter cannot be parsed.
- Refuse templates and files that are not records in `armarium illustrate`,
  `armarium handout` and `armarium trace --outbound`.
- Write the `image` field double-quoted in `armarium illustrate ingest`, as
  other commands write frontmatter.
- Fix the README's links on PyPI, and the docs' account of `held_by`,
  numbering in subfolders and creating a vault.

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
