# Extensions

Extensions add schemas, templates and reference pages across the whole vault,
including existing records and every campaign. Multiple game systems in one vault
are not supported; use separate vaults for different systems.

| Extension | Content |
| --- | --- |
| [`dnd-5-5`](../extensions/dnd-5-5/README.md) | D&D 2024 Gear fields and template. |
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
it on update. Updating is allowed even when versions match. Replacing an extension
installed by a newer Armarium version requires `--allow-downgrade`. The command
does not upgrade Armarium or migrate records automatically.

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
`type` and `schema`. Optional `subtype` limits its scope to an existing subtype;
optional `template` selects a template. Source declaration paths are relative to
the extension directory. Schemas and templates belong in their respective
subdirectories.

### Declaring subtypes

An extension can add Content subtypes for kinds of record that only its game
system has, such as spells. List them under `subtypes`, keyed by type:

```json
{
  "my-system": {
    "subtypes": {"Content": ["Spell"]},
    "rules": [
      {
        "type": "Content",
        "subtype": "Spell",
        "schema": "schemas/spell.schema.json",
        "template": "templates/Spell.md"
      }
    ]
  }
}
```

Only Content subtypes can be declared. A name starts with a letter and contains
only letters and digits. Each declared subtype needs a rule in the same
extension that selects it and supplies a template, so `armarium add content`
can create it. Its records also meet the core Content requirements that apply
to every subtype. The extension's schema adds anything else, including body
rules. Document new subtypes in the extension's README.

An extension cannot declare a core subtype or one another enabled extension
declares, and no rule may select a Content subtype that neither core nor an
enabled extension declares. Any of these makes the vault's extensions invalid.
Removing an extension leaves its records in place; validation then reports their
subtype until the records are changed or the extension is enabled again.

Vaults created before Armarium supported declared subtypes have a closed list of
subtypes in `reference/schemas/content.schema.json`. Copy that file from the
starter vault of the current release before enabling an extension that
declares subtypes.
