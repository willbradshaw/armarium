Pages with `type: "[[types/Session]]"` are play-session records containing preparation and actual play notes, including events, interactions, and rewards.

Use [[templates/Session]] for the page structure.

Store records under `campaigns/campaign_1/sessions/`, named `S-1-001.md`,
`S-1-002.md`, etc. Set `session_number` and the campaign link. For another campaign,
update the path, campaign link and campaign number in the filename.

`prepared_clues`, `prepared_locations` and `prepared_npcs` are ordered link lists
(use `[]` for none; omitted lists also select nothing). Clues must belong to this
campaign; Locations and NPCs must be matching Content subtypes, shared or in this
campaign. List order is display order. Preparation shows current Clue `text` and
Content `summary`, including in past Sessions. Put session-specific instructions
in Scene notes and actual play under Events.

When campaigns use the same reference filename, qualify links with the shortest
unique path, for example `campaign_2/reference/Campaign`. Update existing
Session and index links, and the setting's Session template, when adding a campaign
makes a formerly unique `Campaign` target ambiguous. Set the template's campaign
link to the intended campaign when creating each Session.

## Schema

A Session’s frontmatter requires `type`, `date`, `campaign`, `session_number`,
`players_absent`, `in_game_start_date` and `in_game_end_date`. The campaign
links to its Reference note, and the session number is a positive integer. Date
is `YYYY-MM-DD` or null when unscheduled. In-game dates are nonblank strings in
the campaign's calendar, or null when unrecorded.

`players_absent` is a list of Player links, `[]` for no absences, or null when
unrecorded. Optional `aliases` is a list of nonblank strings, an empty list, or
null. The body keeps the template's level-one and level-two headings in order
through Rewards. Sections may be empty; Loot and other subsections are optional.

See the [Session schema](../schemas/session.schema.json).
