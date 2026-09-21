# Armarium

A system-general starter for tabletop roleplaying knowledge bases in Obsidian.

## Create a vault

From this checkout, copy `vaults/starter/` to a new folder whose parent exists:

```sh
vault_path="../my-setting"
mkdir "$vault_path" && cp -R vaults/starter/. "$vault_path/"
```

Open the new folder in Obsidian and edit
`campaigns/campaign_1/reference/Campaign.md`. The copy includes hidden files;
`mkdir` prevents copying over an existing destination.

## Explore the example

Copy `vaults/example/` in the same way to explore **The Third Bell**, an original
swashbuckling campaign on the Crownless Coast. Open its
`campaigns/campaign_1/reference/Campaign.md` for the cast, setting and sessions.

Shared setting pages describe the coast, harbor, reefs, pilots' assembly and local
customs. One campaign adds a crew escaping a disputed ship seizure: two played
sessions, a prepared third session, an attributed transcript excerpt and a handout.
The records show every Content subtype, individual and collective possession,
a consumed object, and Pending, Hinted, Revealed and Abandoned Clues. The unvisited
reefs have no campaign-history block; prepared events and unrevealed Clues remain
separate from established setting facts.

Both vaults include the same templates, type/status references and Content schema.
Each vault is self-contained; copying the example does not depend on the starter.
The fictional players and all setting/session material are original sample data.

## Layout

| Folder | Purpose |
| --- | --- |
| `content/` | Shared setting content. |
| `campaigns/campaign_1/` | Campaign content, clues, sessions, and reference material. |
| `reference/` | Templates, type descriptions, schemas, statuses, and shared reference material. |
| `assets/` | Maps, images, and handouts. |

Copy a file from `reference/templates/` to create a record. See the corresponding
reference for its fields and conventions:
[Content](vaults/starter/reference/types/Content.md),
[Clue](vaults/starter/reference/types/Clue.md),
[Session](vaults/starter/reference/types/Session.md),
[Player](vaults/starter/reference/types/Player.md), or
[Transcript](vaults/starter/reference/types/Transcript.md).

Enable Obsidian's Dataview community plugin to render the included Clue views.
The supplied links and queries target campaign 1.

`.scratch/` is ignored working space; `.gitkeep` files preserve empty directories
in Git. The copied vault can be its own Git repository.

Planned work is tracked in the [issues](https://github.com/willbradshaw/armarium/issues).
