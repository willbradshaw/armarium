# Extensions

An extension adds schemas, templates and reference pages to the whole vault,
including its existing records and every campaign. Armarium does not support
several game systems in one vault; use a separate vault for each.

| Extension | Content |
| --- | --- |
| [`dnd-5-5`](../extensions/dnd-5-5/README.md) | D&D 2024 Gear fields and template, Spell and Monster subtypes, character checks, and rules reference pages. |
| [`example`](../extensions/example/README.md) | A Location `climate` field, demonstrated in [the example vault](../vaults/example/). |

## Enabling

```sh
armarium init ../my-vault --extension EXTENSION
armarium extension enable EXTENSION --vault ../my-vault
```

Repeat `--extension` to install several when creating a vault. For an
existing vault, `--vault` defaults to the vault containing the current
directory.

The extension's files go in `reference/extensions/NAME/`, grouped into
`schemas/`, `templates/` and reference pages. Records must satisfy both the
core schemas and the extension's. An extension's template for a type or
subtype supplies the defaults for new records of it; the command refuses
templates that conflict.

An extension can also
[add to the vault's agent skills](agents.md#adding-to-a-skill). Each addition
goes in `.agents/skills/SKILL/addenda/NAME.md`. If the vault doesn't have that
skill, the command skips the addition and logs a warning.

Both commands validate the vault once they finish. If validation fails, the
new vault or the enabled extension stays in place for you to correct. If
installing fails, the command undoes everything, including every extension
selected for a new vault.

## Removing

```sh
armarium extension remove EXTENSION --vault ../my-vault
```

`remove` unregisters the extension and deletes its installed directory and
skill addenda, including any local edits to them. It keeps records and their
fields. It then validates the vault; if validation fails, the extension stays
removed for you to correct the records.

## Updating

```sh
armarium extension update EXTENSION --vault ../my-vault
```

After upgrading Armarium, run this command to replace an installed extension
with its current files, rules and skill addenda. Until then, validation
reports `vault.outdated` for any extension whose installed files differ from
those Armarium supplies. [`armarium update --extensions`](update.md#extensions)
updates every such extension along with the vault's other copied files.

The update overwrites local edits to the installed files, and keeps records,
separate custom schemas and the vault's own addenda. If installing fails, it
restores the previous extension. It then validates the vault; if validation
fails, the updated extension stays installed for you to correct the records.

`reference/extensions.json` records the `armarium_version` that supplied the
extension, on enable and on update. An update runs even when the versions
match. Replacing an extension installed by a newer Armarium requires
`--allow-downgrade`. The command does not upgrade Armarium or migrate records.

## Custom schemas

Do not edit installed extension files. Keep your own constraints in a separate
schema, such as `reference/schemas/custom.schema.json`, and register it with
an entry in `reference/extensions.json`, beside the installed extensions:

```json
{
  "house-rules": {
    "rules": [
      {"type": "Content", "schema": "schemas/custom.schema.json"}
    ]
  }
}
```

This entry applies the custom schema to Content records, on top of their
existing schemas. The path names a file in the vault's `reference/` directory.
Removing the entry leaves the schema file in place.

## Defining an extension

Put the extension's files in `extensions/NAME/` and declare its rules in
`extension.json`, as in the
[example declaration](../extensions/example/extension.json). Each rule
requires `type` and `schema`, and may also have:

- `subtype`, limiting the rule to an existing subtype;
- `template`, the template for new records the rule matches;
- `yaml_blocks`, a list of code block info strings, such as `statblock`. A
  fenced block with one of them in a matching record must hold a YAML mapping,
  or validation reports `extension.yaml`;
- `links`, [declaring link targets](#declaring-link-targets).

Paths in the declaration are relative to the extension directory. Schemas go
in `schemas/` and templates in `templates/`.

An extension can also turn on one of Armarium's optional checks by listing its
name under `checks`, beside `rules`. The one available is `xp-tables`, which
[`dnd-5-5`](../extensions/dnd-5-5/README.md#sessions) uses.

To add to an agent skill, put a Markdown file named for the skill in
`skills/`, such as `skills/update-record.md`. It needs no declaration, and
installs as that skill's addendum, not with the reference files.

### Declaring subtypes

An extension can add Content subtypes that Armarium itself does not have. List
them under `subtypes`, keyed by type, and give each one a rule in the same
extension that supplies a template:

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

Only Content takes new subtypes; Reference has a fixed set. A name starts with
a letter and holds only letters and digits, and may not repeat a core subtype
or one that another enabled extension declares. A record of a declared
subtype must meet the core Content requirements and the extension's schema.

### Declaring link targets

A rule's `links` restricts which records the wikilinks in a frontmatter field
may point to. Each key is a top-level field. Its value gives the record `type`
that a link in the field must target and, when that type is Content or
Reference, may list the `subtypes` allowed:

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

In a matching record, every link in a declared field must resolve to a
correctly placed record of that type and subtype, in the same campaign as the
linking record or, for Content, shared. A list may not name the same record
twice. Validation reports `link.type`, `campaign.mismatch` and
`link.duplicate`, as it does for [built-in fields](type.md). A value without
links, such as null or a URL, is left to the schema.

A rule may not declare a field whose target the core already fixes for its
records, such as `parent_location` on a Location, nor one that another rule
declares for the same records.
