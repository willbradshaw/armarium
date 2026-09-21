# Initial work programme (draft)

These are candidate GitHub issues. Their sequence is a proposal, not a settled
architecture. Each should become a concrete issue after the relevant design
discussion; unresolved choices should remain explicit in the published issues.
Section numbers identify work items, not GitHub issue numbers; published issues
are linked explicitly.

## 1. Specify the vault boundary and content ownership

Define the default organization of references, world material, campaign records,
templates, instructions, assets, and working files.

Confirmed: a vault supports multiple campaigns sharing world information, similar
to Isles. This issue resolves the detailed layout and state model, not whether
multi-campaign vaults are supported. Tracked in [GitHub issue #1](https://github.com/willbradshaw/armarium/issues/1).
The owner prefers `world/` for shared world content and has accepted per-campaign
metadata blocks on shared pages; specify the remaining details within those choices.

Acceptance:
- Show a minimal example tree and explain the purpose and owner of each area.
- Walk through starting a campaign, starting a second campaign, and reusing lore.
- Specify campaign selection for scripts and skills; avoid a hardcoded campaign
  identifier or ambiguous writes when several campaigns exist.
- Decide how names and links distinguish entities across campaigns.
- Explain where changing campaign state belongs relative to reusable reference.

## 2. Define distribution, customization, and updates

Choose how users obtain the starter materials, invoke scripts, and access skills.
Compare copying, initialization, and installed tooling against actual user needs.
Terminal-based setup is accepted. Tracked in [GitHub issue #2](https://github.com/willbradshaw/armarium/issues/2).

Acceptance:
- Document the complete first-use sequence and its prerequisites.
- Identify which files users edit and which are managed by shared tooling.
- Demonstrate how a shared fix reaches an existing vault without overwriting
  custom templates, instructions, or campaign content.
- Decide version tracking, update review, conflict handling, and recovery.

Depends on work item 1 and coordinates with work item 9; additional installation
prerequisites remain to be decided.

## 3. Extract the general page conventions and templates

Build a minimal, coherent set of page types from the source examples, removing
game, setting, and campaign assumptions rather than merely replacing their names.

Review input: [conventions inventory](conventions-review.md). Items 1–15, 17–29,
and 33–36 are accepted with the recorded qualifications and expanded definitions.
Items 16 and 30–32 remain unreviewed. Reconcile source guidance with those decisions
before extraction, particularly the distinction between candidate clues and canon.

Acceptance:
- Cover sessions, transcripts, PCs, NPCs, locations, factions, lore, objects, and
  clues/open threads, explaining any types combined or deferred.
- Define required versus optional fields, empty values, links, and page naming.
- Include original examples from materially different kinds of game.
- Require neither XP, levels, classes, nor a particular calendar.
- Explain how users add fields or adapt the default style.

Depends on work items 1 and 2.

## 4. Deliver the usable starter knowledge base

Implement the chosen setup mechanism and provide navigation, templates, and local
instructions that support the default workflow from first use.

Acceptance:
- A clean setup produces a vault with resolving links and useful starting guidance.
- Setup needs no previous campaign files, game-system module, or model API call.
- Document and exercise the chosen Obsidian dependency policy.
- Existing destinations cannot be silently overwritten.

Depends on work items 1–3 and the installation decisions in work item 9.

## 5. Extract general validation and vault utilities

Separate reusable parsing, link resolution, and structural checks from campaign
paths, game rules, and personal editorial constraints.

Acceptance:
- Utilities accept an explicit target vault and the agreed conventions.
- Check unresolved/ambiguous links and malformed page structure with actionable
  locations and diagnostics.
- Support documented customizations rather than rejecting all additional fields.
- Carry forward relevant existing tests with synthetic fixtures and add tests for
  assumptions removed during extraction.
- Checks do not rewrite user content unless an explicit fix operation is selected.

Depends on work items 2 and 3.

## 6. Deliver preparation and entity-maintenance skills

Provide reusable instructions for session preparation and maintaining consistent
entity records in the chosen AI host or hosts.

Acceptance:
- Skills discover the target campaign and local conventions without hardcoded IDs.
- Support creating and updating the agreed page types.
- Distinguish preparation, proposals, mentions, and established events.
- Follow the same templates and rules as validation.
- Explain host setup and which capabilities the skills require.

Depends on work items 2–5 and 9.

## 7. Deliver the notes/transcript-to-session workflow

Adapt the existing workflow into a general process for draft notes, GM review,
session records, and consistent updates to related entities.

Acceptance:
- Accept written play notes or an existing transcript without requiring audio.
- Preserve source attribution and surface unresolved facts for GM review.
- Keep proposed/prepared scenes distinct from events established in play.
- Propagate corrections from the reviewed session into entity updates.
- Avoid duplicating updates when rerun; show changes for review.
- Specify optional audio transcription setup, or explicitly defer audio support.

Depends on work items 3, 5, and 6.

## 8. Validate and document the first complete user journey

Exercise the release as a new user, including starting a second campaign and
updating shared materials after customizing the first.

Acceptance:
- Original sample material demonstrates setup, preparation, session processing,
  entity updates, and validation end to end.
- The same core works with contrasting game styles without system adapters.
- A second campaign does not inherit private records or state accidentally.
- An update preserves a deliberate user customization.
- Publish a quickstart, customization guide, troubleshooting guidance, contribution
  instructions, and the selected license for distributable project materials.

Depends on work items 4–7 and 9, and the licensing decision.

## 9. Design agent portability and optional model API support

Support Claude Code and Codex at minimum, aiming for broad drop-in portability
across skill-capable coding agents. Investigate host integration separately from
provider support in any retained model-calling scripts.

Scope and acceptance criteria: [agent portability](agent-portability.md).
Tracked in [GitHub issue #3](https://github.com/willbradshaw/armarium/issues/3).

Coordinate with work item 2; this design precedes the relevant parts of starter
setup and skill extraction. Its position here does not imply it runs last.
