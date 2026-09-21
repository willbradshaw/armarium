# Structural vault validation

`python scripts/validate_vault.py PATH` validates the explicitly chosen vault
root. Install `requirements.txt` in a virtual environment first; Python 3.9+
and PyYAML are the only requirements. Tests use the standard-library `unittest`.
No global installation, setup script, model credentials, plugin, or user vault
is required. The script works from any current directory. Exit 0 means valid;
exit 1 means diagnostics; argparse uses exit 2 for invalid command arguments.

Diagnostics include a vault-relative file/directory, a stable rule identifier,
and a line for YAML/wikilinks or a field for property errors where possible.
Files are never rewritten. YAML and file-read failures are reported while the
remaining pages continue to be checked.

## Discovery and page categories

The required root directories are `world`, `templates`, `types`, `statuses`,
`reference`, `assets`, and at least one `campaign_<number>`. World requires
`locations`, `npcs`, `factions`, `lore`, and `objects`; each campaign requires
those plus `pcs`, `players`, `sessions`, `clues`, `transcripts`, and `index`.
All may be empty. Additional directories and fields are allowed.

Hidden files/directories (including `.git`, `.scratch`, caches and `.gitkeep`)
are ignored. All symlinks are skipped, including internal symlinks; links to
skipped files are unresolved. In particular, traversal never follows a symlink
outside the vault. Supported content inside `world/` or `campaign_N/` must be
in its corresponding plural folder; nested user folders inside it are allowed.
PCs, Players, Transcripts, Sessions and Clues belong in campaign scope. Root
and custom-folder entities are allowed; actual Sessions/Clues still require a
containing campaign for identity checks.

Every visible Markdown page gets YAML and link checks, including pages whose
type cannot be parsed. Content-folder pages and named supported templates need
a type. Indexes, reference pages, ordinary notes, and definition pages do not
need entity frontmatter. `templates/Content.md` is a body-only scaffold.
Templates get property/body checks but no record filename or session-number
identity checks. Type/status definition pages are not entities. Player and
Transcript placement/type links are recognized, but their future schemas and
full transcript body rules are deferred.

## Properties and unknown values

Frontmatter must be a YAML mapping; duplicate keys at every depth (including
merge collisions) are errors. Type must be a canonical link resolving to a
Markdown definition directly in `types/`. Custom type definitions are allowed;
only the supported types below have entity-specific required fields.

| Type | Required properties |
| --- | --- |
| Location, NPC, Faction, Lore, Object, PC | `type`, `summary`, at least one `campaign_N` mapping |
| Location | `parent_location` |
| NPC | `aliases`, `stats`, `birth_year` |
| Faction | `members` |
| Lore | `aliases` |
| PC | `player`, `pronouns` |
| Each entity campaign mapping | `first_session`, `last_session`; Object also `held_by` |
| Clue | `type`, `status`, `text`, `subjects`, `first_session`, `last_session` |
| Session | `type`, `date`, `campaign`, `session_number`, `aliases`, `players_absent`, `in_game_start_date`, `in_game_end_date` |
| Status definition | `applies_to` |

Required means the key must exist, not that its value is known. Null is allowed
except for type, status, applies_to, campaign links, campaign mappings, and an
actual Session's session_number. Empty summary/text strings and empty lists
are valid, including on records; this checker does not assess completeness.

Known values use these shapes:

- `summary`, `text`, and `pronouns`: strings. `aliases`: a list of strings or
  null. The starter Session template's deliberate `aliases: [null]` placeholder
  is accepted only in templates; remove/fill that entry on a copied Session.
- `stats`: string (including a link) or mapping, with no system-specific stat
  registry. `birth_year`: integer or calendar-neutral string. No removed
  species/class/level/XP fields are required.
- `parent_location`: a Location link; `player`: a Player link;
  `held_by`: an entity link; `first_session`/`last_session`: Session links.
  These links must resolve to actual records, not templates or definitions.
- `members` and `subjects`: lists of entity links; `players_absent`: a list of
  Player links. Null lists and empty lists are accepted; null list entries are
  not links.
- `campaign_N`: a mapping to nullable properties, referencing an existing
  campaign directory. Campaign-scoped entities need their containing campaign's
  mapping. Session references in each mapping must belong to that campaign.
- Session `campaign`: a Reference link to the containing campaign's `Campaign.md`.
  `session_number`: a positive integer when supplied, required on actual records.
  Dates accept YAML dates, strings, or integer calendar values; calendar syntax
  and chronology are not validated.
- Clue `status`: a link to a Markdown definition directly in `statuses/`, whose
  `applies_to` resolves to `types/Clue.md`. `applies_to` must resolve to a type
  definition, not a same-named template.

Known field shapes also apply when those fields are supplied on custom/reference
pages. Extra fields are accepted. Entity templates determine which keys are
required; for example, aliases is required on NPC/Lore, optional on Location.

## Body and identity

Entities require level-2 Notes, Active Clues, Appearances in that order. Clues
require level-2 Sessions. Sessions require the current template's level-1
Preparation and Notes, with their ordered level-2 sections and level-3 Loot.
Additional headings and nested content are allowed. No literal Dataview query
text is required; future Bases views can replace queries.

Actual Session/Clue filenames use `S-N-NNN.md` / `C-N-NNNN.md`; the campaign
component must match the containing `campaign_N`. Session numbers must match
the filename and be positive integers (booleans are not integers). No `id`
property is required. Clue session references must belong to its campaign.

## Wikilinks and code

Resolution accepts full vault-relative paths, unambiguous basenames, optional
`.md`, display aliases, embeds/assets, and heading/block suffixes. Resolution is
case-sensitive and does not prefer a nearby or root file over an ambiguous
basename. Use `[[types/NPC]]`, not `[[NPC]]` when both type and template exist.
Paths must not be absolute or contain `..`.

YAML aliases are display names, not canonical link targets. An alias-only link
reports the known canonical paths; use `[[canonical/path|Alias]]`. In Markdown
tables escape the display pipe: `[[canonical/path\|Alias]]`. Malformed bracket
pairs and unescaped alias pipes in table rows produce diagnostics.

Anchors validate **only the target file**, not the existence of a heading/block.
`[[#Heading]]` and `[[#^block]]` refer to the current file. Ordinary fenced code
and inline code are examples and are not scanned for links. Literal wikilinks
in `dataview`/`dataviewjs` fences and inline Dataview expressions (`= ...` or
`$= ...` inside backticks) are scanned; queries are not executed. Dynamic string
targets, ordinary Markdown `[label](url)` links, and Dataview FROM strings are
outside this wikilink increment.

## Source rule mapping and deferrals

The issue #6 contract and the committed starter at PR #12 are the public source
of truth. The optional `.scratch/isles` source checkout was unavailable during
implementation, so no direct comparison with its implementations/tests could
be performed. No private source or runtime dependency was imported.

| Requested source rule family | Public implementation |
| --- | --- |
| Vault/index discovery | `validator.discover`: required folders, numerical campaigns, hidden/symlink exclusions |
| Common/content properties | `parsing.parse_page`, `Checker.check`: duplicate-safe YAML, nullable template schema, field shapes and placement |
| Wikilinks | `scan_links`, `Resolver`: canonical path/basename resolution, aliases, anchors, assets, table/code distinction |
| Content/session body rules | `Checker.sections`: ordered structural headings without query-text or writing-style enforcement |
| Clue/session identity | Actual-record filename, containing campaign, session number, and status applicability checks |

Deliberate public behavior includes unfinished null templates and calendar-neutral
NPC stats/birth_year, instead of any stricter personal-vault requirements. With
Isles unavailable, these are explicit compatibility choices, not claims of exact
parity. No starter correction was needed.

Deferred: heading/block existence, system registries, D&D arithmetic, custom
calendar validation, style/tense/punctuation rules, cross-record history
reconciliation (#16), subject/text synchronization, entity sweeps, full
transcript workflows, and proposed Player/Transcript schemas (#15). Validation
does not edit content or invent missing values. Multi-campaign history choices
(#13) and prototype views (#5) are not dependencies.

## Regression evidence

`python -m unittest discover -s tests/validation -v` builds independent temporary
fixtures from the real starter. It tests positive populated/null/custom/campaign
cases, isolated negative mutations with expected rule IDs/fields, CLI success
and failure statuses, continuation after bad YAML/encoding, and byte-for-byte
preservation. The copied vault has spaces in its path; the CLI runs from outside
the vault and checkout. CI runs these tests and separately validates `starter/`
on PRs; deliberately broken fixtures are expected to fail inside the tests, not
treated as a request to validate the repository as a vault.
