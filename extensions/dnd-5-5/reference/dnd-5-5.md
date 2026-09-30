---
type: "[[Reference]]"
---
# D&D 5.5 (2024 rules): Gear

Gear uses the structure and campaign possession rules in [[types/Content]].
The extension adds these frontmatter fields to every Gear record in the vault,
across all campaigns. Use a separate vault for campaigns using another system.

| Field | Required | Values |
| --- | --- | --- |
| `item_type` | Yes | Armor, Potion, Ring, Rod, Scroll, Staff, Wand, Weapon, Wondrous Item, or null when unrecorded or inapplicable. |
| `rarity` | Yes | Common, Uncommon, Rare, Very Rare, Legendary, Artifact, Varies, or null when unrecorded or not applicable to mundane equipment. |
| `attunement` | Yes | Boolean: whether attunement is required; null when unrecorded. |
| `consumable` | Yes | Boolean: whether using the item consumes it; null when unrecorded. |
| `cursed` | Yes | Boolean: whether the item is cursed; null when unrecorded. |
| `attunement_restrictions` | No | Nonblank prerequisite description, or null. A description requires `attunement: true`. |
| `sentient` | No | Boolean, or null when unrecorded. |
| `item_tags` | No | List of distinct nonblank tags, or null when unrecorded. |

Use YAML booleans (`true` or `false`), not quoted strings. An empty list of tags
means no recorded tags. The template leaves fields null for you to fill in.

Shields use `item_type: Armor`. Use null for mundane equipment without an
applicable category.
Use `Varies` for a record describing multiple rarity variants; describe them in
the rules callout. These conventions follow the
[2024 magic item rules](https://www.dndbeyond.com/sources/dnd/br-2024/magic-items).

The rules callout holds mechanics and any further restrictions. Publication or
homebrew attribution belongs in `source`; `url` can link to the source page.
Additional custom fields are allowed.

See the [Gear schema](schemas/extensions/dnd-5-5/gear.schema.json) and
[Gear template](templates/extensions/dnd-5-5/Gear.md).
