# Issue #25 evaluation

## Current revision: tables with original columns

All replacement views now use tables. Their displayed fields, labels and column
order match the original Dataview queries and preparation tables at `33e18f3`:

| View | Columns |
| --- | --- |
| Active/Closed Clue index | ID, Status, Last Session, Text |
| Content Active Clues | ID, Text |
| Clue Sessions | Session, Date |
| Preparation Secrets & Clues | ID, Text |
| Preparation Locations | Location, Description |
| Preparation Important NPCs | Name, Summary |

Session number remains only a sort tie-breaker. No Status column is added to
Content Active Clues. The source values and filtering contracts are unchanged.
Clue text tables use extra-height rows; very long values may still be clipped.
The source record remains available through its link. Inline wikilinks inside
Bases text fields remain literal; preparation Markdown renders them as links.

**Current verification:** 19 deterministic tests pass, including comparisons of
fields/labels/order against every inventoried original query, and preparation
headers against the original Session template and records. Checks cover refresh,
staleness, conflicts, canonical selections, ordering, carry-forward, aliases,
duplicate basenames, all statuses, symlinks, escaped pipes, preserved user notes
and Events/Loot. Shared reference trees are identical; the vault audit finds zero
runtime Dataview uses; `git diff --check` passes.

**Revised table rendering is not yet rechecked in Obsidian.** The user requested
no focus stealing, so no foreground test was run for this revision. Historical
list-view results below must not be represented as validation of the new tables.
Outdated screenshots were removed from the PR.

The review copy is on the user's Desktop under
`Armarium PR 30 Review/Crownless Coast`. Review changes are applied only to files
that still match the previous PR copy, preserving any independent review edits.

## Historical in-app evidence (commit `54438df`)

On 2026-09-22, actual starter/example copies were opened under
`/private/tmp/armarium25-review/` with an isolated Obsidian profile. The launcher
was 1.12.7; the complete run used **Obsidian 1.13.7**, Bases enabled and no community
plugins enabled. Python 3.9.6 / PyYAML 6.0.3 ran the fallback checks; Node 22.18.0
ran the separate UI harness. Personal vault settings were not modified.

- [Per-use inventory](inventory.json): 42 original uses (28 blocks and 14 inline
  expressions), replacements and current verification status.
- [Historical rendered DOM](evidence/rendering.json): all 31 containing notes and
  templates, runtime plugin states, expected original rows and synthetic checks.
  The index/Content views in this evidence were **lists**, with subsequently
  corrected column choices. Its long-text wrapping claim does not apply to tables.
- [Historical native editing/navigation](evidence/editing.json): removing a pill,
  adding a selection with input + Enter, preserved preparation/Notes, and clicking
  a link embedded in a canonical summary. Generated header labels have since been
  restored to the original names.

The synthetic fixture includes six statuses in each of two campaigns, duplicate
Content basenames, display/YAML aliases, shared Content, empty states, multiline
and long text, tied Session dates, reversed preparation order, nested Transcript
and Session-shaped decoys, and an Events-only NPC. It is not a narrative second
campaign and does not depend on PR #29.

Filtering, campaign isolation, canonical subjects, date/number ordering, explicit
selection order and source-link navigation passed in that run. Source text and
nonempty changes updated live. The **former list layout** could retain a stale row
under “0 results” after removing the last match; reopening the note cleared it.
The raw evidence preserves that limitation. It is not a finding about the current
table layout.

Preparation stayed unchanged after a canonical summary edit, then updated in the
open Session after explicit refresh. A second run reported `Current`. Notes,
Events and Loot stayed byte-identical. UI selection changes did not silently
rewrite snapshots. A link inside a generated summary opened its canonical file.

## Repeatable checks and manual table review

From the repository root, install `tools/requirements-views.txt` in a temporary
Python environment, then run:

```sh
python3 -m unittest discover -s tests -v
```

For a new disposable fixture:

```sh
python3 tests/views/build_review.py /private/tmp/armarium25-review
```

The destination must not already exist. For manual review, open each generated
folder as a vault, enable core Bases and disable all community plugins. Record
the app version, then:

1. Check starter Content/Clue/Session templates and its Clues index are empty tables.
2. Check every table's headers and order against the column matrix above. Check
   ID/status/Session link cells navigate, and inspect long Text cells at normal
   window width. Record any clipping instead of claiming full visibility.
3. In each campaign's synthetic index, `9001/9002` are active and `9003–9006` closed.
   Original campaign 1 active rows are `0003/0004`, closed rows `0001/0002`.
4. Switch `content/Review/Signal Keeper` between campaigns using `view_campaign`:
   only that campaign's `9001` appears. The duplicate under `Visitors/` gets `9002`;
   `Empty` gets none. Edit text, all six statuses and subjects, including removal
   of the final match. Check actual table refresh behavior without assuming the
   former list-view behavior applies.
5. Each campaign's `C-N-9001` must show Sessions `902, 903, 901`, with no nested or
   cross-campaign records. Only Session and Date are displayed.
6. In `S-1-901`, Clues are `Second, First` and NPCs `Visitor, Keeper`. Check full
   preparation text and embedded links. `Events Only` must not be selected. Use
   Properties to add/remove and Source mode to reorder selections; edit canonical
   text/summary, refresh, and confirm changes without altering Notes/Events/Loot.
7. Create a new Session from the template; copy only desired selection lists and
   refresh. Past Events and Content files must remain unchanged. Edit a generated
   region and check refresh refuses it without partial writes.

The optional `tests/views/observe.mjs`, `check_rendering.mjs` and `check_editing.mjs`
use local CDP and private UI APIs. They target only the exact disposable root above.
A test profile uses `--remote-debugging-port=9225`; Node 22 runs the harnesses:

```sh
ARMARIUM_PYTHON=/path/to/python node tests/views/check_rendering.mjs /private/tmp/view-evidence
mkdir -p /private/tmp/armarium25-edits
node tests/views/check_editing.mjs
```

They no longer capture screenshots automatically or request window focus by
default. Set `OBSIDIAN_ALLOW_FOCUS=1` only for an explicitly agreed foreground
session. Background capture may be incomplete because Obsidian virtualizes hidden
content. An unmounted view is not evidence of successful rendering.

## Outstanding review and integration

The explicit-refresh preparation tradeoff still needs user review, and final
integration into #24's installable package remains part of #25. This draft does
not close the issue. No #24 package branch/PR was available during implementation.
Move the bounded single-Session refresher into that same package/parser/resolver,
retain checksum ownership, atomic replacement and stale/conflict behavior, verify
installed-wheel operation outside the checkout, then remove the temporary harness
entry point/dependency file and update instructions. No competing package,
validator or Obsidian plugin was introduced.

PR #20 was inspected for Base filters, ordered selection and checksummed-region
ideas. Its obsolete NPC/Location types were reconciled with current Content
subtypes; campaign/index scope derives from paths. Its evidence was not used as
validation for this implementation.

For #22 / PR #28, Content `view_campaign` is a display string, not a campaign claim.
Session's three ordered link arrays allow `[]` and require canonical uniqueness,
correct Content subtypes and same-campaign Clues. Content schemas allow custom
fields. Canonical `text`, `summary`, subjects, statuses and histories are unchanged.
Shared type-reference edits require reconciliation at central review.
