# Vault Guide

This folder is an independent setting vault. Open it in Obsidian and start at
[[Home]]. Its world information and campaigns belong to this vault, not to an
Armarium development checkout.

## Start a session

1. Choose a campaign from [[campaigns/Campaigns]].
2. Copy [[templates/Session]] into that campaign's `sessions/` directory.
3. Name it `S-<campaign-id>-001.md` (then 002, 003, ...), set `id` to that
   filename without the extension, `session_number` to the unpadded number,
   and `campaign` to the campaign hub's full wikilink.
4. Read the previous session, carry forward still-relevant unresolved material,
   and fill Preparation. Keep unplayed plans distinct from actual Events.
5. After play, draft and review Events before updating related entity pages.

Dates of play use YYYY-MM-DD. In-game dates are optional: use a convention chosen
for this setting, with no required calendar. Do not assume a game has XP, levels,
classes, or spellcasting. Encounters and rewards are deliberately system-general.

## Where things go

| Area | Purpose |
| --- | --- |
| `world/` | Shared, established setting entities: locations, NPCs, factions, lore, objects. |
| `campaigns/<id>/` | Sessions, transcripts, PCs, players, clues, and campaign-bound entities. |
| `reference/` | Rules and source records; these do not establish campaign events. |
| `templates/` | User-owned page structures. |
| `bases/` | Integration point for evaluated live views; this starter requires none. |
| `assets/` | Durable, visible maps, images, and handouts suitable for embedding. |
| `.input/unprocessed/` | Incoming recordings, raw transcripts, and source documents. |
| `.input/processed/` | Inputs already handled; do not delete them without an explicit retention decision. |
| `.scratch/` | Temporary drafts, extracted beats, and review checklists. |

Input and scratch folders are Git-ignored and may need recreating after cloning.
This is not a deletion policy or a backup. Retain originals until the GM decides
otherwise. Do not store the only durable copy of a handout in a hidden folder.

Decide entity scope by intended reuse. A building can be world-level; a city can
have campaign-specific records. Avoid copying a shared entity just because another
campaign encounters it.

## Page identity and links

Use canonical names for entity filenames. Session and clue IDs include a campaign
ID: `S-<id>-001` and `C-<id>-0001`. Campaign IDs are immutable lowercase
letters/digits with optional internal hyphens, not display names.

Every entity has a quoted type link to a page in `types/`. Bare empty metadata
means unknown/null; `[]` means an empty list and `{}` an empty mapping. Clue
`text` starts as an empty string. These are distinct values, not interchangeable
placeholders.

Always link to a canonical target. Full vault-relative paths are preferred when
names collide, especially type pages, templates, and campaign-specific entities.
Use explicit display aliases when useful and escape their pipes inside Markdown
tables. Rename duplicate names with a meaningful qualifier or use their full paths;
do not let an agent guess which page a bare link means.

A minimal stub is acceptable when details are unknown. Do not fill it with invented
history. Keep one canonical home for facts and link to it.

## Entity structure and shared history

NPCs, PCs, locations, factions, lore, and objects share Notes, Active Clues, and
Appearances. Put durable knowledge in Notes and stable identity in `summary`.
Date changing world facts rather than treating one campaign's present as universal.

Per-campaign state uses a `campaigns` mapping on both shared and campaign-bound
entity pages. Its keys are the IDs from `armarium.json`, quoted if numeric:

```yaml
campaigns:
  "1":
    first_session: "[[campaigns/1/sessions/S-1-001]]"
    last_session: "[[campaigns/1/sessions/S-1-003]]"
    held_by:
```

The example above illustrates syntax, not links to starter content. Add only the
fields appropriate to the type: `held_by` is for objects. Leave `campaigns: {}`
until there is state to record. Adding campaign state here never means the other
campaign's history should be replaced.

Under Appearances, use a separate third-level heading per campaign (include its
ID), with chronological linked session bullets. Log actual interactions: an NPC
on stage, a place visited, an object used, or collective faction action. Incidental
mentions remain discoverable through backlinks. PC logs record noteworthy
contributions, not attendance alone.

Session loot is a historical acquisition record. Current possession is separate:
use `held_by` with an explicit PC/NPC/place link when known. For shared party
possession, add an explicit `holder_scope: party` in that campaign block; leave
`held_by` bare. A bare holder without that scope means unknown/no named holder.
These metadata fields do not require a general inventory system.

## Clues and preparation

A clue is a persistent GM-known candidate fact not fully known to players. Its
existence in prep does not make it canon, and an abandoned clue may never become
true. Generic questions and unresolved tasks can stay in the campaign's Open
threads section.

Keep canonical clue text in `text` and list its canonical entity links in
`subjects`, with duplicates removed. Use [[statuses/Pending]], [[statuses/Hinted]],
[[statuses/Revealed]], [[statuses/Abandoned]], [[statuses/Dormant]], or
[[statuses/Superseded]]. The first two appear in active clue indexes; the rest are
closed for preparation purposes. Status changes are GM decisions.

Clue `first_session` records first preparation or introduction, unlike an entity's
first actual appearance. Its `last_session` records its latest relevant play.
When revealed, incorporate established facts into substantive subject pages with
a link back to the clue. Keep unrevealed candidates out of world Notes. Preserve
already-established facts when retiring a clue.

Session `prepared_npcs`, `prepared_locations`, and `prepared_clues` hold explicit
lists of canonical links. They distinguish preparation from incidental references
in Events. The starter's tables are manual presentation space for links and
session-specific prep; do not copy source summaries or clue text into them. Live
displays are a separate deliverable described in [[bases/Views]].

## Ownership and tooling

`armarium.json` records the setting, campaign IDs/paths, starter version, and the
source starter's content hash. The hash records provenance, not a restriction on
editing these files. Templates, instructions, views, and content are yours to edit.

The toolkit repository reference is portable; `revision: null` explicitly means
that a shared runtime has not been configured. This basic installer copies no
utility scripts or shared skills and creates no machine-specific pointers.
Host skill discovery, version pinning, updates, and migrations are later steps.
The vault remains readable after moving it or removing the Armarium checkout.

Initialize Git here if desired. Keep this vault's repository separate from
Armarium's. When using Git for agent-assisted work, use branches and reviewed PRs.
Raw recordings and scratch work are ignored by default; review what you publish.
