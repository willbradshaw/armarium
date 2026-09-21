# Basic starter acceptance evidence

Scope: canonical static starter, fresh-path installer, and original two-campaign
example. This report does not claim the future packaged CLI, agent skills, live
views, updater, or full validator are implemented.

## Automated result

Executed during this implementation:

```sh
uv run --no-project --with 'PyYAML>=6,<7' python -m unittest discover -s tests -v
```

Result: **13 tests passed, no skips or failures** on the local macOS development
environment. The test suite creates isolated temporary directories and uses the
actual installer CLI from outside the repository where appropriate.

Verified:

- Fresh installation, paths containing spaces, Unicode/punctuation in display names.
- Two campaigns, string-valued numeric IDs, parsed YAML, and resolving static links.
- Existing empty/nonempty directories, files, and dangling symlinks are preserved.
- A destination created after initial validation is not overwritten.
- Bad IDs, duplicate IDs, invalid names, and missing parents do not create a vault.
- Unknown template substitutions fail before the destination is created.
- Repeated installations at new locations are byte-identical for identical inputs.
- Relocation preserves links; installed files contain no source-machine paths.
- Customized files survive a refused attempt to install over the existing vault.
- A setting vault can be its own Git repository, with raw inputs/scratch ignored
  and durable handouts available for tracking.
- The original fixture has two distinct campaign histories on shared world pages.
  Its abandoned passage candidate is not asserted as canon on the location page.

Separately invoked the CLI to create a blank review vault and a two-campaign
review vault under a fresh temporary parent outside the checkout, then overlaid
the original example into the latter. Both commands completed successfully.

## Still unverified

No in-app Obsidian rendering check was performed. The reproducible manual checklist
is in [the starter guide](starter-vault.md#manual-obsidian-acceptance-checklist).
Do not close the broader starter issue's Obsidian acceptance criterion based on
file-level checks alone. Other operating systems and agent hosts were not tested
by this increment. The installer does not set up shared agent skills.
