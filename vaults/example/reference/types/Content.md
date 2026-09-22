# Content

Content pages describe characters, places, groups, objects, or setting lore.
Keep each shared entity in one page under `content/`; campaign-specific entries
live in `campaigns/campaign_1/content/` (or the corresponding campaign folder).

Copy [[templates/Content]], name it for the entity, choose a subtype,
and add its required fields.

## Fields

Every Content record requires `type`, `subtype`, and `summary`. The template sets
`type`; choose subtype NPC, PC, Location, Faction, Object or Lore. Write a short
summary of stable identity, or leave it empty for a stub. `aliases` is optional:
use a list of alternate names, or omit it or leave it empty when there are none.

| Subtype | Additional required fields |
| --- | --- |
| NPC | `stats`: empty, an internal wikilink, or an HTTP/HTTPS URL. |
| PC | `player`: a nonempty wikilink to a Player record. |
| Location | `parent_location`: empty or a wikilink to Location Content. |
| Faction | `members`: empty if unknown, or a list of PC/NPC Content links. An empty list means no recorded members. |
| Object | `held_by` inside each campaign block: holder link(s) or `GONE`; may be empty before entering play. |
| Lore | None. |

Use bare `field:` for null and quote YAML wikilinks. Additional custom fields are
allowed. Object holders are PC, NPC or Faction Content. Shared-party possession
links to the party's Faction. Lists represent split sets. `GONE` means the object
has left play, for example through sale, loss, destruction or consumption.

## Body and campaign history

All subtypes share Notes, Active Clues and Appearances, in that order. Notes contain
established information. A Clue is a candidate fact; displaying it under Active
Clues does not establish it as world canon.

Store campaign state in separate `campaign_1:`, `campaign_2:`, etc. blocks. The
initial template includes campaign 1; retain, remove or add blocks according to
the entry's recorded state. Each existing block requires `first_session` and
`last_session`: both empty before appearances, otherwise links to the earliest
and latest Sessions in that campaign's history.

Separate shared histories under headings such as `### campaign_1`. Record actual
interaction, not mentions/prep, and noteworthy PC contributions rather than
attendance. Keep acquisition and transfer history in Session records when current
possession changes.

The included Active Clues query targets campaign 1. For another campaign, copy it
into a separately labeled subsection and update the campaign path.

## Schema

The [Content schema](../schemas/content.schema.json) describes a parsed note as
`{frontmatter, body}`. Fill in the subtype and required fields before treating a
copied template as a record. See the [parsed-note contract and standalone schema checks](../schemas/README.md).

The body regex checks heading order; duplicate headings and matching headings
inside code fences can satisfy it. Link existence, target types, campaign agreement
and consistency with Appearances require separate vault-aware checks. Enable URI
format assertions to check URL syntax locally.
