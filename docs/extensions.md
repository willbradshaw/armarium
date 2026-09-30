# Extensions

Extensions provide additional schemas, templates and reference pages. Each enabled
extension applies throughout the vault, including existing records and every
campaign. Extensions cannot be scoped to individual campaigns. Multiple game
systems within one vault are not supported; use separate vaults for different
systems.

## Available extensions

| Identifier | Content |
| --- | --- |
| [`dnd-5-5`](../extensions/dnd-5-5/reference/dnd-5-5.md) | D&D 5.5 (2024 rules) Gear fields, template and reference page. |

## Enabling an extension

Choose an identifier from the table above and substitute it for `EXTENSION`.
Select an extension when [creating a vault](init.md):

```sh
armarium init ../my-vault --extension EXTENSION
```

For an existing vault:

```sh
armarium extension enable EXTENSION --vault ../my-vault
```

`--vault` defaults to the vault containing the current directory, as for
[`armarium add`](add.md#choosing-a-vault-and-destination). Both commands use the
same installer and validate the vault after setup.

## Installed files

Installation copies the extension's reference files into the vault and registers
its rules in `reference/extensions.json`. Core files and existing records are
preserved. Existing destination files and already-enabled extensions are refused.
Failed installation rolls back its changes.

Existing records may need changes to meet the additional constraints. Validation
failures exit with status 1 and leave the extension installed so you can update
the records.

Files are local and editable. Moving the vault, putting it in its own repository,
or upgrading Armarium does not change them. Extension updates and removal are not
yet automated.

## Schemas and templates

Records must satisfy both their [core schema](schemas.md) and every matching
extension schema. Constraints are combined, so an extension cannot relax a core
requirement. Additional vault-specific constraints can be registered in the same
file.

A matching extension template takes precedence over the default template for
[record creation](add.md#templates-and-validation). Defaults and body text come
from that local template. Records without a matching extension template continue
using their default template. Two matching template declarations are an error.

## Developing extensions

Repository extensions live under `extensions/NAME/`. Each has an
`extension.json` declaration and a `reference/` tree copied into the vault.
Include only the extension's files, leaving core files alone. The wheel and source
distribution include these directories.

Declarations map an extension identifier to a list of rules. For example:

```json
{
  "example-extension": [
    {
      "type": "Content",
      "schema": "extensions/example-extension/content.schema.json",
      "template": "extensions/example-extension/Content.md"
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `type` | Required record type to which the rule applies. |
| `subtype` | Optional restriction to one subtype; omitting this field applies the rule to the whole type. |
| `schema` | Required path relative to `reference/schemas/`. |
| `template` | Optional path relative to `reference/templates/`; omit to add only validation. |

Paths must stay within their respective directories and cannot use symlinks.
Malformed declarations and missing or invalid referenced files are errors.
Document the extension's conventions in its own Reference pages and link to its
schemas and templates there.

Test installation into a fresh vault, record creation and validation, and failure
when invalid field values are introduced. Keep schemas additive and templates
complete enough to read and edit directly.
