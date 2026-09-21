# Bases prototype

Original, disposable two-campaign experiment for [issue #5](https://github.com/willbradshaw/armarium/issues/5).
The production starter is unchanged. See [evaluation and recommendations](EVALUATION.md)
and the captured Obsidian evidence in [evidence/](evidence/).

## Run

From the repository root, with Python 3.9 or later:

```sh
python3 -m venv examples/bases-prototype/.venv
examples/bases-prototype/.venv/bin/pip install -r examples/bases-prototype/requirements.txt
examples/bases-prototype/.venv/bin/python examples/bases-prototype/prototype.py build /tmp/armarium-bases-demo
```

The destination must not exist. Open that directory using Obsidian's **Open
folder as vault**, open `Start.md`, and switch to **Reading view**. Core Bases
is enabled by the generated configuration; no community plugins are installed
or enabled. Do not enable Dataview for this experiment. The copied starter's
unused templates still contain the Dataview baseline.

Follow the links in Start. Each campaign index embeds Active and Closed views.
Keeper Mira and visiting Mira share a basename but have different canonical
paths. Keeper Mira's `subjects` link has an alias. Empty has no Clues. Both
campaigns contain all six statuses. Sessions 1 and 2 share a date to exercise
the session-number tie-break; session 3 has empty prep but an Events reference.
Campaign 2's session also references a campaign 1 Clue in Events to test exclusion.

The `.base` files are reusable **embeds**. Opening them standalone does not supply
the containing note's `this` context. A shared entity's `view_campaign` selects
`campaign_1` or `campaign_2`; it is display context, not ownership. The two
top-level campaign state objects remain separate. Only Pending/Hinted count as
active; unknown/missing statuses are not silently active. Clues remain candidate
facts, not established world canon.

## Preparation workflow and fallback

Edit the session's `prepared_npcs`, `prepared_locations`, and `prepared_clues`
link lists in Properties or YAML source. Use qualified links, optionally with
display aliases. List order is preparation order. Remove a link to drop prep;
add it to prepare a page. `Events Only` should never appear unless explicitly
selected. To carry forward, copy just these lists into the next session and
update its date/number. Do not copy Events or delete the selected entity.

Each prep heading shows the live Base followed by a generated Markdown snapshot
for comparison. Source `summary`/`text` properties are authoritative. Refresh a
snapshot explicitly:

```sh
examples/bases-prototype/.venv/bin/python examples/bases-prototype/prototype.py refresh /tmp/armarium-bases-demo campaign_1/sessions/S-1-001
```

Only the three `armarium:prep:*` regions are generator-owned. Write human notes
outside them. The checksum detects hand edits; malformed/missing/duplicate
markers, duplicate selections, missing pages, wrong types, ambiguous/unqualified
links and cross-campaign Clue selections stop refresh without a partial write.
Resolve conflicts by moving human edits outside the region and restoring its
last generated content/marker from version control, then refresh. There is no
force flag. Serialize refresh with editing the session; the final content check
is optimistic conflict detection, not a multi-process lock.

Bases displays stay live, including in old sessions. Fallback tables change only
on refresh. To preserve history, deliberately stop refreshing the completed
session; its selection lists and generated text then document that preparation.
The fallback does **not** meet automatic live refresh or in-table source editing
criteria. Its text is navigable and wraps as Markdown, and its ordering is exact.

Agents need no rendered Base output: read a session's three lists, resolve each
qualified path, and read `summary` (NPC/Location) or `text` (Clue) from that record's
frontmatter. For Clue views, inspect campaign folder/property, status and subjects;
for Sessions, inspect session links, campaign, date and number. Do not treat
generated tables as authoritative, and do not infer prep from all outbound links.
`prototype.py` deliberately implements only prep refresh, not a general query engine.

## Reproduce checks

```sh
examples/bases-prototype/.venv/bin/python -m unittest discover -s examples/bases-prototype -v
examples/bases-prototype/.venv/bin/python examples/bases-prototype/prototype.py build /tmp/armarium-bases-scale --corpus 3000
```

The large fixture adds 3,000 NPCs and 300 active Clues: 90% of synthetic NPCs have
empty Active Clues sections. `Repeated.md` embeds 30 entity sections (3 nonempty,
27 empty). Open it and scroll through the entire note.

For automated **actual app** observations, enable Obsidian's CLI in Settings →
General → Advanced and open each disposable vault first. On macOS:

```sh
python3 examples/bases-prototype/observe.py armarium-bases-demo /tmp/rendered.json
python3 examples/bases-prototype/exercise.py armarium-bases-demo /tmp/edits.json
python3 examples/bases-prototype/benchmark.py armarium-bases-scale /tmp/performance.json
examples/bases-prototype/.venv/bin/python examples/bases-prototype/usability.py armarium-bases-demo /tmp/usability.json
```

The observation scripts use only Python's standard library, except `usability.py`,
which imports the PyYAML-dependent snapshot refresher. `observe.py --cli`
can select another CLI executable; the two other harnesses use its macOS default.
They use private Obsidian UI APIs and DOM selectors, so version upgrades can
require harness changes. `exercise.py` changes disposable records while views
are open, records observations, and restores their original bytes in `finally`.
If forcibly terminated, rebuild a fresh vault before repeating. Run UI harnesses
serially and keep the test window visible; background-window throttling and
Markdown/table virtualization affect both DOM capture and timings.

## Handoff to #17

Generated notes add `view_campaign`; Clues also add a qualified `campaign` link.
Generated Sessions add three ordered `prepared_*` properties and replace only
the contents under the existing three prep headings. Preparation/Notes and all
other headings are preserved. These are prototype conventions, not a redesign
of the canonical multi-campaign schema. Reconcile context and campaign properties
with #13. Both fixtures also pass #6's validator from PR #19 at pinned revision
`f30a60163185754ee1d823ca8fa3a0bd03456245`; see the evaluation for reproduction.
Neither implementation was merged into this branch's main baseline.

For integration, adapt the real templates, choose either live Base or snapshot
prep displays (the side-by-side comparison is experimental), and review the
performance/layout limitations before adding an Active Clues embed everywhere.

Official documentation checked during implementation on 2026-09-21:
[Bases](https://obsidian.md/help/bases),
[syntax and containing-note context](https://obsidian.md/help/bases/syntax),
[functions](https://obsidian.md/help/bases/functions),
[embedding](https://obsidian.md/help/bases/create-base), and
[Table settings](https://obsidian.md/help/bases/views/table).
