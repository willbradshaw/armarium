# Views

## Setup (each vault)

Use Obsidian **1.13.7 or later** and enable **Bases** in Settings → Core plugins.
Then enable the community plugin **Frontmatter Markdown Links** by **mnaoumov**:

1. Open Settings → Community plugins and turn on community plugins if restricted.
2. Select Browse, search for **Frontmatter Markdown Links**, and select Install.
3. Select **Enable**. Installing alone does not turn it on.
4. In Settings → Appearance → CSS snippets, keep **armarium-prose** enabled.
   It ships enabled in the starter/example vault and makes linked prose flow as
   one paragraph instead of separate flex columns. For an existing vault, copy
   `.obsidian/snippets/armarium-prose.css` and enable it there.

Tested combination: Obsidian 1.13.7 with Frontmatter Markdown Links 3.0.2.
The plugin is required for clickable wikilinks embedded within `text` and `summary`
values. Without it, Bases still shows live tables, but those embedded links can
appear as literal `[[wikilinks]]`. Enable it in every new or copied vault, including
the example vault; plugin code is not bundled with Armarium.

[Plugin details and releases](https://github.com/mnaoumov/obsidian-frontmatter-markdown-links).
The plugin may offer Advanced Rename and Delete Handler; that additional plugin
is not required for these views, and you can choose **Not now**. When renaming
notes referenced inside property prose, check the resulting links. Use full
vault-relative targets when filenames collide (for example,
`[[content/Visitors/Signal Keeper|the visitor]]`). The plugin resolves clicked
links from the open note, so ambiguous short names should be avoided.
 Open the containing note in Reading view to
use its embedded view; opening a `.base` directly has no containing-note context.

## Live views

- **Clue index:** Active is Pending/Hinted; Closed is Revealed/Abandoned/Dormant/
  Superseded. Sorted by ID. Its containing `campaigns/campaign_N/` folder sets scope.
- **Content → Active Clues:** scope follows the Content note’s location. World-level
  `content/` items show active clues from all campaigns; items inside
  `campaigns/campaign_N/` show only that campaign. Subfolders inherit the same
  scope. Only canonical `subjects` and active status select Clues; no selector
  property is needed. Clues must be directly in a campaign’s `clues/` folder.
- **Clue → Sessions:** the Clue's folder selects the campaign. Only Session records
  directly in its `sessions/` folder with the matching campaign link appear,
  ordered by date, numeric session number, then filename. A mention in preparation
  or Events counts as a reference; it does not prove an appearance. Nested
  Transcripts are excluded.

All views are tables, preserving the original columns and their order:

| View | Columns |
| --- | --- |
| Active/Closed Clue index | ID, Status, Last Session, Text |
| Content Active Clues | ID, Text |
| Clue Sessions | Session, Date |
| Preparation Secrets & Clues | ID, Text |
| Preparation Locations | Location, Description |
| Preparation Important NPCs | Name, Summary |

Session number is a sort tie-breaker, not a displayed column. Prose tables use compact two-line rows; very long values may still be clipped.
Open the source record for the full value, or increase the row height in the view
settings. Text, Description and Summary are read-only displays of the same
canonical fields; edit these fields in the source note. This avoids the plugin
spreading editable prose fragments across the height of a cell. Frontmatter Markdown Links makes wikilinks inside Text, Description and Summary
cells clickable. The ID, status and Session link cells use native Bases links. Candidate facts remain
candidates even when displayed on a Content page. Missing or unknown statuses
appear in neither index; fix the source rather than treating them as active.

Source and selection edits update the tables live. Preparation reads current
canonical values even when viewing a past Session; record historical facts in
Events or Scene notes when they need to remain fixed.
Editing an editable property such as Status changes the canonical note.
Keep campaign records directly in their prescribed folders. For another campaign,
copy the index into its `reference/indexes/` folder; the same Bases definitions work.
Clue templates get scope when moved to `campaigns/campaign_N/clues/`.

## Preparation

In Session Properties, edit the ordered link lists `prepared_clues`,
`prepared_locations` and `prepared_npcs`. In Source mode these are YAML lists:

```yaml
prepared_clues: ["[[campaigns/campaign_1/clues/C-1-0001]]"]
prepared_locations: ["[[content/Port Briselle]]"]
prepared_npcs: []
```

List order is display order. Use the link picker, or canonical paths when names
collide; display aliases such as `[[content/Port Briselle|the port]]` are fine.
Only explicit selections count. Events-only links never add preparation items.
Locations and NPCs must be matching Content subtypes, shared or in this campaign;
Clues must be from this campaign. Closed Clues remain selectable intentionally.

Preparation uses live Bases tables reading Clue `text` and Content `summary`.
There is no refresh command or generated copy to maintain. An empty selection
shows an empty table. Invalid selections (wrong type/subtype, missing target or
wrong campaign) do not produce rows; use canonical links and the matching subtype.
Duplicate selections produce one row at their first position.

To add/remove preparation, edit the lists. Use Source mode to reorder them.
Removing a selection does not delete Content. To carry forward, create the next
Session from the template and copy only the desired lists. Do not copy previous
Events or Loot. Put instructions and session-specific variations in Scene notes,
not in source summaries. Edit preparation text and summaries in their source notes.
