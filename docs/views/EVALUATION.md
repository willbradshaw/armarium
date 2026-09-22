# Issue #25 evaluation

## Current implementation

All 42 inventoried Dataview uses are replaced by live Bases tables. Enable core
Bases and **Frontmatter Markdown Links** by **mnaoumov** in each vault. Tested:
Obsidian **1.13.7**, Frontmatter Markdown Links **3.0.2**. Plugin installation and
activation are documented in both the root README and the copied vault's
`reference/views/README.md`. No community-plugin code is bundled in the repository.

Preparation reads canonical Clue `text` and Content `summary`, filtered by explicit
ordered `prepared_clues`, `prepared_locations` and `prepared_npcs` selections.
A hidden formula sorts by the first matching selection position. Source edits and
selection changes update live; no generated Markdown, checksums, refresh command,
Python runtime dependency or retained snapshots remain in either vault.

| View | Columns, in original order |
| --- | --- |
| Active/Closed Clue index | ID, Status, Last Session, Text |
| Content Active Clues | ID, Text |
| Clue Sessions | Session, Date |
| Preparation Secrets & Clues | ID, Text |
| Preparation Locations | Location, Description |
| Preparation Important NPCs | Name, Summary |

Session number remains a sort tie-breaker only. No Subjects or Status column has
been added to Content Active Clues. Canonical fields, Events and Loot are preserved.
Invalid preparation selections are excluded rather than rendered: missing records,
wrong types/subtypes and wrong campaigns. Duplicate selections produce one row.

## Verification

[Current background integration evidence](evidence/live-tables.json) records real
Bases controllers in the already-open disposable `armarium25-starter` vault under
`/private/tmp/armarium25-review/`. The synthetic example fixture was copied into
that disposable vault. Tables were mounted transparent and noninteractive so the
actual virtualized cells could render. The harness does not open notes, change
active tabs, show or focus windows, or take screenshots. Link navigation is
intercepted at `openLinkText`, recording its actual target without changing tabs.

**29 background integration checks passed.** They cover:

- Actual table headers match the original Dataview fields, labels and order.
- Wikilinks within property prose render with their aliases and invoke internal
  navigation, including fully qualified targets with duplicate basenames.
- Rendered short-prose rows stay compact and successive lines have normal spacing.
  Text/summary formulas read the same canonical fields but avoid nested editable
  property widgets, whose flex layout stretched prose fragments vertically.
- Canonical Clue text and Content summaries change in mounted tables without a
  manual refresh, query reset or reopening the note.
- Preparation selection reordering, removal of the last selection, duplicate
  selections and missing/wrong-type/cross-campaign exclusions.
- Content campaign switching and removal of its final matching subject.
- All six statuses, active/closed index scope, and explicit preparation of closed
  Clues. Events-only links do not add preparation records.
- Session date/number ordering; cross-campaign and nested Transcript/Session
  decoys excluded.
- Empty Session template tables and all three real example Sessions' preparation.
- Notes/Events/Loot and the active tab stay unchanged during the tests.

Four deterministic repository tests compare every original block's columns and
all original preparation headers against the new Bases; check shared reference
parity; reject remaining runtime Dataview/snapshot artifacts; and compare example
Notes/Events/Loot byte-for-byte with `33e18f3`.

## Repeatable checks

Python is needed only for repository tests and fixture construction, not vault use:

```sh
python3 -m venv /private/tmp/armarium-views-venv
/private/tmp/armarium-views-venv/bin/pip install -r tests/requirements-views.txt
/private/tmp/armarium-views-venv/bin/python -m unittest discover -s tests -v
/private/tmp/armarium-views-venv/bin/python tests/views/build_review.py NEW_DIRECTORY
```

For background integration, use a disposable vault under the exact
`/private/tmp/armarium25-review/` root, with the example fixture contents, named
`armarium25-starter`. Enable core Bases and install/enable Frontmatter Markdown
Links 3.0.2 there. A Bases embed must already be loaded in the active Reading-view
note. The isolated Obsidian profile must expose CDP on port 9225. Then:

```sh
ARMARIUM_PYTHON=/private/tmp/armarium-views-venv/bin/python \
  node tests/views/check_live_tables.mjs /private/tmp/live-tables.json
```

The harness rejects other vault roots. It restores changed fixture notes and
unloads its test controllers even on failure. Plugin installation/enabling is an
explicit prerequisite; fixture generation does not download or enable plugins.

## Limits and review

- Compact two-line native table rows can still clip very long prose. Open the linked
  source record for its full value. These DOM checks do not establish visual
  appearance at every window width, theme, or mobile device size.
- This plugin renders embedded links; it is not a general Markdown renderer for
  arbitrary formatting in properties. Without it, embedded wikilinks can remain
  literal text even though Bases filtering and updates still work.
- The plugin's click handler uses the open note as source context. Use full
  vault-relative targets for ambiguous basenames; short ambiguous names are not
  made safe by this implementation. Rename handling is owned by Obsidian or an
  optional separate plugin, not by Armarium.
- Past Sessions now display current canonical preparation text. Historical facts
  belong in Events/Scene notes. The user explicitly rejected frozen snapshots.
- Community-plugin internals can change across Obsidian updates. Recheck this
  tested combination before raising supported versions.

The Desktop review copy is `Armarium PR 30 Review/Crownless Coast`. Updating it
preserves independent edits by replacing only files still matching the previous
PR copy. The plugin must also be enabled in that review vault.

## Superseded experiments

Historical list/snapshot evidence in `evidence/rendering.json` and
`evidence/editing.json` is retained only as an experiment record; it does not
validate the current implementation. Their old UI harnesses and the snapshot
refresher have been removed. [The HTML-formula experiment](HTML-FORMULA.md) failed
internal navigation and is not used. Its separate negative-control harness must
run with community plugins disabled.

PR #20 informed the initial filtering/selection investigation; current tests use
current Content subtypes and canonical fields. There is no production fallback
command to integrate with #24. For #22 / PR #28, `view_campaign` is a display
selector and the three Session selections are ordered link arrays allowing `[]`.
No custom plugin, competing package, or general query framework was introduced.
