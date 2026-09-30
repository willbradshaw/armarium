# Extensions

Extensions add schemas, templates and reference pages across the whole vault,
including existing records and every campaign. Multiple game systems in one vault
are not supported; use separate vaults for different systems.

```sh
armarium init ../my-vault --extension EXTENSION
armarium extension enable EXTENSION --vault ../my-vault
armarium extension remove EXTENSION --vault ../my-vault
```

Replace `EXTENSION` with an identifier below. For an existing vault, `--vault`
defaults to the vault containing the current directory.

| Extension | Content |
| --- | --- |
| [`example`](../extensions/example/reference/example.md) | A Location `climate` field, schema and template; enabled in [the example vault](../vaults/example/). |

Enabling installs editable reference files and registers rules in
`reference/extensions.json`. Records must pass their core schema and all matching
extension schemas. Matching extension templates supply defaults for new records.
Existing files are not overwritten; conflicting templates are rejected.

Removal unregisters the extension and deletes its unchanged installed files.
It refuses to delete locally edited files or files declared by another extension.
Records and their fields are preserved. Both enabling and removal validate the
vault afterward; validation failures leave the change in place for you to resolve.

Upgrading Armarium does not update installed extension files. For the declaration
format and contributor guidance, see [Extension development](extension-development.md).
