Pages with `type: "[[types/Session]]"` are play-session records containing preparation and actual play notes, including events, interactions, and rewards.

Use [[templates/Session]] for the page structure.

Store records under `campaigns/campaign_1/sessions/`, named `S-1-001.md`,
`S-1-002.md`, etc. Set `session_number` and the campaign link. For another campaign,
update the path, campaign link and campaign number in the filename.

In preparation tables, select the relevant records and use inline Dataview to
display their source fields: `text` for Clues, `summary` for Locations and NPCs.
These fields remain live as the source records change. Put session-specific
instructions in Scene notes; record what actually happened under Events.
