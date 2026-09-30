# Extensions

Extensions add schemas, templates and reference pages across the whole vault,
including existing records and every campaign. Multiple game systems in one vault
are not supported; use separate vaults for different systems.

| Extension | Content |
| --- | --- |
| [`example`](../extensions/example/README.md) | A Location `climate` field, demonstrated in [the example vault](../vaults/example/). |

## Enabling

```sh
armarium init ../my-vault --extension EXTENSION
armarium extension enable EXTENSION --vault ../my-vault
```

Repeat `--extension` to select several during initialization. For an existing
vault, `--vault` defaults to the vault containing the current directory.

Files install into `reference/extensions/NAME/`, grouped into `schemas/`,
`templates/` and reference documentation. Records must satisfy both core and
extension schemas. Matching extension templates supply defaults for new records;
conflicting templates are rejected.

Both commands validate the completed vault. Validation failures leave the new
vault or enabled extension in place for correction. Installation failures roll
back the operation, including all selected extensions during initialization.

## Removing

```sh
armarium extension remove EXTENSION --vault ../my-vault
```

Removal unregisters the extension and deletes its installed directory, including
any local edits. Records and their fields are preserved. The command then validates
the vault; validation failures leave the removal in place for correction.

## Updating

```sh
armarium extension update EXTENSION --vault ../my-vault
```

After upgrading Armarium, run this command to replace an installed extension with
its current files and rules. Local edits to installed files are overwritten;
records and separate custom schemas are preserved. Installation failures restore
the previous extension. Validation runs afterward; failures leave the updated
extension installed for record corrections.

`reference/extensions.json` records the supplying `armarium_version` on enable
and update. Older installations without this field remain supported and acquire
it on update. Updating is allowed even when versions match. The command does not
upgrade Armarium or migrate records automatically.

## Custom schemas

Do not edit installed extension files. Store custom constraints separately, for
example in `reference/schemas/custom.schema.json`. Register them by adding an entry
to `reference/extensions.json`, alongside the installed extensions:

```json
{
  "house-rules": {
    "rules": [
      {"type": "Content", "schema": "schemas/custom.schema.json"}
    ]
  }
}
```

This applies the custom schema to Content records in addition to their existing
schemas. The path names a file inside the vault's `reference/` directory. Removing
this local registration leaves the custom schema file intact.

## Defining an extension

Put files in `extensions/NAME/` and declare rules in `extension.json`; see the
[example declaration](../extensions/example/extension.json). Each rule requires
`type` and `schema`. Optional `subtype` limits its scope; optional `template` selects
a template. Source declaration paths are relative to the extension directory.
Schemas and templates belong in their respective subdirectories.
