# Content schema

Use one [[reference/templates/Content|Content template]] for all characters,
locations, factions, objects, and lore. Choose one subtype and add its required
fields before treating the copied template as a completed record. This page defines
the conventions; automated enforcement will be supplied separately.

## Common fields

| Field | Requirement |
| --- | --- |
| `type` | Required value: `"[[reference/types/Content]]"`. |
| `subtype` | Required value: exactly one of `NPC`, `PC`, `Location`, `Faction`, `Object`, `Lore`. |
| `summary` | Required key. A short description of stable identity; may be empty for a stub. |
| `aliases` | Optional list of alternate names. Omitted, bare-null, and an empty list all mean no aliases. |
| `campaign_N` | A mapping for each campaign with recorded state. Do not require a block for every campaign in the vault. |

Inside each existing `campaign_N` block, both `first_session` and `last_session`
keys are required. Before an appearance, both are bare-null. Otherwise both link
to Sessions in that campaign and match its earliest and latest Appearances entries.
Keep these fields nested even on campaign-specific Content pages.

The template includes `campaign_1` for convenience. Remove it if the entry has no
campaign state yet; add another campaign's block when needed. Campaign directories
are `campaigns/campaign_1/`, `campaigns/campaign_2/`, and so on; metadata keys remain
`campaign_1`, `campaign_2`, etc.

An empty value is written as bare `field:` (YAML null), not `""` or `"[[]]"`.
Quote wikilinks in YAML. Additional custom fields are allowed; they must not change
the meanings or value shapes of the standard fields.

## Subtype fields

These fields are top-level unless explicitly marked as campaign state.

| Subtype | Additional requirements |
| --- | --- |
| Lore | None. |
| Object | `held_by` is required inside each existing campaign block; see possession below. |
| Faction | `members` is required: bare-null if unknown, or a list of links to Content pages with subtype PC or NPC. An empty list means there are no recorded members. |
| Location | `parent_location` is required: bare-null for unknown/no parent, or a link to a Content page with subtype Location. |
| PC | `player` is required and must contain a link resolving to a Player page. It cannot be empty, including on a PC stub. |
| NPC | `stats` is required: bare-null, a link to a statistics page, or an absolute HTTP/HTTPS URL. |

Pronouns and birth information belong in Notes when useful. Neither is a required
frontmatter field. A user may add `pronouns` or `birth_year` as a custom property;
there is no required calendar or birth-year format.

For `stats`, null means unspecified or unnecessary. An internal link must resolve
to an existing page, without requiring a particular page type. An external URL
must be well-formed with an HTTP/HTTPS scheme and host; checking it does not require
a network request or prove that the destination is reachable.

For example, after choosing subtype NPC, add `stats:` at the same indentation as
`summary`. For a PC, create its Player page first and fill `player` with that page's
quoted wikilink. Blank templates are unfinished forms, not valid populated records.

## Object possession

Store `held_by` inside each campaign block, alongside its first/last-session fields.
Use the same conventions for ordinary objects and objects with game statistics:

- A quoted link to Content with subtype PC, NPC, or Faction identifies a holder.
- Collective party possession links to the party's Faction page; `party` is not a
  special literal value.
- A list of holder links represents split sets held by different people/groups.
- The literal `GONE` records an object sold, consumed, destroyed, lost, or otherwise
  out of play. In a split set, a list may include `GONE` for a departed portion.
- Before the object enters play (both session fields empty), `held_by` may be
  bare-null. `GONE` is reserved for objects that have entered play.
- Once the object has entered play, a holder or `GONE` is required. An empty list
  or a list containing empty items does not satisfy this requirement.

Locations are not holders. Describe storage location in Notes if relevant. The
current holder is state; session loot and Appearances retain acquisition/transfer
history. Do not rewrite historical loot when an object changes hands.

## Body

All subtypes use these sections, in order:

1. **Notes:** established information; `- N/A` is sufficient for an otherwise empty stub.
2. **Active Clues:** linked Clues relevant to the entry, without asserting their
   unrevealed content as established facts.
3. **Appearances:** chronological session-linked records of actual interaction.
   Incidental mentions and preparation alone do not count. PCs record noteworthy
   contributions rather than attendance.

For entries shared across campaigns, keep each campaign's history under a separate
third-level heading, such as `### campaign_1`. The included Active Clues query is
scoped to campaign 1; when adding another campaign, copy the query into a separately
labeled subsection and change its campaign path. Do not change the shared facts
merely because another campaign encounters the entry.

This schema describes Content. Sessions, Clues, Players, and Transcripts keep their
own record structures; in particular, a Clue's first-session field can refer to
preparation/introduction rather than a Content appearance.
