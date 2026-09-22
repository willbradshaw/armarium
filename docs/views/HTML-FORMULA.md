# HTML formula experiment

**Result: not a working internal-link replacement in Obsidian 1.13.7.**
The user rejected snapshots and requested a test of a live HTML formula. No
production Base or Desktop review file was changed by this experiment.

The formula uses the documented `html()`, `escapeHTML()`, `replace()` and
`toString()` functions to turn bare/aliased wikilinks into HTML anchors, preserving
prose. It reads `note.text` directly; it does not duplicate source text. Calling
`toString()` matters when the whole property is a wikilink: Obsidian represents
that value as a Link rather than an ordinary String.

[Exact formula and results](evidence/html-formula.json) and
[reproducible test](../../tests/views/check_html_formula.mjs).

| Check | Result |
| --- | --- |
| Bases parser and HTML cell renderer | Accepted the formula and produced anchors. |
| Bare links and aliases | Correct visible labels and `data-href` values. |
| Qualified duplicate basenames | Correct distinct type/template file targets. |
| Heading target / optional `.md` | Preserved target and alias. |
| Literal HTML, ampersands, quotes, multiline text | Escaped; no script or event-handler nodes created. |
| Null field | Empty output. |
| Successive edits to canonical source | Re-evaluation used the new value. This was not a mounted-table automatic-refresh test. |
| Native `link()` positive control in the same Base cell renderer | Click invoked `workspace.openLinkText` with the expected target. |
| HTML `<a class="internal-link" data-href="…" href="…">` | Click did **not** invoke internal navigation. |
| `html("[[file|label]]")` without conversion | Left Markdown literal. |

An initial probe also tried anchors with `data-href` but no `href`; they did not
invoke internal navigation either. Styling an anchor as `internal-link` does not
attach the click handler that Obsidian gives native Link values. A normal relative
HTML `href` is not evidence of vault-aware navigation, rename handling or hover
behavior. The formula therefore cannot be presented as a working wikilink fix.

Testing ran entirely in the already-open disposable `armarium25-starter`, using
Obsidian's actual Base query parser and actual table-cell renderer. Temporary DOM
was hidden inside an existing Base. A temporary source note was created, edited
and removed. Navigation was intercepted to observe the internal handler without
opening notes; browser default navigation was also prevented. No window was
opened or focused, and the user's Desktop review vault was not touched. This is
an engine/DOM/click-handler test, not a claim of visual layout verification.

To reproduce with the original disposable starter and its Base controller loaded:

```sh
node tests/views/check_html_formula.mjs /private/tmp/armarium25-html.json
```

The test fails if a future app version begins handling these HTML links; that is
a signal to reevaluate this finding. Snapshots remain rejected. Neither this
failed experiment nor the earlier snapshot implementation closes issue #25.

Official references: [Bases functions](https://help.obsidian.md/bases/functions),
[Bases link types](https://help.obsidian.md/bases/syntax),
[Properties and Markdown limitations](https://help.obsidian.md/properties).
