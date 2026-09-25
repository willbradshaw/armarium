---
type: "[[Type]]"
directories: { campaign: reference/players }
---
Player records represent the people at the table and link to the PCs they play.
They live under the campaign's `reference/players/` directory.

Use [[templates/Player]]. A PC's `player` field must link to a Player record.

## Schema

A Player record’s frontmatter requires `type` and `plays`, a list of PC Content
links. Use `[]` for an unassigned Player; null and a single scalar link are
invalid. The body may be empty or contain free Markdown.

See the [Player schema](../schemas/player.schema.json).
