# Product brief

Status: early planning. Confirmed decisions and proposals are distinguished below.
The project is Armarium, published at <https://github.com/willbradshaw/armarium>.

## Confirmed direction

Provide a fully system-general foundation for AI-assisted TTRPG knowledge bases:
templates, a file structure, and general skills and scripts. Deliver a coherent
default workflow that people customize. Starting another campaign should not
require reconstructing tooling and conventions from a previous campaign.

Terminal-based setup is acceptable, including with an AI assistant's help.

The setup mechanism copies a canonical starter vault and populates campaign-specific
values. The starter contains the agreed structure, templates, type/status pages,
navigation, and default instructions/configuration, with example campaign content
kept separately. Shared executable utilities are installed outside the copied
content. Every implementation issue must deliver an inspectable artifact with
explicit acceptance tests and recorded results; design prose alone is insufficient.

Claude Code and Codex are the minimum supported coding agents. Broad drop-in
portability across skill-capable coding agents is the goal; the delivery mechanism
and compatibility details are a dedicated design work item. If reusable scripts
retain model API calls, provider portability is considered separately from agent
host support. See [agent portability](agent-portability.md).

A single vault can support multiple campaigns sharing world information, following
the existing Isles model. Starting another campaign within a vault must reuse its
world information and established tooling and conventions. Prefer a `world/`
folder for shared world content, with campaign-bound entities in campaign folders.
Shared pages carry per-campaign metadata blocks. Exact subfolders, name-collision
handling, and multi-campaign history rendering remain to be specified.

The owner has accepted conventions 1–15 in the [conventions review](conventions-review.md):
canonical entity names and campaign-qualified record IDs, linked type pages,
minimal stubs, a common Notes/Active Clues/Appearances body, stable summaries,
dated changing world facts, interaction-based appearances, noteworthy PC logs,
separate historical acquisition records and current possession, consistent entity
linking, defined metadata types and empty values, and canonical link targets with
explicit display aliases.

Conventions 17–29 are also accepted: use recent Isles session structure and
preparation/transcript-processing workflows, extracting them without mandatory
system mechanics. Clues are candidate facts: an unrevealed clue may be abandoned
and never become canon. The reviewed session account drives entity updates, with
explicit GM approval of revised Events before propagation. Campaign users are
offered a branch/PR workflow (36); Armarium development requires branches and
user-merged PRs for all changes. The expanded conventions 33–35 are accepted:
specific structural and cross-page checks, repeatable operations that protect
local edits and avoid duplicate records, and separate intake, scratch, durable
campaign records, and assets. Source retention and deletion policy remain to be
specified. Convention 16 now has an agreed Bases-first prototype, with the final
view/dependency choice based on its results ([issue #5](https://github.com/willbradshaw/armarium/issues/5)).
Only conventions 30–32 remain unreviewed.

The resource must work without a system adapter and without assumptions about
classes, levels, XP, spellcasting, a particular calendar, setting, or campaign.
Existing projects are design references, with Isles the primary example. Their
particular structures and editorial conventions are not automatically defaults.

This session is for planning, repository creation, and an initial issue programme.
It is not an instruction to implement the toolkit or migrate existing campaigns.

## Proposed default journey

1. Create a knowledge base with working templates, navigation, instructions, and
   access to the shared skills and utilities.
2. Add setting information and reference material, preserving its provenance.
3. Start a campaign and create its characters, locations, factions, and open threads.
4. Prepare a session, keeping proposed events distinct from established events.
5. Bring in play notes or a transcript; optionally transcribe a recording first.
6. Draft session notes, resolve uncertain attribution and facts with the GM, and
   update related entities from the reviewed account.
7. Check links and structure, then review the resulting changes.
8. Start another campaign in the same vault, reusing world information, defaults,
   and chosen customizations while keeping campaign-specific records distinct.

Steps must also be usable independently: a GM can write notes without recording
audio, maintain entities without processing a transcript, or use the vault manually.

## Proposed design principles

- Markdown pages are user-owned records, readable and editable independently of
  the automation. Obsidian is the initial intended interface.
- Templates, instructions, and validation describe the same conventions.
- Shared utilities receive fixes without requiring campaign-by-campaign code edits.
- Local customizations have an explicit home and survive shared-tool updates.
- Page types provide useful defaults without enforcing mechanics from a game.
- Established facts, GM preparation, suggestions, and uncertain source claims remain
  distinguishable. Creative assistance must not silently establish campaign canon.
- The public project distributes reusable materials and original examples; local
  campaign records, credentials, and imported source collections stay separate.

## Decisions still open

- Installation prerequisites and intended audience beyond acceptance of terminal use.
- Detailed folder layout and history rendering for entities shared across campaigns.
- Whether and how independent vaults reuse reference material and setting content.
- Exact packaging and command interfaces; how shared utilities and skills are
  delivered, pinned, customized, and updated.
- Agent integration and optional model API support beyond the confirmed minimum.
- Required versus optional Obsidian plugins.
- How much of the session and entity style is a default versus a configurable rule.
- First-release scope and licensing.

System-specific importers are possible later additions, not prerequisites for the
general workflow. No plugin framework or system-profile mechanism is yet proposed
as an implementation requirement.
