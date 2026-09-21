# Minimal Isles-derived starter

With Python 3.10 or later:

```sh
python3 scripts/create_vault.py /path/to/new-setting
```

The parent must exist. The new setting folder must be outside this checkout.
The installer copies `starter/vault/` exactly, including empty directories preserved
by `.gitkeep`. It refuses existing directories, files, and symlinks. A filesystem
failure during copying may leave an incomplete destination; inspect it before
removing anything or retrying at a different path.

Open the resulting folder as an Obsidian vault. Use the file browser to find
`campaign_1/Campaign.md`, edit its description, and copy templates into the relevant
content folders. Name sessions `S-1-001.md`, `S-1-002.md`, etc.; clues use
`C-1-0001.md`, `C-1-0002.md`, etc. Set the session number and other known metadata.
The directory name is the setting vault's name; there is no separate identity file.

```text
world/{locations,npcs,factions,lore,objects}/
campaign_1/
  Campaign.md
  index/Clues.md
  {sessions,transcripts,pcs,players,npcs,locations,factions,lore,objects,clues}/
reference/
templates/
types/
statuses/
assets/
.scratch/
```

World entities are shared setting records; campaign-bound entities and play records
live under `campaign_1/`. Entity state retains Isles' top-level `campaign_1:` block.
This increment installs one blank campaign. Adding campaigns and evaluating shared
history across them are follow-on work, not limitations of the intended product.

The inherited Active Clues, clue-session, and clue-index queries require the
Dataview community plugin, which this installer does not install or enable. Without
it, the Markdown and properties remain available but these sections do not render
as live tables. Session preparation retains Isles' table headings; automatic inline
summary expressions are not supplied by its source Session template. The Bases
replacement remains tracked separately in issue #5. There are no replacement
manual indexes to maintain in this increment.

The vault contains no private examples, generated navigation, agent instructions,
shared skills, utility scripts, or runtime configuration. Installed files are
user-owned. The vault can be moved or initialized as its own Git repository.
Scratch files and local Obsidian settings are ignored; assets are trackable.

## Extraction record

| Artifact | Isles source | Deliberate changes |
| --- | --- | --- |
| Entity and Content templates | `templates/{Content,Faction,Location,Lore,NPC,Object,PC}.md` | Resolve `{{campaign}}` to 1; qualify type/status links; remove species/class/subclass/level fields. Retain NPC `stats` and `birth_year`. |
| Session template | `templates/Session.md` | Replace private campaign link; qualify type; replace D&D encounter/XP and magic-item sections with generic encounter/reward placeholders. Remaining section order and table headings retained. |
| Clue template | `templates/Clue.md` | Qualify type/status links; resolve campaign query to 1. No new ID, campaign, or GM Notes fields. |
| Campaign reference | `campaign_1/Ghosts of Szamasz.md` | Generic filename/description; retain Reference type. |
| Clue index | `campaign_1/index/Clues.md` | Replace private campaign identity; qualify links; apply the reviewed candidate-fact correction to status explanation. Queries retained. |
| Type/status pages | Corresponding `types/` and `statuses/` pages | Short generic descriptions; reviewed candidate-fact semantics replace older canon assumptions. No new Setting or Campaign type. |
| Content directories | Isles root and `campaign_1/` | Group shared entities under agreed `world/`; omit system-specific and private content directories. |
| Obsidian settings | `.obsidian/app.json` | Keep automatic link updating; omit Isles' deletion preference. |
| Git ignores | `.gitignore` | Retain relevant scratch/settings ignores; generic credential and machine-file exclusions. |

The installer, its tests, and this documentation are new implementation support.
No proposed metadata map, party-holder flag, preparation-selection fields, extra
Player/Transcript templates, or new navigation structure is included.

## Verification

```sh
python3 -m unittest discover -s tests -v
```

See [acceptance evidence](starter-acceptance.md) for recorded results.

Manual Obsidian checklist (still pending):

- Open a fresh installed folder and inspect the campaign reference and templates.
- Copy a Session, NPC, and Clue template into their campaign directories. Confirm
  properties and type/status links resolve and no private setting names remain.
- If testing live queries, enable Dataview explicitly and record its version.
  Populate an original clue linked to the NPC and a session linked to the clue;
  confirm entity Active Clues, clue Sessions, and the campaign index render.
- Change the clue to Abandoned; confirm it leaves active results without adding
  its candidate text to the NPC's Notes.

File-level tests do not establish that query rendering works in Obsidian.
