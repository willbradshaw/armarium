Pages with `type: "[[types/Session]]"` are play-session records containing preparation and actual play notes, including events, interactions, and rewards.

Use [[templates/Session]] for the page structure.

Store records under `campaigns/campaign_1/sessions/`, named `S-1-001.md`,
`S-1-002.md`, etc. Set `session_number` and the campaign link. For another campaign,
update the path, campaign link and campaign number in the filename.

`prepared_clues`, `prepared_locations` and `prepared_npcs` are ordered link lists
(use `[]` for none). Clues must belong to this campaign; Locations and NPCs must
be matching Content subtypes, shared or in this campaign. List order is display
order. Preparation shows current Clue `text` and Content `summary`, including in
past Sessions. Put session-specific instructions in Scene notes and actual play
under Events.
