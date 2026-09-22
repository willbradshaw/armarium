Pages with `type: "[[types/Clue]]"` are persistent GM-known candidate facts not fully known to the players. A clue may be abandoned without revelation and never become canon. Its status tracks its lifecycle, and its subjects link to relevant entities.

Use [[templates/Clue]] for the page structure. Clue text belongs in the `text`
property. The body contains only the Sessions heading and its query, with no
additional commentary.

Store records under `campaigns/campaign_1/clues/`, named `C-1-0001.md`,
`C-1-0002.md`, etc. For another campaign, update the path, campaign number in the
filename, and the Sessions query's campaign path.

## Schema

The [Clue schema](../schemas/clue.schema.json) uses the shared
[parsed-note contract and standalone checks](../schemas/README.md).

`type`, `status`, `text`, `subjects`, `first_session` and `last_session` are
required. Text must contain non-whitespace text; a blank candidate is still a
form. Subjects may be null (not yet identified), `[]` (none recorded), or a list
of Content links. Status is one of the six supplied status links.

`first_session` is the first Session for which the Clue was prepared or used;
`last_session` is the most recent Session in which it was introduced or developed
in play. Both may be null for an unassigned candidate. Preparation alone can set
first while leaving last null; a non-null last requires a non-null first. Unlike
Content appearance history, these fields need not become populated together.
Status does not alone determine either field. `superseded_by` is optional and
nullable except when status is Superseded, which requires a replacement Clue
link. History, campaign agreement and replacement cycles need vault-aware checks.
