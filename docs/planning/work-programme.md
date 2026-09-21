# Initial work programme

Each numbered item is the work specified by its linked issue, not an additional
stage before or after it. The [implementation plan](implementation-plan.md) gives
the deliverable, acceptance tests, and dependencies. Issues are open statements of
work, not claims that implementation or testing is complete.

| Order | Issue / deliverable | Depends on |
| --- | --- | --- |
| 1 | [#1: Build the canonical starter vault](https://github.com/willbradshaw/armarium/issues/1) | None |
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
