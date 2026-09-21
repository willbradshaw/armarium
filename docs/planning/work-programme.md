# Initial work programme

Each numbered item is the work specified by its linked issue, not an additional
stage before or after it. The [implementation plan](implementation-plan.md) gives
the deliverable, acceptance tests, and dependencies. Issues are open statements of
work, not claims that implementation or testing is complete.

| Order | Issue / deliverable | Depends on |
| --- | --- | --- |
| 1 | [#1: Extract the minimal Isles-derived starter](https://github.com/willbradshaw/armarium/issues/1) | None |
| 2 | [#2: Ship installable shared tooling and vault setup commands](https://github.com/willbradshaw/armarium/issues/2) | #1 |
| 3 | [#3: Deliver and test portable agent integration](https://github.com/willbradshaw/armarium/issues/3) | #2 |
| 4 | [#5: Deliver evaluated live views for clues and session preparation](https://github.com/willbradshaw/armarium/issues/5) | #1 |
| 5 | [#6: Ship vault validation and the post-session entity sweep](https://github.com/willbradshaw/armarium/issues/6) | #1, #2, #5 |
| 6 | [#7: Deliver entity-maintenance and session-preparation skills](https://github.com/willbradshaw/armarium/issues/7) | #3, #5, #6 |
| 7 | [#8: Deliver transcript and play-notes processing through reviewed session records](https://github.com/willbradshaw/armarium/issues/8) | #7 |
| 8 | [#9: Ship optional recording transcription and cleanup](https://github.com/willbradshaw/armarium/issues/9) | #2, #8 |
| 9 | [#10: Ship safe updates for tools, templates, and agent materials](https://github.com/willbradshaw/armarium/issues/10) | #2, #3, #5 |
| 10 | [#11: Deliver a tested first-release candidate and user documentation](https://github.com/willbradshaw/armarium/issues/11) | #1, #2, #3, #5, #6, #7, #8, #9, #10 |

Every completion PR must include an inspectable artifact and actual acceptance
evidence. Deterministic checks should be automated; Obsidian rendering and agent
behavior also require reproducible in-application checks. Preserve test fixtures
and distinguish verified results from limitations or unavailable checks.

Accepted scope follows the [product brief](product-brief.md) and
[conventions review](conventions-review.md). Conventions 30–32 remain open.
All repository changes go through working branches and user-merged PRs.

## Starter follow-ons

The first implementation PR is deliberately a small Isles-derived baseline.
The additional template features are separate reviewable deliverables:

- [#13: Multi-campaign state and examples](https://github.com/willbradshaw/armarium/issues/13).
- [#14: Minimal, demonstrated navigation](https://github.com/willbradshaw/armarium/issues/14).
- [#15: Player/Transcript templates and source storage](https://github.com/willbradshaw/armarium/issues/15).

All start from #1 and can proceed alongside #5. Final add-campaign behavior in #2
and two-campaign view integration in #5 use #13's tested conventions; #8 uses #15's
records. Release validation in #11 includes all three. Integration dependencies do
not prevent independent prototyping. Each PR records its source-derived behavior,
new choices, automated checks and actual Obsidian acceptance evidence.
