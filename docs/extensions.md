# Extensions

Extensions add system-specific schemas, templates and reference pages to a vault.
Select D&D 5.5 (2024 rules) Gear support when [creating a vault](init.md):

```sh
armarium init ../my-vault --extension dnd-5-5
armarium add content "Signal Lantern" --subtype Gear --vault ../my-vault
```

For an existing vault, use the same installer through:

```sh
armarium extension enable dnd-5-5 --vault ../my-vault
```

`--vault` defaults to the vault containing the current directory, as for
[`armarium add`](add.md#choosing-a-vault-and-destination). Enabling an extension applies its
conventions throughout the whole vault, including existing records and every
campaign. Extensions cannot be scoped to individual campaigns. Multiple game
systems within one vault are not supported; use separate vaults for different
systems.

## Installed files

The command copies the extension's reference files into the vault and registers
its rules in `reference/extensions.json`. Core files and existing records are
preserved. Existing destination files and already-enabled extensions are refused.
The command validates the vault after installation; existing records may need
additional fields. Validation failures exit with status 1 and leave the extension
installed so you can update the records.

Files are local and editable. Moving the vault, putting it in its own repository,
or upgrading Armarium does not change them. Extension updates and removal are not
yet automated.

## Schemas and templates

Records must satisfy both their [core schema](schemas.md) and every matching
extension schema. Constraints are combined, so an extension cannot relax a core
requirement. Additional vault-specific constraints can be registered in the same
file.

A matching extension template replaces the default template for record creation.
For example, D&D Gear uses its own template while other Content continues using
`reference/templates/Content.md`. Defaults and body text come from the local
selected template. Two matching template declarations are an error.

The declaration for D&D Gear is:

```json
{
  "dnd-5-5": [
    {
      "type": "Content",
      "subtype": "Gear",
      "schema": "extensions/dnd-5-5/gear.schema.json",
      "template": "extensions/dnd-5-5/Gear.md"
    }
  ]
}
```

`schema` is relative to `reference/schemas/`; `template` is relative to
`reference/templates/`. Each rule requires `type` and `schema`. Omitting `subtype`
applies it to the whole type; omitting `template` adds only validation. Paths must
stay within their respective directories and cannot use symlinks. Malformed
declarations and missing or invalid referenced files are errors.

The installed `reference/dnd-5-5.md` explains the Gear fields and links to its
schema and template. The extension provides conventions, not an equipment
catalogue or importer.

## Developing extensions

Repository extensions live under `extensions/NAME/`. Each has an
`extension.json` declaration in the format above and a `reference/` tree copied
into the vault. Include only original extension files, leaving core files alone.
The wheel and source distribution include these directories.

Test installation into a fresh vault, record creation and validation, and failure
when invalid field values are introduced. Keep schemas additive and templates
complete enough to read and edit directly.
