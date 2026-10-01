---
type: "[[Reference]]"
---
# D&D 5.5 (2024 rules): Gear

Gear uses the structure and campaign possession rules in [[types/Content]].
The extension adds these frontmatter fields to every Gear record in the vault,
across all campaigns. Use a separate vault for campaigns using another system.

| Field | Required | Values |
| --- | --- | --- |
| `item_type` | Yes | Armor, Potion, Ring, Rod, Scroll, Staff, Wand, Weapon, Wondrous Item, or Equipment. |
| `rarity` | Yes | Common, Uncommon, Rare, Very Rare, Legendary, Artifact, Varies, or Mundane. |
| `attunement` | Yes | Boolean: whether attunement is required. |
| `consumable` | Yes | Boolean: whether using the item consumes it. |
| `cursed` | Yes | Boolean: whether the item is cursed. |
| `attunement_restrictions` | No | Nonblank prerequisite description, or null. A description requires `attunement: true`. |
| `sentient` | No | Boolean, or null when unrecorded. |
| `item_tags` | No | List of distinct nonblank tags, or null when unrecorded. |

Use YAML booleans (`true` or `false`), not quoted strings. An empty list of tags
means no recorded tags. All five required fields need concrete values; the template
provides no assumed defaults. Supply them through frontmatter:

```sh
armarium add content "Rope" --subtype Gear \
  --frontmatter '{"item_type":"Equipment","rarity":"Mundane","attunement":false,"consumable":false,"cursed":false}'
```

`--frontmatter-file PATH` accepts a JSON object file instead. These fields record
GM knowledge, including properties not yet revealed to the players.

Shields use `item_type: Armor`. Use `Equipment` when none of the nine magic-item
categories applies, and `Mundane` for nonmagical equipment.
Use `Varies` for a record describing multiple rarity variants; describe them in
the rules callout. These additional values supplement the categories and rarities
in the [2024 magic item rules](https://www.dndbeyond.com/sources/dnd/br-2024/magic-items).

The rules callout holds mechanics and any further restrictions. Publication or
homebrew attribution belongs in `source`; `url` can link to the source page.
Additional custom fields are allowed.

See the [Gear schema](schemas/gear.schema.json) and
[Gear template](templates/Gear.md).
