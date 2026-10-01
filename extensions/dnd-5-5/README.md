---
type: "[[Reference]]"
---
# D&D 5.5 (2024 rules): Gear

See [[types/Content#Fields]] for the definition of Gear and its core fields.
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
| `sentient` | Yes | Boolean: whether the item is sentient. |
| `item_tags` | Yes | List of unique, nonblank strings; `[]` for no tags. |

Use YAML booleans (`true` or `false`), not quoted strings. An empty list of tags
means no recorded tags. All seven required fields need concrete values; the template
provides no assumed defaults. Supply them through frontmatter:

```sh
armarium add content "Rope" --subtype Gear \
  --frontmatter '{"item_type":"Equipment","rarity":"Mundane","attunement":false,"consumable":false,"cursed":false,"sentient":false,"item_tags":[]}'
```

`--frontmatter-file PATH` accepts a JSON object file instead. These fields record
GM knowledge, including properties not yet revealed to the players.

For nonmagical equipment, use the `Equipment` type and `Mundane` rarity.
Magic shields use `item_type: Armor`.
Use `Varies` for a record describing multiple rarity variants; describe them in
the rules callout. These additional values supplement the categories and rarities
in the [2024 magic item rules](https://www.dndbeyond.com/sources/dnd/br-2024/magic-items).

See the [Gear schema](schemas/gear.schema.json) and
[Gear template](templates/Gear.md).
