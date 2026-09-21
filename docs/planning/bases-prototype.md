# Prototype Bases replacements for remaining Dataview uses

Armarium needs live clue and preparation views without requiring Dataview if
Obsidian Bases can preserve the workflow. Isles already uses Bases for gear and
monster catalogues, but still uses Dataview for clue views and inline preparation
tables. Prototype replacements for these remaining uses before choosing the
starter vault's dependencies.

The agreed direction is **Bases first**, including explicit preparation lists in
session metadata. This is a feasibility and usability task, not an instruction to
migrate the Isles vault or a commitment to remove Dataview regardless of results.

## Prototype scope

Use a small, original fixture vault with two campaigns sharing world entities.
Implement reusable `.base` files for these four cases:

| Existing use | Proposed replacement |
| --- | --- |
| Active and closed clue indexes | Campaign-scoped clue views filtered by status. |
| Active Clues on entity pages | Embedded view selecting clues whose subjects include the containing entity and whose status remains active. |
| Sessions referencing a clue | Embedded view selecting that campaign's sessions linking to the containing clue, sorted by date/session order. |
| Inline clue text and NPC/location summaries in session prep | Embedded tables selecting only the pages listed in the session's explicit preparation metadata, displaying their canonical text or summaries. |

For the fourth case, start with list properties such as `prepared_npcs`,
`prepared_locations`, and `prepared_clues`. Names are provisional. Store links,
not copied descriptions. Do not select all outbound session links: entities
mentioned only in Events must not silently appear as prepared entities.

Preserve the accepted session headings and Preparation/Notes distinction. Change
the table implementation, not the overall preparation workflow.

## Acceptance criteria

- [ ] All four cases run in Obsidian with Dataview disabled. Record the tested
  Obsidian version, enabled plugins, fixture, and reproduction steps. Reviewing
  YAML alone is not sufficient to claim the rendered prototype works.
- [ ] Shared view definitions adapt to their containing note. No fixed campaign
  ID is embedded in a supposedly reusable query.
- [ ] Each view has explicit campaign scope. A world entity shared by two campaigns
  shows each campaign's clues only in its corresponding view; define how that
  context is supplied on a page without a single campaign owner.
- [ ] Pending/Hinted clues are active; Revealed/Abandoned/Dormant/Superseded clues
  appear in the appropriate closed view. Displaying a candidate clue does not
  promote it to world canon. Render no clues from another campaign accidentally.
- [ ] Clue subject matching and session-reference matching use canonical file
  identity. Exercise aliases and identically named entities in different folders.
- [ ] Clue text and summaries containing wikilinks, punctuation, and long text
  remain readable and navigable. Verify wrapping, column widths, and empty states.
- [ ] Verify row order, including whether a GM can preserve a deliberate prep order.
  Sorting by filename is not automatically equivalent to the current selected order.
- [ ] Editing a source summary, clue text, clue status, subject list, or session prep
  list updates the appropriate rendered views. Record any refresh/reopen requirement
  and whether it is acceptable for table use; test with views already open.
- [ ] Test adding, removing, and carrying forward selected prep rows. Removing a row
  must not delete its entity page; encountering an unprepared entity must not
  retrospectively change the Preparation section.
- [ ] Both manual editing and agent-assisted preparation can maintain the selection
  lists. Document how agents read underlying records without depending on rendered
  Base output being present in the Markdown source.
- [ ] Record usability and performance observations for repeated embedded views
  and a realistically sized synthetic corpus, including mostly empty Active Clues
  sections. Distinguish measured behavior from assumptions.
- [ ] Produce a per-use-case decision with evidence, dependency requirements, and
  bounded implementation follow-ups. Document any unresolved rendering limitations.

## Fallbacks and decision

If Bases makes session preparation materially worse, evaluate:

1. **Generated Markdown tables:** a deterministic script reads selected links and
   refreshes summaries/text in clearly owned sections. Define explicit refresh,
   stale-output detection, ordering, and conflict handling. Do not overwrite GM
   edits or duplicate rows; source entity pages remain authoritative.
2. **Retain inline Dataview initially:** convert the suitable block views to Bases
   while keeping the current inline cells until a better replacement is proven.

Explain whether historical prep tables remain live or become deliberate snapshots;
do not introduce snapshot semantics accidentally during replacement. Avoid building
a general query engine or custom Obsidian plugin just to remove one dependency.

## Coordination and references

- Coordinate campaign context and page identity with #1, installation/update
  behavior with #2, and agent-visible data with #3.
- Feed the outcome into template extraction, the starter vault, preparation skills,
  and validation. Leave existing source vaults unchanged.
- [Bases overview](https://obsidian.md/help/bases)
- [Syntax and containing-note context](https://obsidian.md/help/bases/syntax)
- [Functions and link/list filters](https://obsidian.md/help/bases/functions)
- [Embedding a Base](https://obsidian.md/help/bases/create-base)
- [Table views](https://obsidian.md/help/bases/views/table)

The initial feasibility assessment used these official references; rendered
behavior has not yet been verified. Recheck documentation when implementing.
