Pages with `type: "[[types/Clue]]"` are persistent GM-known candidate facts not fully known to the players. A clue may be abandoned without revelation and never become canon. Its status tracks its lifecycle, and its subjects link to relevant entities.

Use [[templates/Clue]] for the page structure. Clue text belongs in the `text`
property. The body contains only the Sessions heading and its query, with no
additional commentary.

Store records under `campaigns/campaign_1/clues/`, named `C-1-0001.md`,
`C-1-0002.md`, etc. For another campaign, update the path, campaign number in the
filename, and the Sessions query's campaign path.

## Schema

A Clue’s frontmatter requires `type`, `status`, nonblank `text`, `subjects`,
`first_session` and `last_session`. Status links to one of the six supplied
statuses. Subjects are Content links: null means unidentified, and `[]` means
none recorded.

`first_session` links to the first Session for which the Clue was prepared or
used; `last_session` links to its latest introduction or development in play.
Both may be null. Preparation alone can set first; setting last requires first.
Superseded Clues also require a replacement Clue link in `superseded_by`;
otherwise that field is optional and nullable.

The body contains only `## Sessions` followed by one nonempty view fenced with
three backticks.

See the [Clue schema](../schemas/clue.schema.json).
