Pages with `type: "[[types/Session]]"` are play-session records containing preparation and actual play notes, including events, interactions, and rewards.

Use [[templates/Session]] for the page structure.

Store records under `campaigns/campaign_1/sessions/`, named `S-1-001.md`,
`S-1-002.md`, etc. Set `session_number` and the campaign link. For another campaign,
update the path, campaign link and campaign number in the filename.

In preparation tables, select the relevant records and use inline Dataview to
display their source fields: `text` for Clues, `summary` for Locations and NPCs.
These fields remain live as the source records change. Put session-specific
instructions in Scene notes; record what actually happened under Events.

## Schema

The [Session schema](../schemas/session.schema.json) uses the shared
[parsed-note contract and standalone checks](../schemas/README.md).

Require `type`, `date`, `campaign`, `session_number`, `players_absent`,
`in_game_start_date` and `in_game_end_date`. The campaign is a non-null campaign
Reference link and the session number is a positive integer, including for an
unplayed Session. Date is null when unscheduled, otherwise an ISO `YYYY-MM-DD`
date string; a filled date does not prove play occurred.

`players_absent` is null when unrecorded, `[]` for no absences, or a list of Player
links. In-game dates are null or non-whitespace strings in the campaign's own
calendar, with no imposed real-world calendar or ordering. `aliases` is optional:
null or a list of non-whitespace strings, including `[]`.

Keep the level-one and level-two template headings in order, through Rewards.
Loot and other subsections are optional. Sections may be empty or contain free
Markdown; this permits preparation stubs.
