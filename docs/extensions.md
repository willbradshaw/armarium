# Extensions

Extensions add schemas, templates and reference pages across the whole vault,
including existing records and every campaign. Multiple game systems in one vault
are not supported; use separate vaults for different systems.

```sh
armarium init ../my-vault --extension EXTENSION
armarium extension enable EXTENSION --vault ../my-vault
armarium extension remove EXTENSION --vault ../my-vault
```

Repeat `--extension` to select several during initialization. For existing vaults,
`--vault` defaults to the vault containing the current directory.

| Extension | Content |
| --- | --- |
| [`example`](../extensions/example/README.md) | A Location `climate` field, demonstrated in [the example vault](../vaults/example/). |

Extensions install into `reference/extensions/NAME/`, with `schemas/`, `templates/`
and reference documentation together. Rules are registered in
`reference/extensions.json`. Records must pass their core schema and all matching
extension schemas; matching templates supply defaults for new records. Conflicting
templates are rejected. Failed initialization rolls back all selected extensions.

**Do not edit installed extension files.** Add custom constraints in separate
vault schemas instead. Removal deletes the entire installed extension directory,
including any edits, but preserves records and their fields. Commands validate the
vault afterward; validation failures leave the change in place for correction.
Upgrading Armarium does not update installed extensions.

To define an extension, put its files in `extensions/NAME/` and declare rules in
`extension.json`; see [the example declaration](../extensions/example/extension.json).
Each rule requires `type` and `schema`; optional `subtype` limits its scope, and
optional `template` selects a template. Paths in the source declaration are relative
to the extension directory. Registered paths are relative to the vault's
`reference/`, so local rules can use `schemas/custom.schema.json` without modifying
an extension. Schema paths must stay in core or extension `schemas/` directories;
templates must stay in `templates/` directories. Local rules without an installation
are unregistered on removal without deleting their files.
