# Minimal starter acceptance evidence

Scope: Isles-derived templates and single-campaign scaffold, copied to a fresh
independent path. The earlier expanded starter and its two-campaign example are
superseded and are not the acceptance baseline for this PR.

Executed on the local macOS environment:

```sh
python3 -m unittest discover -s tests -v
```

Result: **6 tests passed, no skips or failures**. Tests use only the standard library.

Verified exact-copy CLI installation from an unrelated working directory, relocation,
resolving wikilinks (including query references), no unresolved template substitutions,
valid Obsidian settings JSON, preservation of existing paths and customized files,
rejection of unsafe destinations/source symlinks, refusal to overwrite a destination
created during installation, and independent Git use with scratch ignored and assets
trackable. Tests require no private source checkout.

Obsidian rendering and Dataview execution remain **unverified**. The
[manual checklist](starter-vault.md#verification) records the outstanding checks.
The test suite does not parse YAML or claim multi-campaign operation, agent support,
Bases replacement, or installation on other operating systems.
