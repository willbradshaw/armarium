# Initial implementation plan

Status: proposed sequence for owner review, not authorization to begin implementation.
This sequences the [work programme](work-programme.md) around the accepted
[conventions](conventions-review.md). Numbers below are plan steps, not issue IDs.

## First usable release

A GM can create an Obsidian vault, add two campaigns sharing world information,
prepare sessions, turn notes or recordings into reviewed session records, and keep
related entities consistent. Claude Code and Codex can use the same conventions
and workflows. Shared-tool updates preserve local customizations. The general
workflow requires no game-system adapter.

All implementation lands through working branches and user-merged PRs. Source
vaults remain reference inputs; this plan does not migrate them. Use original
fixtures rather than publishing campaign records or imported corpora.

## 1. Specify the vault layout, metadata, and ownership rules

Build on issue [#1](https://github.com/willbradshaw/armarium/issues/1). Specify
`world/`, campaign folders, reference material, templates, shared instructions,
assets, intake, and scratch areas. Define campaign identity and selection, page
names and collisions, linked types, per-campaign metadata on shared entities,
and how appearance logs distinguish campaigns.

Specify the clue lifecycle with candidate facts distinct from established canon.
Identify where conventions are configurable. Settle source-retention defaults
and select licensing for the distributable materials. Resolve conventions 30–31
before finalizing writing instructions; treat the optional worldbuilding interview
workflow (32) as a separate scope decision.

**Complete when:** a documented example with two campaigns explains every page's
location, ownership, and relevant state, including a shared entity with different
campaign histories and an abandoned clue that never became canon.

## 2. Design distribution and prove the minimum agent integrations

Resolve issues [#2](https://github.com/willbradshaw/armarium/issues/2) and
[#3](https://github.com/willbradshaw/armarium/issues/3). Choose the setup mechanism,
shared-script packaging, local skill/instruction delivery, version recording,
customization precedence, and update/conflict behavior.

Prototype one small skill that reads the campaign context and invokes a harmless
local check in both Claude Code and Codex. Specify how common instructions are
maintained once and adapted where hosts differ. Inventory any direct model API
calls in candidate utilities; retain only those justified by the initial workflow,
with explicit model/provider configuration and optional dependencies.

**Complete when:** both hosts can discover and use the prototype, and a new-user
installation plus existing-vault update can be described without unresolved file
ownership questions. Additional agent support has a documented extension path.

**Dependency:** the initial contract from step 1; design can iterate alongside it.

## 3. Prototype the live views in Obsidian

Execute issue [#5](https://github.com/willbradshaw/armarium/issues/5): replace clue
indexes, entity Active Clues, sessions referencing a clue, and session preparation
tables with Bases prototypes. Use explicit preparation-selection lists rather than
all outbound session links.

Test rendering, campaign isolation, linked text, row order, live refresh, manual
editing, and agent access to underlying data. Decide separately for each view
whether Bases is sufficient. Keep generated Markdown tables or inline Dataview
as documented fallbacks.

**Complete when:** actual Obsidian checks support the chosen views and dependency
policy. Templates can be finalized without guessing how their live sections work.

**Dependency:** the relevant draft schema from step 1. Can run alongside step 2.

## 4. Extract the coherent starter templates and conventions

Extract and reconcile current Isles templates, the content spec, and relevant
skills, using the other projects to expose assumptions that are not general.
Cover campaign and player records, sessions, transcripts, PCs, NPCs, locations,
factions, lore, objects, clues, and linked type/status pages.

Preserve accepted entity structure and recent Isles session organization, with
the views selected in step 3. Remove required D&D fields, campaign names, calendar
rules, and personal defaults not selected for Armarium. Distinguish clues from
open threads. Specify supported extensions so templates and validators agree.

**Complete when:** a small hand-populated starter vault demonstrates the agreed
page types and links, needs no system-specific module, and carries no references
to private source content or hardcoded source-campaign identifiers.

**Dependencies:** steps 1–3, with prose decisions settled for affected instructions.

## 5. Implement vault creation and adding campaigns

Implement the distribution design, including a new-vault operation and an
add-campaign operation. Proposed CLI names such as `init` and `campaign add` are
illustrative until step 2 settles the interface.

Install the templates, views, selected host instructions, and shared utility
access; record versions and local configuration. Setup should make no model API
calls. Require unambiguous campaign selection and refuse to silently overwrite
existing files. Keep reusable world content when adding another campaign.

**Complete when:** a fresh install produces a usable vault and adds two distinct
campaigns; collision/retry checks demonstrate that existing work is preserved.

**Dependencies:** steps 2 and 4.

## 6. Extract general validation and entity-review utilities

Extract the shared vault parsing/link-resolution machinery and accepted checks:
broken or ambiguous links, malformed table links, metadata shape, campaign/session
identity, clue subjects and states, and qualifying appearance dates. Add a
post-session sweep that surfaces candidate entity updates without pretending to
decide relevance mechanically.

Retain relevant tests using original fixtures. Exercise valid custom fields,
duplicate names, two campaigns, and the candidate-clue distinction. Keep validators
read-only by default; report actionable paths and distinguish errors from warnings.

**Complete when:** the starter passes, deliberately inconsistent fixtures produce
useful diagnostics, and ordinary supported customizations are accepted.

**Dependencies:** steps 1 and 4. Can overlap step 5.

## 7. Implement entity maintenance and session preparation skills

Deliver the shared skills and host integrations for entity creation/updates,
clue management, and preparation. Use current Isles carryover behavior: read prior
play, collect unresolved material, then collaborate on new preparation. Preserve
the distinction between candidate facts, established world facts, planned scenes,
and events that actually happened.

Connect skills to the agreed templates, views, validation, and explicit campaign
context. Follow the accepted review checkpoints and branch/PR workflow where used.

**Complete when:** Claude Code and Codex can prepare a session and maintain its
entities in the fixture vault, including a second campaign, without editing
another campaign's state or promoting abandoned clues to canon.

**Dependencies:** steps 2, 5, and 6.

## 8. Implement the session recording/notes workflow

Extract the recent Isles sequence: optional audio transcription and cleanup,
campaign-local cast/name glossary, attributed Transcript page, beat extraction,
actual Events draft, GM correction and explicit go-ahead, Session entry, and
entity sweep. Support starting from written notes or an existing transcript.

Separate optional transcription dependencies from ordinary vault use. Preserve
uncertainty, check draft claims against source material and prior play, and derive
entity changes from the final reviewed session. Reapply later corrections without
duplicate log entries. Retain raw inputs according to the chosen policy.

**Complete when:** original sample notes and a short original recording both reach
reviewed session/entity records on the required hosts, including an uncertain
speaker, a corrected event, an unrevealed clue, and a safe rerun. Record any bounded
audio-support limitation explicitly rather than implying broader provider support.

**Dependencies:** steps 6–7 and the prose decisions from step 1.

## 9. Implement and verify the update/customization lifecycle

Finish the update mechanism designed in step 2. Track installed versions and
managed material, show proposed changes, preserve user-owned pages and overrides,
and report conflicts rather than overwriting custom templates or skill changes.
Provide a documented recovery path for unsuccessful updates.

**Complete when:** an older fixture with a customized template, local instruction,
and two active campaigns adopts a shared-tool fix without losing its edits or
changing campaign records. Repeating the update produces no unnecessary changes.

**Dependencies:** the distribution contract in step 2 and implementation from
steps 5–8. Edit-protection rules apply from the first implementation, not only here.

## 10. Exercise the whole journey and prepare the first release

Run fresh-install and existing-vault scenarios with contrasting game styles,
both required agent hosts, and two campaigns sharing world information. Exercise
setup, preparation, session processing, correction propagation, validation,
adding another campaign, and an upgrade with customizations.

Write the quickstart, page/workflow reference, customization and upgrade guides,
host/plugin requirements, troubleshooting, and contribution guidance. Include the
selected license and original sample material. State tested platforms and known
limits; prepare release artifacts for review through a PR.

**Complete when:** another GM can follow the documented journey without access to
the private reference projects, and checks demonstrate the claimed behavior.
Publishing a release is a separate action after review.

**Dependencies:** steps 5–9.

## Sequence and scope

Begin with step 1, then run the agent/distribution and Bases investigations (2–3)
alongside each other. Finalize templates (4), implement setup and checks (5–6),
then complete preparation, session processing, updates, and release validation
(7–10). Early research must resolve the decisions it affects; it need not block
unrelated work.

System-specific importers, migration of existing campaigns, shared reference
synchronization between independent vaults, a plugin marketplace, and a custom
Obsidian plugin are proposed follow-on work rather than initial-release requirements.
Worldbuilding interviews await the owner's convention-32 decision. These scope
recommendations are part of this plan for review, not previously agreed exclusions.
