# Player and Transcript examples

These original, fictional records demonstrate the two templates. `Example Player`
is a placeholder, and Mira and the observatory scene are invented. The PC and
Session are minimal link targets, not replacements for the starter templates.

From the repository root, copy the starter and overlay the fixture in a new,
disposable vault (choose a destination whose parent exists):

```sh
records_vault="../armarium-records-example"
mkdir "$records_vault" && cp -R starter/. "$records_vault/" && cp -R tests/records/fixture/. "$records_vault/"
```

Open that folder in Obsidian. Check the Player's `type` and `plays` properties;
follow `plays` to Mira and `player` back. Check the Transcript's `type` and
`session` properties and follow the session link. In reading view, confirm that
the three content headings and speaker labels render, including `[Mira?]`,
`[Player?]`, and inline `[?]`. Obsidian may visually join adjacent utterances
within a paragraph; source mode preserves one utterance per line.

Also inspect both templates: `plays` and `session` start blank (YAML null), with
no fake link targets or speech. Fill `plays` with quoted canonical PC links, or
use `[]` when explicitly empty. Before using a Transcript as a record, fill its
session link, name it `S-N-NNN Transcript.md`, and replace/add/remove its content
headings as appropriate. The example uses campaign 1's existing paths.

Run the focused checks with Python and PyYAML, or let uv provide the dependency:

```sh
uv run tests/records/test_records.py
```

These checks cover only these templates and fixtures. Issue #6's general vault
checker is not yet on main; integration with it remains a follow-up when it lands.

## Rendering check

Checked on 2026-09-21 in Obsidian 1.13.7 (installer 1.12.7), using an isolated
profile and a disposable starter copy with this fixture overlaid. Opened the
Player, Transcript, and both templates in reading view. The Player's `type` and
`plays` and the Transcript's `type` and `session` rendered as resolved links;
following the PC and Session targets opened the expected pages. The templates
showed empty `plays` and `session` properties and resolved type links. The
Transcript displayed all three content headings, separate utterance lines,
and literal `[Mira?]`, `[Player?]`, and `[?]` labels. Verified the rendered DOM
through Obsidian's local CLI and visually inspected a transcript screenshot.
