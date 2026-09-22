Player pages represent the people at the table and link to the PCs they play.
They live under the campaign's `reference/players/` directory.

Use [[templates/Player]]. A PC's `player` field must link to a Player page.

## Schema

The [Player schema](../schemas/player.schema.json) validates parsed
`{frontmatter, body}` records.

Require `type` and `plays`. Use a list of PC Content links; `[]` explicitly
permits an unassigned Player. Null, a single scalar link, and empty link items
are invalid. The body may be empty or contain free Markdown. Reciprocal PC
`player` links are checked separately.
