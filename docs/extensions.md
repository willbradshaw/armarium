# Extensions

Extensions add schemas, templates and reference pages across the whole vault,
including existing records and every campaign. Multiple game systems in one vault
are not supported; use separate vaults for different systems.

| Extension | Content |
| --- | --- |
| [`dnd-5-5`](../extensions/dnd-5-5/README.md) | D&D 2024 Gear fields and template, Spell and Monster subtypes, character checks, and rules reference pages. |
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
optional `template` selects a template. Optional `yaml_blocks` lists code block
info strings, such as `statblock`, whose fenced blocks must hold a YAML mapping
in matching records; validation reports `extension.yaml` otherwise. Optional
`links` [declares link targets](#declaring-link-targets). Source
declaration paths are relative to the extension directory. Schemas and templates
belong in their respective subdirectories.

### Declaring subtypes

An extension can add Content subtypes not present in the base package. List them
under `subtypes`, keyed by type, and give each a rule in the same extension that
supplies a template:

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

Content is the only type with subtypes. Names start with a letter and contain
only letters and digits, and may not repeat a core subtype or one another
enabled extension declares. Records of a declared subtype meet the core Content
requirements and the extension's schema.

### Declaring link targets

A rule's `links` restricts which records the wikilinks in a frontmatter field
may point to. Each key is a top-level field; its value gives the record `type`
a link in that field must target and, when that type is Content, optionally
the `subtypes` allowed:

```json
{
  "type": "Content",
  "subtype": "Location",
  "schema": "schemas/location.schema.json",
  "links": {
    "ruler": {"type": "Content", "subtypes": ["NPC", "PC"]},
    "surveyed_by": {"type": "Player"}
  }
}
```

In matching records, every link in a declared field must resolve to a
correctly placed record of that type and subtype, in the same campaign as the
linking record or, for Content, shared; a list may not name the same record
twice. Validation reports `link.type`, `campaign.mismatch` and
`link.duplicate` as it does for [built-in fields](type.md). A value without
links, such as null or a URL, is left to the schema.

A rule may not declare a field whose target the core already fixes for its
records, such as `parent_location` on a Location, nor one that another rule
declares for the same records.
