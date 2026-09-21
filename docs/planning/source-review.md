# Source review

Initial inspection, 2026-09-20. This is planning evidence, not an agreed architecture
or a claim that the existing implementations have been fully audited.

The workspace contains three local reference projects. They are inputs to design;
their campaign content and imported source collections are not project assets.

## Confirmed product scope

The owner intends a fully system-general resource providing templates, a file
structure, and general skills and scripts. It is not tied to any game system,
setting, or campaign. The existing projects supply evidence and reusable patterns;
their particular conventions are not requirements for the new resource.

The general resource must be useful without choosing or installing a supported
system profile. System-specific importers may be considered separately, but are
not an agreed initial deliverable or the organizing principle of the core.
Packaging as a copied tree, a generator, or installed tooling remains undecided.

The owner has chosen a coherent default workflow that users can customize, rather
than a collection requiring users to assemble their own workflow from scratch.
Terminal-based setup is acceptable, including with an AI assistant's help. The
confirmed public repository is `willbradshaw/armarium`.
A single vault can support multiple campaigns sharing world information, similar
to Isles. Exact folder names and shared-entity state handling remain undecided.

## Isles: primary reference

The most developed example combines an Obsidian vault, Python utilities, agent
skills, and substantial setting and campaign content.

- `docs/vault-conventions.md` distinguishes world-persistent entities from campaign
  state. Root-level reference pages can also carry campaign-specific metadata.
- `docs/specs/content.md` describes a shared entity structure, stable summaries,
  session appearances, and propagation of established facts into entity notes.
- `templates/` contains useful starting structures, but embeds campaign identifiers,
  a campaign name, D&D mechanics, and particular editorial preferences.
- `.claude/skills/` covers preparation, transcript processing, session writing,
  entity maintenance, imports, and handouts.
- The transcript workflow separates transcription, extraction, GM review, session
  writing, and updates to related entities. Preserving the distinction between
  established events and inferred or proposed content is a reusable requirement.
- `scripts/lib/` offers candidates for shared parsing, indexing, rendering,
  transcription, storage, and model-call infrastructure.
- `scripts/lint/` mixes general vault integrity checks with system mechanics,
  setting calendars, page schemas, and house style.
- Content import pipelines separate fetching, annotation, and rendering. Their
  protection of handwritten material and campaign state is valuable precedent
  for both reference updates and future toolkit upgrades.
- Existing Obsidian configuration includes Dataview and several D&D-oriented
  plugins; required versus optional dependencies need deliberate selection.

## Imperium Maledictum: portability evidence

The campaign already reuses the transcript-to-session workflow and similar Python
checks, but with simpler entity and session templates. Its session workflow omits
the Isles XP apparatus. This is a useful second case for separating general
workflows from system rules and GM preferences.

Candidate extraction should compare both implementations rather than assume that
every Isles convention belongs in the universal core.

## Museion: contrasting reference and authoring workflow

The Pathfinder project has structured source extraction, Archives of Nethys
parsers, trait normalization, and generated Obsidian entries. It also contains
extensive setting-specific creative workflows for galleries and encounters.

Its import scope is driven partly by the setting: creatures, objects, and hazards
are prioritized, while spells are generally linked externally. These choices
should not become defaults for all Pathfinder campaigns.

## Decisions to work through

1. Primary audience and acceptable installation requirements.
2. How a shared-world vault organizes multiple campaigns and their distinct state.
3. How reference collections are reused without sharing mutable campaign state.
4. Distribution: copied starter materials, installed utilities, and skill delivery.
5. Ownership and update rules for templates, generated files, and local overrides.
6. Boundaries between universal conventions, system rules, setting choices, and
   GM preferences.
7. Initial end-to-end milestone for the system-general resource.
8. Supported agent hosts and Obsidian dependencies.
9. Public distribution scope, project licensing, and synthetic example fixtures.

## Candidate acceptance scenarios

These are proposals to refine with the project owner:

- Start a fresh campaign without copying and editing a previous campaign's scripts.
- Start a second campaign without leaking the first campaign's notes or state.
- Process a sample transcript into reviewed session notes and consistent entities.
- Update shared tooling while preserving campaign-specific customizations.
- Use the common workflow for an arbitrary or homebrew system without needing a
  system adapter, class/level fields, XP rules, or a particular setting calendar.
- Customize templates and conventions for different games without modifying the
  shared utilities themselves.

Reference-import refresh behavior is a potential later extension, not an agreed
core acceptance scenario.
