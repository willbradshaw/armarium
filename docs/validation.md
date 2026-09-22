# Validate a Markdown file

From a source checkout with the dependencies in `tests/schemas/requirements.txt`
installed:

```sh
PYTHONPATH=src python -m armarium.cli validate path/to/record.md
PYTHONPATH=src python -m armarium.cli validate path/to/record.md --vault path/to/vault
```

The command parses and schema-validates one file without changing it. It prints
relative paths, field or line locations where available, diagnostics, and counts
of checked, skipped and unsupported records. Missing types are errors; only
files under `reference/templates/` are skipped after successful parsing. Missing
schemas produce explicit partial-coverage warnings.

Exit codes: **0** for no errors (including skips and partial coverage), **1** for
validation errors, **2** for invalid invocation. Diagnostics and counts go to
standard output; invocation errors go to standard error.

Directory traversal, vault-wide checks and contextual link validation are not
part of this command yet. Schemas come from the selected vault; remote schema
retrieval is disabled.
