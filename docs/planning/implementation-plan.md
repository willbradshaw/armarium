# Initial implementation plan

Status: proposed programme of work; the basic starter/fresh-path installer increment
is now implemented for review (see [acceptance evidence](../starter-acceptance.md)).
The remaining implementation work is not included in that increment. Every numbered
item maps to one issue and must deliver an inspectable artifact with recorded
acceptance evidence. A design document alone does not complete an implementation
item. Automated tests cover deterministic behavior; Obsidian and agent workflows
also require reproducible in-application checks. Missing access means a check is
unverified, not passed.

All work uses branches and user-merged PRs. Keep private source vaults unchanged
and use original fixtures. The canonical starter vault is copied and populated
by setup; reusable executable utilities are installed separately.

## 1. Extract the minimal Isles-derived starter

**Issue:** [#1](https://github.com/willbradshaw/armarium/issues/1)

**Deliverable:** An exact-copy starter with one blank campaign, agreed `world/`
grouping, source-derived templates/type/status pages, and a fresh-path installer.
Retain Isles' `campaign_1:` metadata and live Dataview queries pending evaluated
replacements. Remove private content and required game mechanics. Include an
explicit [extraction record](../starter-vault.md#extraction-record).

**Acceptance:** Test fresh installation from an unrelated directory, relocation,
resolving links, absence of unresolved placeholders, preservation of existing
content and independent Git use. Open the installed vault in Obsidian and record
actual property/link/query behavior; file-level checks alone do not pass that gate.

**Dependencies:** No preceding implementation work.

### Separate starter follow-ons

| Issue | Evaluable deliverable | Coordination |
| --- | --- | --- |
| [#13](https://github.com/willbradshaw/armarium/issues/13) | Two-campaign fixture and tested shared state/history conventions | Required for final add-campaign and two-campaign live-view integration. |
| [#14](https://github.com/willbradshaw/armarium/issues/14) | Minimal navigation justified by an Obsidian walkthrough | Develop independently; integrate against the multi-campaign fixture. |
| [#15](https://github.com/willbradshaw/armarium/issues/15) | Source-derived Player/Transcript templates and tested intake/storage example | Supplies records to #8; coordinate campaign paths with #13. |

Each is a separate PR after the baseline, and each requires actual acceptance
evidence. They can be developed alongside one another and #5. No removed schema,
landing page, manifest, or agent wrapper is presumed accepted. Metadata versions
and package configuration belong to #2, agent integration to #3, and preparation
selection and live replacements to #5.

## 2. Ship installable shared tooling and vault setup commands

**Issue:** [#2](https://github.com/willbradshaw/armarium/issues/2)

**Deliverable:** An installable, versioned shared utility package plus working new-vault and add-campaign commands that instantiate the starter vault.

Choose and implement packaging, command entry points, vault configuration, recorded versions, and the ownership boundary between managed and user-owned files. Command names remain an implementation choice. Establish the extension points for host integration and live views without blocking setup on those later artifacts. Define the upgrade contract now; deliver its complete implementation in step 9.

**Acceptance tests:**

- Install a built package in a clean environment and create a vault without access to the source projects or model API credentials.
- Add a second campaign without copying scripts into either campaign or changing shared world content.
- Exercise existing destination, duplicate campaign, missing/ambiguous campaign selection, and retry cases; no existing user files are silently overwritten.
- Invoke a packaged utility against an explicit vault from outside its directory; verify version/configuration records identify the installed materials.

**Dependencies:** Step 1 and #13 for final add-campaign integration.

## 3. Deliver and test portable agent integration

**Issue:** [#3](https://github.com/willbradshaw/armarium/issues/3)

**Deliverable:** Working Claude Code and Codex installation/invocation paths for one shared smoke-test skill, with reusable host integration and a verified compatibility matrix.

Use one maintained source for common workflow instructions and narrowly scoped host adaptations. The smoke skill resolves the target campaign, reads its conventions, and invokes a deterministic read-only check. Cover coexistence, local instruction precedence, missing host capabilities, and adding another agent. Inventory direct model API calls in candidate scripts separately and document provider/model/credential decisions only where functionality is retained.

**Acceptance tests:**

- Run the same fixture workflow in both Claude Code and Codex; record versions, commands, observed output, and required adaptations.
- Verify both agents select the intended campaign and read a local customization; neither should write to the other campaign.
- Verify installation and repeated installation preserve user-owned instructions and changes.
- Document actual verified capabilities and unsupported optional features. Do not mark host testing complete based solely on matching SKILL.md files.

**Dependencies:** Steps 2.

## 4. Deliver evaluated live views for clues and session preparation

**Issue:** [#5](https://github.com/willbradshaw/armarium/issues/5)

**Deliverable:** A runnable Bases prototype for the four remaining Dataview uses, a per-view result report, and the selected working view definitions integrated into the starter templates.

Execute the existing Bases-first prototype specification. Use explicit prep-selection lists. Prefer Bases where the actual workflow is satisfactory; if needed, implement the selected bounded generated-Markdown or retained-inline-Dataview fallback rather than leaving the template unusable. Record final dependencies. Do not migrate Isles.

**Acceptance tests:**

- Exercise all four view cases in Obsidian with Dataview disabled for the Bases experiment; record actual successes and failures, not just YAML validity.
- Check two-campaign isolation on shared entities, candidate-clue status filters, canonical identity, linked-text readability, ordering, and refresh with views open.
- Demonstrate adding/removing prep entries and carryover without altering Events or deleting entities.
- Re-run the chosen implementation in the starter example; document required plugins and any fallback semantics, including live versus historical snapshots.

**Dependencies:** Step 1; coordinate final two-campaign integration with #13.

## 5. Ship vault validation and the post-session entity sweep

**Issue:** [#6](https://github.com/willbradshaw/armarium/issues/6)

**Deliverable:** Read-only validation commands with actionable diagnostics, a session-to-entity review report, and a fixture-based test suite.

Extract reusable parsing and link resolution and the accepted checks: broken/ambiguous links, Markdown table links, metadata schemas, session/campaign IDs, clue subjects/states, and qualifying appearance dates. Preserve type-specific clue tracking semantics and supported custom fields. The sweep identifies candidates; it does not treat every mention as an appearance or decide whether a clue is true.

**Acceptance tests:**

- The starter and valid customized fixtures pass with no writes.
- Independently malformed fixtures produce the expected file-specific errors or warnings, including name collisions and wrong-campaign references.
- Verify clue subject mismatches and inconsistent appearance metadata are detected without requiring D&D XP or an Isles calendar.
- Verify the sweep includes direct and relevant indirectly referenced entities while leaving decisions and source pages untouched.

**Dependencies:** Steps 1, 2, 4.

## 6. Deliver entity-maintenance and session-preparation skills

**Issue:** [#7](https://github.com/willbradshaw/armarium/issues/7)

**Deliverable:** Installed shared skills for entity creation/updates, clue management, and recent-Isles-style preparation, working on both required agents.

Implement carryover review followed by collaborative new preparation using the agreed templates and live views. Maintain separate world/campaign state and distinguish candidate facts, accepted world facts, prepared scenes, and played events. Apply local conventions, deterministic checks, and review checkpoints. Conventions 30–31 must be decided before embedding any unreviewed prose defaults.

**Acceptance tests:**

- Run the same original scenario on both agents: create entities, prepare a session, carry forward unresolved material, and abandon an unrevealed clue.
- Verify existing IDs and entities are reused, links resolve, and preparation does not mutate past Events.
- Verify an abandoned candidate is not promoted into world lore and campaign A work does not change campaign B records.
- Review produced artifacts against behavioral criteria; retain a reproducible scenario and results rather than demanding identical model prose.

**Dependencies:** Steps 3, 4, 5.

## 7. Deliver transcript and play-notes processing through reviewed session records

**Issue:** [#8](https://github.com/willbradshaw/armarium/issues/8)

**Deliverable:** A working workflow from written play notes or a raw/prepared transcript to attributed transcript material as applicable, reviewed Events, session records, and consistent entity updates.

Extract recent Isles cast/name glossary maintenance, uncertainty handling, beat extraction, source verification, actual Events-text review, and explicit go-ahead after corrections. Derive downstream records from the final session account. Support entering at the appropriate stage and do not require audio or API credentials for an already-written transcript.

**Acceptance tests:**

- On both agents, exercise an uncertain speaker, a misspelled name, an unplayed prepared scene, and an unrevealed candidate clue.
- Demonstrate that clarification answers alone do not advance the required approval checkpoint; the committed Events match the approved draft.
- Correct an event after entity updates and verify the relevant records are re-derived without stale claims.
- Rerun the workflow without duplicate history entries; run validation and inspect the entity-sweep results.

**Dependencies:** Steps 6.

## 8. Ship optional recording transcription and cleanup

**Issue:** [#9](https://github.com/willbradshaw/armarium/issues/9)

**Deliverable:** A separately installable/configurable audio transcription path, cleanup utilities, and documented handoff into step 7.

Extract the general recording utilities without fixed cast, system, model, or machine paths. Declare the initial supported transcription backend and formats and keep optional dependencies outside ordinary vault setup. If a provider API is retained, use the decisions from issue #3 and explicit credential/model configuration. Preserve sources and expose transcription uncertainty; processing does not authorize deleting recordings.

**Acceptance tests:**

- Use a short original recording with a known reference transcript to verify supported input, usable output, names needing review, and handoff into the session workflow.
- Test missing backend/model, unsupported input, and interrupted processing with actionable diagnostics and preserved source files.
- Test repeated-ASR-loop cleanup on a controlled fixture without deleting legitimate repeated dialogue indiscriminately.
- Verify users without the audio dependencies can still install, prepare sessions, validate, and process existing text.

**Dependencies:** Steps 2, 7.

## 9. Ship safe updates for tools, templates, and agent materials

**Issue:** [#10](https://github.com/willbradshaw/armarium/issues/10)

**Deliverable:** An explicit update operation with a reviewable change preview, version tracking, conflict reporting, and a documented recovery path.

Implement the ownership/update contract established by setup. Preserve user-owned campaign records and overrides. Distinguish untouched managed files from changed files and protect edits to generated regions. This work can run alongside workflow extraction; safe writes apply throughout implementation rather than starting at this step.

**Acceptance tests:**

- Upgrade an older fixture containing two campaigns, a customized template, local instructions, and modified managed material.
- Verify a shared-tool fix is installed, user edits and campaign content remain intact, and conflicting updates require a deliberate resolution.
- Repeat the update and confirm no unnecessary rewrites or duplicated material.
- Simulate a failed/interrupted update and demonstrate the documented recovery behavior.

**Dependencies:** Steps 2, 3, 4.

## 10. Deliver a tested first-release candidate and user documentation

**Issue:** [#11](https://github.com/willbradshaw/armarium/issues/11)

**Deliverable:** Installable release-candidate artifacts, original example material, a quickstart/customization/upgrade guide, selected license, and an end-to-end validation report.

Exercise the complete experience using contrasting game styles, two campaigns sharing world information, and both required agent hosts. Document the actual tested platform/plugin/backend versions and limitations. Select licensing before distributing extracted materials; do not invent a license choice. Publishing a release and merging PRs remain separate user-controlled actions.

**Acceptance tests:**

- From a clean environment, follow the documentation to create a vault, add campaigns, prepare sessions, process notes and the sample recording, correct records, validate, and upgrade a customized vault.
- Demonstrate the general workflow without a game-system adapter or private source project.
- Verify docs and package artifacts match the tested installation paths and declared optional dependencies.
- Record results and known limits; do not claim an independent-user trial unless someone actually performs it.

**Dependencies:** Steps 1, 2, 3, 4, 5, 6, 7, 8, 9, plus #13–15.

## Scope and sequencing

After the starter vault, setup/agent integration and live-view work can proceed
alongside each other. Validation precedes the full workflow skills. Update support
can proceed once setup and managed-file contracts exist. Final release validation
exercises the integrated result.

Conventions 30–32 remain unreviewed: settle narrative/prose defaults before the
relevant skills, and decide separately whether to include worldbuilding interviews.
System-specific importers, migration of existing campaigns, cross-vault reference
synchronization, a marketplace, and a custom Obsidian plugin are proposed follow-on
work, not dependencies of this first usable general workflow.
