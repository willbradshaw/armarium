# Issue #25 evaluation

Evaluated 2026-09-22 from main after PR #23 (`33e18f3`). This is a reviewable
implementation, **not closure of #25**: the explicit-refresh preparation tradeoff
is still under user review, and final integration into the #24 package is pending.
No #24 package branch/PR was available when inspected. Do not merge a competing
package or call the temporary harness final package integration.

## Results

| Required case | Implementation and result | Remaining limitation |
| --- | --- | --- |
| Campaign Active/Closed Clue indexes | Reusable `clue-index.base`; actual rendered rows match all six statuses, ID ordering and each of two campaign folders. List view wraps long text. | Inline wikilinks inside text remain literal; ID/status/last Session links are usable. |
| Content Active Clues | `content-clues.base`; canonical subjects, display aliases, duplicate basenames, live text edits and `view_campaign` switching passed. | Obsidian 1.13.7 can retain a stale row when the result changes to empty; reopen the containing note. |
| Sessions referencing a Clue | `clue-sessions.base`; exact Session folder, canonical type, campaign link and backlink; date/number/filename ordering. Both campaigns passed, with nested Transcript and nested Session-shaped decoys excluded. | References include preparation/Events; they are not a claim that an appearance occurred. |
| Preparation | Checksummed generated Markdown from three explicitly ordered `prepared_*` lists. Full long text and embedded links render; native Properties add/remove controls and link navigation passed. Source/selection edits require explicit refresh. | User tradeoff review and #24 package integration remain open. No automatic stale detection in Obsidian. |

No community plugins were enabled in either review vault. Core Bases is the only
view-specific plugin requirement. The fallback harness requires Python 3.9+ and
PyYAML; testing used Python 3.9.6 / PyYAML 6.0.3 and Node 22.18.0 for the separate
UI observation harness. No custom Obsidian plugin, validator, directory roster,
private reference project, agent service or model credential is required.

## Inventory and evidence

[inventory.json](inventory.json) records all **42 original runtime uses** (28
blocks, 14 inline expressions), their source locations, replacement and per-file
rendering verification. Both root README enablement instructions and the two
shared Session references were updated. The final hidden-file-inclusive audit of
both vaults found zero Dataview blocks, inline expressions or enablement references.

The actual copies were `/private/tmp/armarium25-review/armarium25-starter` and
`.../armarium25-example`, opened in an isolated Obsidian profile. The installed
launcher was 1.12.7; its list-view probe already showed literal inline wikilinks.
The profile updated to **Obsidian 1.13.7**, which was used for the complete
production-view evaluation. Personal vault settings were not modified.

- [Rendered DOM and checks](evidence/rendering.json): all 31 containing notes,
  including templates and blank starter views, with explicit expected rows for
  each example Content page, Clue and index. Runtime plugin states are recorded
  separately for each vault. Eighteen check records include two explicit reopen
  limitations, not eighteen claims of uninterrupted live refresh.
- [Native Properties editing and navigation](evidence/editing.json): remove via
  the pill's x, add via input + Enter, resulting ordered YAML, preservation of
  preparation/Notes, and clicking a wikilink embedded in a canonical summary.
- [Long Clue text](evidence/content-clues.png),
  [rendered preparation](evidence/preparation.png),
  [selection controls](evidence/selections.png): screenshots of actual Obsidian
  Reading view. The screenshot with long preparation text shows the terminal
  `LONG_TEXT_END` marker and clickable embedded links.

The synthetic records live only in disposable copies. They include six statuses
in each campaign, two Content records with the same basename, display/YAML aliases,
shared Content, an empty Content view, multiline and long source fields, tied
Session dates, reversed preparation order and an Events-only NPC. They are not a
second narrative example campaign and do not depend on PR #29.

### Refresh behavior actually observed

Text edits, campaign display switching and nonempty status changes updated without
reopening. When a status or subject edit removed the last match, Bases displayed
“0 results” but retained its old list row. Waiting longer did not fix it. Opening
another note and returning cleared the row and produced the expected empty state.
The evidence retains the stale and reopened captures. This is documented for users;
it must not be represented as a fully live empty-state transition.

Preparation deliberately stayed unchanged after a canonical summary edit. Running
the refresher updated the source text and selection in the already-open Session
without reopening; a second run reported `Current`. Actual Notes/Events/Loot were
byte-identical. The native Properties UI edits changed selections without silently
rewriting snapshots. A generated summary link was clicked and opened its canonical
Location file.

## Deterministic checks

Run from the repository root, with the harness dependency installed:

```sh
python3 -m unittest discover -s tests -v
```

**17 tests pass.** Contracts include canonical source edits, read-only stale checks,
repeatability, intentional ordering, add/remove/carry-forward, all six statuses as
explicit preparation selections, empty lists, aliases versus canonical identities,
ambiguous basenames, wrong types/campaigns, duplicate selections/YAML keys,
symlinks, edited or misplaced ownership markers, escaped table pipes, preserved
user notes and historical Events/Loot. The historical-preservation test uses the
base commit in this repository. Shared reference trees are byte-identical.

These tests are reported separately from the in-app checks. They do not prove
Obsidian rendering. `git diff --check` also passes.

## Reproducing or manually reviewing

1. Install `tools/requirements-views.txt` in a temporary Python environment. Run
   `python tests/views/build_review.py /private/tmp/armarium25-review` with a **new**
   destination (the builder refuses an existing directory).
2. Open both generated vault folders in Obsidian. Confirm Settings → Core plugins
   → Bases is on, and Settings → Community plugins has no enabled plugins. Record
   the app version. Do not use a personal vault for these exercises.
3. Starter: open `reference/templates/Content`, `Clue`, `Session` and the campaign
   Clues index. Check empty views/tables and absence of query errors.
4. Example: open the campaign 1 Clues index and then campaign 2's synthetic index.
   Synthetic `9001/9002` are active; `9003–9006` are closed. Campaign 1 additionally
   has original active `0003/0004` and closed `0001/0002`. Scroll long text through
   `CLUE_TEXT_END`, and click an ID/status link.
5. Open `content/Review/Signal Keeper`. Switch `view_campaign` between campaigns;
   only that campaign's `9001` appears. The duplicate under `Visitors/` gets `9002`.
   `Empty` gets none. Edit the Clue text, all six statuses and subjects; check live
   changes and the documented last-row reopen requirement.
6. Open each campaign's `C-N-9001`. Sessions must be ordered `902, 903, 901` (date
   first, numeric Session order for the tie), with no cross-campaign/nested records.
7. Open `S-1-901`. Check Clues `Second, First` and NPCs `Visitor, Keeper`, full long
   summaries, multiline Location text and clickable links. `Events Only` must not
   appear in preparation. Add/remove links in Properties; reorder the YAML list
   in Source mode. The snapshot stays unchanged until refresh. Edit source `text`
   and `summary`, refresh, and confirm the changes and preserved Notes.
8. Copy the Session template to a new Session, set its campaign/number, carry forward
   only desired selection lists and refresh. Old Session Events and Content files
   must remain untouched. Edit inside a generated table and verify refresh refuses
   it without changing any other region; move edits to Scene notes and restore the
   region from history to recover.

The optional `tests/views/observe.mjs`, `check_rendering.mjs` and `check_editing.mjs`
harnesses use local Chrome DevTools Protocol, Node 22 and private Obsidian UI APIs.
Launch a disposable Obsidian profile with `--remote-debugging-port=9225`, then run:

```sh
ARMARIUM_PYTHON=/path/to/python node tests/views/check_rendering.mjs /private/tmp/view-evidence
node tests/views/check_editing.mjs
```

The harness validates the review-vault name/path before manipulating it. Its
scripts use the exact temporary root above. `check_editing.mjs` writes to
`/private/tmp/armarium25-edits/` (create that output directory first). Foreground
rendering can require a visible window because Obsidian virtualizes offscreen
content. **The harness no longer requests window focus by default.** Set
`OBSIDIAN_ALLOW_FOCUS=1` only during an explicitly agreed foreground test session.
Background capture may be incomplete; do not interpret an unmounted view as proof
of successful rendering. No further foreground testing is needed for the recorded
run. The user requested that subsequent work not steal focus.

## Reuse and integration points

PR #20 was inspected via GitHub and its source branch. Reused ideas: context-aware
Base filters, explicit ordered preparation selections and checksummed bounded
Markdown. Its prior 1.13.7 evidence was not counted as testing this implementation.
The obsolete `types/NPC`, `types/Location`, Clue `campaign`, and repeated
`view_campaign` properties were reconciled with current conventions: NPC/Location
are Content subtypes; Clue/index scope comes from paths; only shared Content needs
a display selector. List views replace the prototype's clipped long-text tables.

For #22 / PR #28: `view_campaign` is a Content display string, not a campaign claim.
Session gains three ordered link arrays, allowing `[]`, with canonical-target
uniqueness, correct Content subtypes and same-campaign Clues. Content schemas already
allow custom fields. Canonical `text`, `summary`, `subjects`, statuses and history
semantics do not change. The shared Session/Content/Clue type-reference edits will
need reconciliation with the schema PR.

For #24: move the bounded refresh implementation and tests into the **same**
installable package/CLI and use its parser/resolver once reviewed. Keep the
single-Session operation, atomic replace, checksummed ownership, stale `--check`
exit codes and conflict protection. Then test an installed wheel from outside the
checkout and vault, remove the temporary standalone entry point/dependency file,
and update the usage instructions. This work intentionally creates no package,
validator or competing CLI distribution. **That final integration is outstanding
and remains part of #25, not a completed follow-up.**
