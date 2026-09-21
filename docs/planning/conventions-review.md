# Conventions for owner review

Status: **1–15, 17–29, and 33–36 accepted**, subject to the decisions below.
**16: Bases-first prototype agreed; final dependency choice awaits its results.**
**30–32 await review.** Prefer **`world/`** for shared world content.
Based on inspection of Isles' conventions,
templates, skills, and tooling runbooks. This is a behavioral inventory, not a
completed audit of whether the current code enforces every instruction.

For each numbered item, choose **default**, **optional**, **omit**, or **revise**.
The recommendations column retains the original review advice; its implementation
suggestions are not additional owner decisions. "Optional" means an available convention
that is not required of every campaign; how options are configured remains open.

The acceptance of 7, 10, and 11 resolves the corresponding source disagreements:
use the common entity body, exclude incidental mentions from appearance logs, and
record noteworthy PC contributions rather than attendance alone. The acceptance
of 3 and 5 selects per-campaign metadata blocks on shared pages and linked type
pages. Detailed naming, layout, and multi-campaign history rendering still need
specification. Accepting Active Clues in the common shape does not settle the
later questions about clue behavior or Dataview.

## Subsequent owner decisions

- **16:** prototype Bases for clue indexes, entity Active Clues, sessions referencing
  clues, and session preparation tables. Use explicit prep-selection lists for the
  latter. Verify behavior in Obsidian before choosing dependencies; generated
  Markdown or retained inline Dataview are fallbacks. Tracked in [issue #5](https://github.com/willbradshaw/armarium/issues/5).
- **17–19:** follow recent Isles session structure and preparation conventions.
  Use the current Session template and preparation/writing skills as the extraction
  baseline. Preserve the Preparation/Notes split, starting scene, other scenes,
  secrets and clues, locations, important NPCs, scene notes, and the post-play
  preamble/events/rewards organization. Extract encounter/reward support without
  making D&D mechanics mandatory. Carryover precedes collaborative new preparation.
- **20:** accepted canon discipline.
- **21:** a clue is a persistent GM-known **candidate fact** not fully known to
  players. It may be abandoned without revelation and may never become canon.
  Writing or approving a clue for prep does not by itself establish world truth.
- **22–24:** accepted lifecycle, canonical clue text/subjects, and revelation
  updates, subject to the candidate-fact correction. An abandoned candidate must
  not be promoted into world/entity facts. Retiring a clue is not itself evidence
  for undoing facts already established independently.
- **25–29:** follow recent Isles transcript/session workflow, including actual
  draft Events review, explicit go-ahead after corrections, propagation from the
  reviewed session, entity sweep, cast/name glossary, and uncertainty handling.
  Source claims are checked against the transcript and previous session before
  presenting the draft. Remove fixed campaign IDs and system rules; adapt execution
  to host capabilities. This does not settle the separately unreviewed prose/style
  items 30–31 or introduce the session workflow's checkpoints into project planning.
- **33–35:** accepted as expanded below: concrete integrity checks, repeatable
  operations that preserve edits, and explicit working-file storage responsibilities.
- **36:** accepted the offered branch/PR workflow for campaign users. Armarium's
  own development requires working branches and user-merged PRs for every change.

## Accepted clarifications for 33–35

**33 — Concrete integrity checks:**

- Report missing or ambiguous link targets and malformed links in Markdown tables.
- Check page metadata against the agreed type schema and campaign namespace.
- Check session IDs, campaign links, and corresponding session numbers agree.
- Check each clue's subject list matches its canonical text's entity links and its
  state is allowed. A checker cannot decide whether a candidate is true or revealed.
- Check first/last-session fields agree with qualifying appearance records under
  the chosen conventions; preserve type-specific semantics for clue tracking.
- Keep the post-session sweep as a review aid for missing/stale entity updates;
  a reference alone does not prove an appearance.

These are agreed check requirements, not a claim that all exist today. Report
file locations and distinguish structural errors from review questions. D&D XP
arithmetic, the Isles calendar, and personal prose rules do not become universal
checks. Define exception handling and test the checks against ordinary valid pages.

**34 — Repeatable operations without lost edits:**

- Adding a campaign or refreshing shared materials cannot overwrite an existing
  session, entity, or customized template silently.
- If an operation generates part of a page, declare what it owns. For example,
  refreshing a reference section preserves the GM's Notes and campaign metadata.
- If the GM edited the generated portion itself, surface a conflict for review
  rather than guessing which version to keep.
- Repeating an operation with unchanged inputs should not rewrite files or append
  duplicate appearance bullets. Shared-material updates should show a reviewable diff.

Isles' import renderers supply a useful example of protecting human edits; Armarium
does not need to adopt their precise hash mechanism or include importers to keep
this behavior. One-time starter templates can simply become user-owned files.

**35 — Distinct storage responsibilities:**

- Incoming recordings, raw transcripts, and source documents have an intake area
  with an explicit processed/unprocessed distinction.
- Working beat extractions, draft text, and sweep checklists have a scratch area;
  their presence does not make them canonical knowledge-base pages.
- Cleaned Transcript and Session pages live in the relevant campaign; durable
  maps, images, and handouts live in a visible assets folder suitable for embedding.
- Exclude temporary working material from normal Git publication by default.
  Raw-source retention and any deletion require a defined policy; marking input
  processed does not authorize deleting it. Exact folder names remain open.

## Organization and identity

| ID | Convention to review | Recommendation |
| --- | --- | --- |
| 1 | One vault holds world information shared by multiple campaigns, each with its own sessions and records. | Already agreed. |
| 2 | Place persistent world entities outside campaign folders; put campaign-bound entities inside them. The same entity type can appear in either scope. | Default; determine scope by intended reuse rather than assuming all cities are shared and all buildings campaign-bound. |
| 3 | Put each campaign's state on shared pages in its own metadata block: first/last session, current holder, etc. | Default candidate; review how corresponding appearance logs are separated and how conflicting timelines are represented. The multi-campaign requirement does not itself settle this representation. |
| 4 | Name entity files by canonical names, but sessions and clues by stable, campaign-qualified sequential IDs; use aliases for alternate names. | Default; make exact prefixes and number padding conventions configurable and specify name-collision handling. |
| 5 | Give every entity a type in frontmatter, expressed as a link to a type page, such as `type: "[[NPC]]"`. | Default candidate; decide whether type pages earn their place or plain type values suffice. |
| 6 | Create minimal stub pages for referenced entities whose details are unknown, without inventing the missing content. | Default, with deliberate deferral allowed rather than compulsory expansion of every reference. |

## Entity records and history

| ID | Convention to review | Recommendation |
| --- | --- | --- |
| 7 | Use a common entity body: Notes, Active Clues, Appearances, with type-specific metadata. | Default shape; make Active Clues conditional on using the clue workflow. Reconcile older skills that prescribe separate Appearance/Background/Personality sections. |
| 8 | A short summary describes stable identity or traits; temporary circumstances belong in state fields or history. | Default. |
| 9 | Date changing world facts and avoid an implicit present: e.g. a ruler held office in a specified year. Stable facts can use present tense. | Default principle; exact tense and date granularity customizable. |
| 10 | Record actual appearances/interactions separately from mentions: NPCs act on stage, places are visited, objects are used, factions act collectively. Backlinks capture incidental mentions. | Default candidate; source guidance conflicts on whether mentions enter the appearance log. |
| 11 | PC history contains only noteworthy contributions, rather than an automatic bullet for attendance. | Default candidate; source guidance also calls for every present PC to have an entry. Owner choice needed. |
| 12 | Keep session acquisition records as historical snapshots; track current possession separately on the item. | Default. Decide the representation of shared party ownership rather than assuming a blank holder is sufficient. |

## Links, metadata, and live views

| ID | Convention to review | Recommendation |
| --- | --- | --- |
| 13 | Link named entities consistently, reuse existing pages, and preserve links when rewriting prose. | Default; review whether literally every occurrence needs a link. |
| 14 | Use consistent frontmatter: quoted wikilinks, defined field types, and bare empty values where the schema expects null. | Default. Keep exceptions explicit, such as an empty string for clue text. |
| 15 | Links target canonical page names; alternate display text is explicit, with pipes escaped inside Markdown tables. | Default. Avoid relying on bare alias text to identify the target. |
| 16 | Provide live summaries, clue displays, and indexes from authoritative source pages. | Revised: prototype Bases first under issue #5; choose the final implementation based on rendered results and usability. |

## Preparation and authority

| ID | Convention to review | Recommendation |
| --- | --- | --- |
| 17 | A session page has separate Preparation and Notes halves. Unplayed prep remains prep; unexpected events do not retrospectively become planned scenes. | Default. |
| 18 | Prepare a starting scene and a menu of possible scenes, plus relevant people, places, clues, and encounters. | Default template, with sections removable when they do not suit a campaign. |
| 19 | Begin preparation by reviewing the previous session and carrying forward unresolved scenes, open clues, cliffhangers, and unfinished encounters. | Default; propose carryover for review rather than blindly duplicating everything. |
| 20 | Separate recovery of existing facts from invention. Source-based updates do not add plausible details; new creative proposals require GM adoption before becoming canon. | Default principle; whether every new detail needs a separate approval is a distinct workflow preference. |

## Secrets and clues

| ID | Convention to review | Recommendation |
| --- | --- | --- |
| 21 | A clue is a persistent GM-known candidate fact not fully known to the players. It may be abandoned without revelation and never become canon. | Accepted with the owner's candidate-fact correction. Do not treat a prep clue as established world truth or conflate clues with generic open threads. |
| 22 | Clues have a lifecycle: Pending, Hinted, Revealed, Abandoned, with Dormant and Superseded also referenced in newer templates/specs. | Optional workflow; reconcile the exact vocabulary and transitions. |
| 23 | Each clue has one canonical text field and a subject list matching its entity links; subject and session pages display that text rather than copying it. | Default within the clue workflow. |
| 24 | Unrevealed clue text stays in its clue page; on revelation, incorporate relevant facts into substantive subject pages with a clue back-reference. | Default within the clue workflow, but specify which parts of world truth versus campaign knowledge can safely be shared across campaigns. |

## Session processing and writing

| ID | Convention to review | Recommendation |
| --- | --- | --- |
| 25 | Process a recording through transcription/cleanup, event extraction, GM review, session writing, and related-entity updates; allow entry at a later stage with existing notes or a transcript. | Default workflow. |
| 26 | The GM reviews the actual proposed Events text before it updates the session and other entities. Isles requires a separate explicit go-ahead after corrections, not just answers to clarification questions. | Accepted: follow the recent Isles session workflow. |
| 27 | After review, the session account is the authoritative source for derived appearance logs. Later corrections propagate from the revised account, not working drafts or memory. | Default; retain links to underlying source material for later factual re-checking. |
| 28 | A post-session sweep checks related entities, including those referenced through newly created pages; update both history and newly established durable facts. | Default; tools identify candidates, with judgment determining which actually need updates. |
| 29 | Maintain a campaign-local cast/name glossary, normalize transcription errors, label speakers, preserve uncertainty, and ask about unresolved significant claims. Clean filler without turning the transcript into a summary. | Default when transcription is used; labels, chunk sizes, and execution strategy need not be universal. |
| 30 | Session Events describe the fiction, keeping mechanical numbers and player logistics in separate sections. | Default candidate; allow campaigns to retain mechanics in the narrative if desired. |
| 31 | Use chronological, past-tense, self-contained event bullets; terse entity logs; explicit actors and linked names; match the campaign's existing voice. Isles adds sentence limits and bans particular constructions and punctuation. | General readability principles as defaults; exact prose and typography rules customizable. |
| 32 | For worldbuilding, read existing canon first, interview the GM about gaps, develop proposals iteratively, and propagate accepted edits to related pages. | Optional authoring workflow. Do not carry over a mandatory interview length, multiselect UI, or number of name suggestions. |

## Validation and maintenance

| ID | Convention to review | Recommendation |
| --- | --- | --- |
| 33 | Validate links, metadata, and cross-page consistency; distinguish blocking errors from warnings and record reasons for exceptions. Keep factual/editorial review separate from mechanical checks. | Default; make personal style checks configurable and define a sensible scope for recursive link checks. |
| 34 | Distinguish generated content from user-owned material. Repeat runs should converge without unnecessary writes, and regeneration must preserve local edits and campaign state. | Default principle wherever generation exists; importing the current hash-based mechanism is a separate implementation choice. |
| 35 | Separate temporary inputs and scratch work from durable pages and embeddable assets; distinguish unprocessed from processed source material. | Default distinction; retention and deletion policies need an explicit choice. |
| 36 | Work on a branch, review the diff, and deliver changes through a PR that the GM merges; retain style decisions for subsequent work. | Git/PR workflow optional. Keep reusable local preferences, but do not automatically promote every one-off correction into a universal rule. |

## System and setting assumptions to remove from general defaults

- Required classes, levels, subclasses, challenge ratings, spellcasting fields,
  fixed XP calculations, and special magic-item or scroll workflows.
- The Isles calendar hierarchy and mandated year/tetrant/day formats.
- Default species/ethnicity, campaign IDs and names, and setting naming rules.
- The assumption that an absent player's PC remains with the party and receives
  the same rewards. This is a table policy, not a general structural convention.
- The hard rule that any narrative object acquiring mechanics must move to a
  separate Gear type. Armarium should decide its general reference/entity model
  without inheriting that D&D-oriented split automatically.
- Particular scraping sources, credentials, and model/provider choices.

These exclusions concern the defaults; they do not prohibit users from adding the
corresponding fields, rules, or optional workflows.

## Conflicts to reconcile before extraction

The source projects have evolved. These discrepancies are evidence for a
reconciliation task, not evidence that either document expresses the owner's
current preference:

1. **Entity body:** `docs/specs/content.md` and current PC/Object templates use the
   common Notes/Active Clues/Appearances structure, while older per-type skills
   still describe different sections.
2. **Mentions:** `docs/vault-conventions.md` includes mentions in appearance logs;
   the content spec excludes them.
3. **PC logs:** the PC skill and vault conventions say noteworthy actions only;
   `write-session-entry/entry-style.md` calls for an entry for each present PC.
4. **Clue states:** the clue skill lists four states; current query templates and
   the content spec also refer to Dormant and Superseded.
5. **Prep authority:** the content spec allows authoritative GM prep in Notes for
   all content types; the location skill also contains older distinctions between
   objective locations and NPC traits awaiting play. Canonical world facts and
   events that actually occurred need separate definitions.
6. **Aliases:** the general conventions suggest automatic alias resolution, while
   the session-writing skill explicitly requires canonical targets with display
   aliases. The general implementation should verify the chosen behavior.

## Source map

Paths below refer to the local Isles reference project, whose content is not
included in this repository. They identify inspected evidence, not public links.

| Review items | Main source paths within Isles |
| --- | --- |
| 1–6, 13–16, 35 | `docs/vault-conventions.md`; `templates/`; `CLAUDE.md` |
| 7–12 | `docs/specs/content.md`; `.claude/skills/manage-{pc,location,object}-entry/SKILL.md`; `.claude/skills/write-session-entry/SKILL.md` |
| 17–20 | `.claude/skills/prepare-session-entry/SKILL.md`; `.claude/skills/write-session-entry/SKILL.md` |
| 21–24 | `.claude/skills/manage-clue-entry/SKILL.md`; `templates/Clue.md`; `templates/Content.md`; `docs/specs/content.md` |
| 25–29 | `.claude/skills/create-transcript-entry/SKILL.md`; `.claude/skills/process-session-transcript/SKILL.md`; `.claude/skills/write-session-entry/SKILL.md` |
| 30–31 | `.claude/skills/write-session-entry/entry-style.md`; `.claude/skills/write-session-entry/SKILL.md` |
| 32 | `.claude/skills/dm-interview/SKILL.md` |
| 33–36 | `CLAUDE.md`; `.claude/skills/write-session-entry/SKILL.md`; `docs/gear-pipeline.md`; `docs/pr-conventions.md` |
