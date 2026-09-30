# Changelog

## Unreleased

## 0.1.0 (2026-09-30)

Initial release of Armarium, a system-general toolkit for tabletop roleplaying
knowledge bases in Obsidian.

- Create a standalone vault with `armarium init`.
- Add campaigns, Content, Clues, Sessions, Players, Notes, and Transcripts with
  `armarium add`, using the vault's own templates and conventions.
- Validate individual records, directories, and whole vaults, including schemas,
  Markdown structure, wikilinks, and relationships between records.
- Share setting content across campaigns, with campaign-specific clues and
  session preparation views powered by Obsidian Bases.
- Include a starter vault and a two-campaign example demonstrating the conventions.
- Distribute the code and vault materials under the MIT license.

Requires Python 3.14+, Obsidian 1.13.7+, Bases, and the Frontmatter Markdown Links
plugin. Long text can be clipped in Bases tables; open the record to read it in
full. Existing vaults are not automatically updated when Armarium is upgraded.
