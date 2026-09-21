# Validate your vault

Check any **Armarium vault**, including populated campaigns and shared worlds.
Validation reports structural mistakes without changing your files.

## Run it

Requires Python **3.14+**. From the Armarium checkout:

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/validate_vault.py "/path/to/your vault"
```

From elsewhere, use absolute paths to the executable and script. Exit status:
**0** success, **1** validation errors, **2** incorrect command arguments.

Each error identifies a relative file, a line or property where possible, and
what to fix. For example:

```text
world/npcs/Guide.md (summary): [field.required] Add this required property.
```

## What is checked

| Check | What must be true |
| --- | --- |
| Files | An existing vault directory and readable UTF-8 Markdown. |
| YAML | Closed frontmatter, valid mapping, no duplicate keys (including nested keys and merge collisions). |
| Types | Content pages and supported named templates link to `types/` definitions. Status definitions have `applies_to`. |
| Placement | Records within `world/` or `campaign_N/` use their plural folder, such as `npcs/`. PC, Player, Transcript, Session and Clue records cannot use world scope. |
| Properties | Required keys and known value shapes, listed below. |
| Campaign state | Campaign-scoped entities have a matching `campaign_N` mapping. Supplied mappings name existing campaigns and contain `first_session`, `last_session`, and (for Objects) `held_by`. Session references belong to that campaign. |
| Clue status | A definition in `statuses/` with `applies_to` linking to `types/Clue`. |
| Identity | Sessions/Clues use `S-N-NNN.md` / `C-N-NNNN.md` in matching `campaign_N/` folders. Session numbers are positive integers matching filenames; `campaign` links to that campaign's `Campaign.md` Reference record. Clue session references stay within its campaign. |
| Headings | Required levels and order, listed below. |
| Wikilinks | Valid syntax, one canonical target, appropriate record types for property links, and escaped display pipes (`\|`) in tables. |

Unused folders are optional; shared/root entities need no campaign state.
Custom types, properties, folders, and nested content are allowed. Ordinary
notes/indexes need no entity metadata. No `campaign_1`, template files, or fixed
status names are required. Actual Sessions/Clues still need campaign scope.

### Required properties

Here, **entities** means Location, NPC, Faction, Lore, Object and PC.

| Page | Required keys, in addition to `type` |
| --- | --- |
| Every entity | `summary`; campaign state when in campaign scope |
| Location | `parent_location` |
| NPC | `aliases`, `stats`, `birth_year` |
| Faction | `members` |
| Lore | `aliases` |
| PC | `player`, `pronouns` |
| Clue | `status`, `text`, `subjects`, `first_session`, `last_session` |
| Session | `date`, `campaign`, `session_number`, `aliases`, `players_absent`, `in_game_start_date`, `in_game_end_date` |

**Unknown values may be null**, except `type`, `status`, `applies_to`, `campaign`,
campaign mappings, and an actual Session's `session_number`. Empty text and
lists are valid. Template aliases may contain a blank placeholder; actual
records must remove or fill it. Templates get property/body/link checks, but
not record filename/number checks. `templates/Content.md` is body-only.

| Property | Shape when known |
| --- | --- |
| `summary`, `text`, `pronouns` | Text |
| `aliases` | List of text values |
| `stats`; `birth_year` | Text or mapping; integer or text, respectively |
| `date`, `in_game_start_date`, `in_game_end_date` | YAML date, text or integer; no calendar-specific checks |
| `parent_location`; `player` | Location link; Player link |
| `held_by`; `first_session`, `last_session` | Entity link; Session links |
| `members`, `subjects`; `players_absent` | Lists of entity links; list of Player links |

Record links must target actual records, not templates or type/status definitions.
Known shapes apply wherever those properties appear, including custom pages.

### Required headings, in order

- **Entities:** `## Notes` → `## Active Clues` → `## Appearances`.
- **Clues:** `## Sessions`.
- **Sessions:** `# Preparation`, followed by `## Starting scene`, `Other scenes`,
  `Secrets & Clues`, `Locations`, `Important NPCs`, `Scene notes`, `Encounters`,
  `Prepared rewards` (all level 2); then `# Notes`, `## Preamble`, `## Events`,
  `## Rewards`, `### Loot`.

### Link handling

Use vault-relative paths or unambiguous basenames, with optional `.md`:
`[[types/NPC]]`, `[[Guide#Notes|Our guide]]`, `![[handouts/map.png]]`.
Resolution is case-sensitive. Absolute paths and `..` are rejected. YAML aliases
are display names, not targets: use `[[Guide|Nickname]]`, not `[[Nickname]]`.

Anchors check the **file only**, not the heading/block. `[[#Notes]]` targets the
current page. Literal links in Dataview/DataviewJS fences and inline `= ...` /
`$= ...` expressions are checked; other fenced/inline code is treated as examples.

## Limits

Hidden paths and all symlinks are skipped. Queries are not executed. Ordinary
Markdown URL links, dynamic targets, heading/block existence, calendar rules,
game-system arithmetic, writing style, historical consistency, and full
Player/Transcript schemas are not checked. Query text is unrestricted, so
Dataview can be replaced with other views.

## Validation versus tests

**Validation checks your vault. Tests check the validator.** You only need the
validation command above. Contributors can run the regression suite with:

```sh
.venv/bin/python -m unittest discover -s tests/validation -v
```

Tests cover populated user vaults, the starter, deliberate errors, and read-only
behavior. The starter's complete folder layout is tested separately; your vault
does not have to reproduce it.
