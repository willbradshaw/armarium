# Views

Enable **Bases** in Settings → Core plugins (tested in Obsidian 1.13.7).
No community plugin is required. Open the containing note in Reading view to
use its embedded view; opening a `.base` directly has no containing-note context.

## Live views

- **Clue index:** Active is Pending/Hinted; Closed is Revealed/Abandoned/Dormant/
  Superseded. Sorted by ID. Its containing `campaigns/campaign_N/` folder sets scope.
- **Content → Active Clues:** set `view_campaign` in Properties to `campaign_1`,
  `campaign_2`, etc. This is a display choice, not ownership or campaign history.
  Only canonical `subjects` and active status select Clues. Shared Content stays
  in one file; switching the display does not change either campaign's history.
- **Clue → Sessions:** the Clue's folder selects the campaign. Only Session records
  directly in its `sessions/` folder with the matching campaign link appear,
  ordered by date, numeric session number, then filename. A mention in preparation
  or Events counts as a reference; it does not prove an appearance. Nested
  Transcripts are excluded.

Clue lists wrap long text. Click the ID to open the canonical source; status and
Session properties are navigable links. Wikilinks *inside* a Bases text field
remain literal text. Use the source note to follow these links. Candidate facts
remain candidates even when displayed on a Content page. Missing or unknown
statuses appear in neither index; fix the source rather than treating them as active.

Source edits to text, status or subjects update live, with one observed Obsidian
1.13.7 list-view limitation: removing the last matching row can leave a stale row
below “0 results.” Open another note and return to clear it. Trust neither that
leftover row nor its old status. Views showing no matches are valid empty states. Editing a Clue through a view edits its canonical note.
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

Preparation uses **explicitly refreshed Markdown snapshots**, because Bases text
cells do not render embedded wikilinks. The authoritative values remain Clue
`text` and Content `summary`. After editing a source or selection, refresh the
chosen Session before relying on preparation. Old output remains visibly labeled
as a snapshot until refreshed; there is no automatic stale badge or background job.
A finished Session can retain its old snapshot deliberately. Refreshing an old
Session updates preparation only, never Events, Notes or Loot.

The temporary repository harness requires Python 3.9+ and PyYAML:

```sh
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements-views.txt
.venv/bin/python tools/refresh_preparation.py /path/to/vault campaigns/campaign_1/sessions/S-1-001.md
```

Run those commands from the Armarium checkout (not from the copied vault).
`--check` performs a read-only comparison: exit 0 means current, 1 means stale,
2 means invalid input or a conflict. Package/CLI integration is pending issue #24;
this harness is not a second installable package and is not copied into vaults.

To add/remove preparation, edit the lists and refresh. Removing a selection does
not delete Content. To carry forward, create the next Session from the template,
copy just the desired lists, then refresh. Do not copy previous Events or Loot.
Put instructions and session-specific variations in Scene notes, not in source
summaries or generated tables.

The refresher owns only the three checksummed regions inside Preparation. Keep
ownership comments intact. It validates all regions and selections before writing
and refuses changed generated text, duplicate selections, missing/ambiguous links
and wrong types/campaigns. There is no force option: move deliberate edits to Scene
notes, restore the generated region from history, then refresh. Edits outside the
regions are preserved byte for byte. It checks for concurrent source/Session edits
and replaces the Session atomically; avoid editing the Session while refreshing
(the final check and replacement are not a filesystem lock).
