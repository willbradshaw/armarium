# Armarium

A system-general foundation for tabletop roleplaying knowledge bases in Obsidian.
The starter provides shared setting content and one blank campaign, with templates
for Content, Clues, Sessions, Players, and Transcripts. Installable commands and
agent support are separate, later additions.

## Create a setting vault

From this checkout, copy `starter/` to a new folder outside the repository:

```sh
vault_path="../my-setting"
mkdir "$vault_path" && cp -R starter/. "$vault_path/"
```

Choose a destination whose parent exists. `mkdir` refuses an existing destination;
`&&` runs the copy only if creation succeeds. Hidden files are included.

Open the new folder as a vault in Obsidian. Start with
`campaigns/campaign_1/reference/Campaign.md` and edit its description.

## Vault structure

```text
assets/
content/                         Shared setting Content
campaigns/
  campaign_1/
    content/                     Campaign-specific Content
    clues/
    sessions/
      transcripts/
    reference/
      Campaign.md
      players/
      indexes/
        Clues.md
reference/
  schemas/
  templates/
  types/
  statuses/
```

Use `assets/` for durable maps, images and handouts. Shared rules and other external
reference material can live under `reference/`; campaign-specific supporting
material belongs under that campaign's `reference/`. Add optional directories
such as `bases/` when working views exist to put in them.

`.scratch/` is available for temporary working material and is ignored by Git.
Empty `.gitkeep` files preserve empty directories in Git; they have no special
meaning to Git or Obsidian and can be removed once the directory contains tracked
files. The copied vault can be its own Git repository.

## Create records

Copy a template from `reference/templates/`, rename it, and fill in its properties:

| Record | Destination and setup |
| --- | --- |
| Content | `content/` for shared setting information, or the campaign's `content/`. Choose a subtype and add its required fields from the [Content fields](starter/reference/types/Content.md). |
| Clue | The campaign's `clues/`, named `C-1-0001.md`, `C-1-0002.md`, etc. |
| Session | The campaign's `sessions/`, named `S-1-001.md`, `S-1-002.md`, etc. Set `session_number` and the campaign link. |
| Player | The campaign's `reference/players/`, named for the player. Link their PCs in `plays`. |
| Transcript | The campaign's `sessions/transcripts/`, named `S-1-001 Transcript.md`, etc. Fill its `session` link. |

Content has one body structure: Notes, Active Clues, Appearances. Its `subtype`
selects NPC, PC, Location, Faction, Object or Lore and determines the additional
frontmatter fields. For example, an NPC needs a `stats` key (possibly empty), while
a PC needs a nonempty link to a Player. Put pronouns and birth information in Notes
when relevant. The [JSON Schema](starter/reference/schemas/content.schema.json) defines common and
subtype fields, nullable values, campaign-state conditions and body heading order.
A future validator will parse a note into `{frontmatter, body}`; actual files remain
Markdown with YAML frontmatter. The schema targets completed records and stubs,
not unfinished templates. This starter does not include a validation command.

The body regex requires Notes, Active Clues and Appearances in order. It does not
parse Markdown: matching headings inside code fences can satisfy it, and it does
not enforce heading uniqueness. Link existence, target record types, campaign
agreement and appearance-history consistency need separate vault-aware checks.
URI format assertions must be enabled to validate external URL syntax; no network
request is needed. YAML parsers should preserve strings/nulls/lists/mappings and
report malformed or duplicate fields before schema validation.

Keep each shared entity in one Content page. Campaign state remains in separate
`campaign_1:`, `campaign_2:`, etc. blocks on that page. The initial template includes
campaign 1; retain, remove or add blocks according to the entry's recorded state.
A Clue is a candidate fact; creating or preparing it does not make it world canon.

## Live clue views

Active Clues on Content, Sessions on Clues, and the campaign Clue index use Dataview.
Enable that community plugin in Obsidian to render the tables. The starter does
not install plugins. Ordinary Markdown and properties remain usable without it.

The included links and queries target campaign 1. When adding another campaign,
update the campaign paths and record IDs in copied records and indexes. On a shared
Content page, give each campaign's Active Clues and Appearances their own labeled
subsections. No campaign-creation command is included yet.

Existing vaults are not migrated automatically. This revision changes paths and
replaces the separate NPC/PC/Location/Faction/Object/Lore types with Content plus
`subtype`; copying it over an existing vault would not perform that conversion.

Follow-on work is tracked in the
[repository issues](https://github.com/willbradshaw/armarium/issues).
