# Extension development

An extension lives in `extensions/NAME/`, with `extension.json` declaring rules
and a `reference/` tree installed into the vault. Both package distributions
include these files. See [the example extension](../extensions/example/) for a
complete implementation and [Extensions](extensions.md) for usage.

A declaration maps an identifier to its rules:

```json
{
  "example": {
    "rules": [
      {
        "type": "Content",
        "subtype": "Location",
        "schema": "extensions/example/location.schema.json",
        "template": "extensions/example/Location.md"
      }
    ]
  }
}
```

Each rule requires `type` and `schema`. Optional `subtype` restricts the rule to
one subtype; optional `template` selects a complete template for record creation.
Paths are relative to `reference/schemas/` and `reference/templates/` respectively
and cannot escape those directories or use symlinks.

Schemas add constraints to the [core schema](schemas.md); they cannot relax it.
Additional local rules can use the same declaration format. Templates must declare
the selected type/subtype; overlapping template selectors are rejected.

Installation adds a `files` mapping to the vault's declaration: paths relative to
`reference/` and their SHA-256 hashes. Removal uses that inventory, independently
of the currently installed Armarium version, to protect local edits. Locally
registered rules without an inventory can be removed without deleting files.

Keep extension files separate from core files. Document conventions in a Reference
page linking to their schema and template. Test installation, creation, validation,
removal, local edits and rollback. The example vault demonstrates an enabled
extension alongside the unextended starter vault.
