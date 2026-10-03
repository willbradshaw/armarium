---
type: "[[Reference]]"
---
# D&D 5.5 (2024 rules)

The `dnd-5-5` extension adapts Armarium vaults for Dungeons & Dragons' 2024 rules.
It provides schemas and templates for recording equipment, spells and monsters,
so they can be described consistently and filtered by their game properties.
Spell and Monster are Content subtypes this extension adds. Monster stat blocks
render with the [Fantasy Statblocks](https://github.com/javalent/fantasy-statblocks)
Obsidian plugin.

Its fields represent concepts from the
[2024 magic item rules](https://www.dndbeyond.com/sources/dnd/br-2024/magic-items):
item category, rarity, attunement requirements, consumability, curses and sentience.
Armarium expresses these as frontmatter fields with validation rules. Gear also
requires the core `content_tags` field, for freeform labels.

## Gear fields

These requirements apply to every Gear record across all campaigns in the vault,
in addition to the definition and core fields in [[types/Content#Fields]].

| Field | Required | Values |
| --- | --- | --- |
| `item_type` | Yes | Armor, Potion, Ring, Rod, Scroll, Staff, Wand, Weapon, Wondrous Item, or Equipment. |
| `rarity` | Yes | Common, Uncommon, Rare, Very Rare, Legendary, Artifact, Varies, or Mundane. |
| `attunement` | Yes | Boolean: whether attunement is required. |
| `consumable` | Yes | Boolean: whether using the item consumes it. |
| `cursed` | Yes | Boolean: whether the item is cursed. |
| `attunement_restrictions` | No | Nonblank prerequisite description, or null. A description requires `attunement: true`. |
| `sentient` | Yes | Boolean: whether the item is sentient. |
| `content_tags` | Yes | A list, not null; `[]` for no tags. |

## Creating Gear

Use YAML booleans (`true` or `false`), not quoted strings. An empty list of tags
means no recorded tags. All seven required fields need concrete values; the template
provides no assumed defaults. Supply them through frontmatter:

```sh
armarium add content "Rope" --subtype Gear \
  --frontmatter '{"item_type":"Equipment","rarity":"Mundane","attunement":false,"consumable":false,"cursed":false,"sentient":false,"content_tags":[]}'
```

`--frontmatter-file PATH` accepts a JSON object file instead. These fields record
GM knowledge, including properties not yet revealed to the players.

## Classifying equipment

Nonmagical armor and shields use `item_type: Armor`; nonmagical weapons use
`item_type: Weapon`. Both use `rarity: Mundane`. Use `item_type: Equipment` for
other mundane gear, such as rope and tools.

Magic items use their D&D category and rarity; magic shields use `Armor`.
`Equipment` and `Mundane` are Armarium conventions for recording nonmagical gear.
`Varies` represents multiple rarity variants in one record; describe the variants
in the rules callout.

See the [Gear schema](schemas/gear.schema.json) and
[Gear template](templates/Gear.md).

## Spell fields

Spell fields follow the
[2024 spell description format](https://www.dndbeyond.com/sources/dnd/br-2024/spells).
They apply in addition to the core fields in [[types/Content#Fields]].

| Field | Required | Values |
| --- | --- | --- |
| `source` | Yes | Publication or homebrew attribution, or null when unrecorded. |
| `level` | Yes | Integer from 0 (cantrip) to 9. |
| `school` | Yes | Abjuration, Conjuration, Divination, Enchantment, Evocation, Illusion, Necromancy, or Transmutation. |
| `casting_time` | Yes | Nonblank text, such as `1 Action` or `1 Reaction, which you take when you fall`. |
| `ritual` | Yes | Boolean: whether the spell can be cast as a ritual. |
| `range` | Yes | Nonblank text, such as `Self`, `Touch` or `60 feet`. |
| `area` | No | Nonblank area of effect, such as `20-foot Sphere`, or null for none. |
| `components` | Yes | List of unique values from Verbal, Somatic and Material. |
| `material` | With Material | Nonblank description of the material component; null or omitted otherwise. |
| `duration` | Yes | Nonblank text, such as `Instantaneous` or `1 minute`. |
| `concentration` | Yes | Boolean: whether the spell requires concentration. |
| `requires_save`, `requires_attack` | Yes | Booleans: whether the spell calls for a saving throw or an attack roll. |
| `content_tags` | Yes | A list, not null; `[]` for no tags. |
| `image`, `url` | No | As for Gear: an image path or URL, and an HTTP/HTTPS source URL. |

Like Gear, the body starts with a `> [!rules]` callout holding the spell's text,
and the template provides no assumed values:

```sh
armarium add content "Salt Ward" --subtype Spell \
  --frontmatter '{"source":"Homebrew","level":1,"school":"Abjuration","casting_time":"1 Action","ritual":true,"range":"Touch","components":["Verbal","Material"],"material":"a pinch of sea salt","duration":"8 hours","concentration":false,"requires_save":false,"requires_attack":false,"content_tags":[]}'
```

See the [Spell schema](schemas/spell.schema.json) and
[Spell template](templates/Spell.md).

## Monster fields

Monster fields record what a creature is for filtering and sorting; its full
statistics live in the stat block. They apply in addition to the core fields in
[[types/Content#Fields]].

| Field | Required | Values |
| --- | --- | --- |
| `source` | Yes | Publication or homebrew attribution, or null when unrecorded. |
| `cr` | Yes | Challenge rating as text: `0`, `1/8`, `1/4`, `1/2`, or `1` to `30`. |
| `cr_sort` | Yes | The challenge rating as a number (`0.125` for `1/8`), for sorting and comparison. |
| `xp` | Yes | Integer experience points. |
| `size` | Yes | Tiny, Small, Medium, Large, Huge, or Gargantuan. |
| `creature_type` | Yes | Aberration, Beast, Celestial, Construct, Dragon, Elemental, Fey, Fiend, Giant, Humanoid, Monstrosity, Ooze, Plant, or Undead. A swarm uses the type of its members. |
| `creature_subtypes` | No | List of unique, nonblank tags, such as `Demon` or `Elf`, or null. |
| `alignment` | No | Nonblank text, such as `Chaotic Evil` or `Unaligned`, or null. |
| `spells` | No | List of unique links to the Spell records the creature can cast, or null. |
| `content_tags` | Yes | A list, not null; `[]` for no tags. |
| `image`, `url` | No | As for Gear: an image path or URL, and an HTTP/HTTPS source URL. |

The body starts with `## Statblock` holding one `statblock` code block: the
Fantasy Statblocks plugin's YAML. Validation reports a `statblock` block that is
not a YAML mapping. The template's block holds only `name:`; fill it in after
creating the record:

```sh
armarium add content "Reef Shark" --subtype Monster \
  --frontmatter '{"source":"Monster Manual","cr":"1/2","cr_sort":0.5,"xp":100,"size":"Medium","creature_type":"Beast","content_tags":[]}'
```

See the [Monster schema](schemas/monster.schema.json) and
[Monster template](templates/Monster.md).
