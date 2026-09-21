# Armarium

A system-general foundation for AI-assisted tabletop roleplaying knowledge bases:
Obsidian vault structure, page templates, reusable skills, and supporting scripts.

The starter currently provides shared world folders and one blank campaign, with
templates for entities, clues, and sessions. Multi-campaign setup, shared skills,
and supporting utilities are planned follow-on work.

## Create a setting vault

From this checkout, copy `starter/` to a new folder outside the repository:

```sh
vault_path="../my-setting"
mkdir "$vault_path" && cp -R starter/. "$vault_path/"
```

Choose a destination whose parent exists. `mkdir` refuses an existing destination;
`&&` runs the copy only if creation succeeds. The copy includes hidden files.
No Python installation or setup script is needed.

Open the new folder as a vault in Obsidian. Start with `campaign_1/Campaign.md`,
edit its description, and copy templates into the appropriate content folders.
Name sessions `S-1-001.md`, `S-1-002.md`, etc., and clues `C-1-0001.md`,
`C-1-0002.md`, etc. Fill in known properties, including each session's number.

## Vault structure

| Folder | Contents |
| --- | --- |
| `world/` | Shared locations, NPCs, factions, lore, and objects. |
| `campaign_1/` | Campaign reference, sessions, clues, PCs, players, transcripts, and campaign-bound entities. |
| `reference/` | External reference material. |
| `templates/` | Page structures to copy and customize. |
| `types/` | Descriptions of page types. |
| `statuses/` | Clue lifecycle states, each linked to the Clue type through `applies_to`. |
| `assets/` | Durable maps, images, and handouts. |
| `.scratch/` | Temporary working material, ignored by Git. |

Entity metadata uses a `campaign_1:` block for that campaign's state. Keep shared
world records in one place and link to them from campaign records. A clue is a
candidate fact; writing it down does not establish it as world canon.

Empty `.gitkeep` files preserve the starter's empty directories in Git. They have
no special meaning to Git or Obsidian and can be removed once a directory contains
other tracked files. You can initialize the copied vault as its own Git repository.

## Live clue views

Active Clues on entities, Sessions on clues, and the campaign clue index use
Dataview queries. Enable the Dataview community plugin in Obsidian to render these
sections as tables. The starter does not install plugins. Ordinary Markdown and
properties remain usable without Dataview.

Evaluated Bases replacements and other follow-on work are tracked in the
[repository issues](https://github.com/willbradshaw/armarium/issues).
