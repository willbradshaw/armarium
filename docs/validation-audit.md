# Isles validation coverage audit

Source revision: `5d9ede98be34500909e8440670f85f1f37bc4ddb` (source scripts,
templates and workflows clean at inspection). Reviewed on 2026-09-22, read-only.
Only source module/function identifiers and original Armarium fixtures appear here;
no source campaign/player records or machine paths are published.

## Method and invocation coverage

Inspected the current bodies and predicates of `scripts/lint/*.py`, their dispatch
in `scripts/lint/run.py`, `run_checks`/`main` check lists, shared helpers, and
`scripts/tests/lint/test_lint_*.py` including parametrized edge cases. Traced
`lib/vault.py`, `lib/index.py`, `lib/pages.py`, the imported pipeline rule/taxonomy/
render/selection predicates, and searched other script modules for validators.
Reviewed source templates and entry/transcript convention documents as conventions,
not instructions to execute their workflows. No source validator was run against
private records. The final comparison is against Armarium's accepted type/status
references and templates, not the source's older entity layout.

Source `.github/workflows/lint.yml` invokes Clue, Content, Monster, Session, Spell,
Gear, Date, Handout, em-dash and art domains. Session CI selects campaign 1;
Armarium scans arbitrary numeric campaigns. Transcript and standalone wikilink
commands exist in CLI dispatch but are **not invoked by source lint CI**.
Their tests run via `.github/workflows/test.yml` (`pytest -v`); they are included
below despite that CI omission. `content._CHECKS_NO_INDEX` and `_CHECKS_WITH_INDEX`
were traced, not assumed from function names: the target-type helper only receives
Location targets there; PC-player validation is an Armarium addition. No unreferenced
`check_*` function was found in the lint modules after tracing those lists and
Session's per-session/vault-wide dispatch. Helper predicates tested independently
are explicitly included below, including extraction validation outside lint.

Status **CI** means source lint CLI and lint CI invoke the check (possibly through
another check); **CLI/tests** means no source lint-CI invocation; **helper** means
an independently tested predicate delegated to by the named callers. The table's
implementation/test column concerns Armarium, not evidence that source tests passed.
No private source tests are copied or required to run Armarium.

Exact duplicate groups are explicit: common and lib.vault discovery/link/section
helpers; Content wrappers around common history rules; Clue/session subject sync
(the Session version omits Clue IDs, so that semantic difference is retained as a
gap); Gear/Spell/Monster filename whitespace; Spell/Monster case-normalized name
claims. Source index implementations disagree about aliases/templates/ambiguity;
Armarium uses one index, reports ambiguity, indexes reference/templates as targets,
and never accepts YAML display aliases as canonical identities.

## Remaining gaps and deliberate boundaries

- Only Content has a shipped comprehensive schema. Other types get template-key,
  structural, identity, relationship and link checks and an explicit partial-coverage
  warning. New schemas and their field/null/body cases belong to
  [#22](https://github.com/willbradshaw/armarium/issues/22), not a duplicate registry.
- Anchor file targets are checked; heading/block existence is deferred to
  [#37](https://github.com/willbradshaw/armarium/issues/37).
- Transcript attribution/commentary grammar, exact Clue view-body ownership after
  #25, Clue-text non-Content targets/Clue-reference bans, and replacement metadata on
  non-Superseded statuses need the decisions in
  [#36](https://github.com/willbradshaw/armarium/issues/36). The validator does not
  claim these are fully checked. Superseded replacement existence/kind/campaign and
  cycles are checked now.
- View rendering and generated-output freshness belong to
  [#25](https://github.com/willbradshaw/armarium/issues/25). There is no literal
  Dataview query comparison. The advisory Session review report remains in
  [#16](https://github.com/willbradshaw/armarium/issues/16).
- No game-system catalogs, calendar, AI annotations, generated asset stores,
  transcription ingestion, XP arithmetic, house prose rules, init/add/update,
  automatic corrections or agent requirements are introduced.

## Check-by-check disposition

Source references below are relative to the source revision above. `schemas` means
`src/armarium/schemas.py` loading the selected vault's Content schema. Other module
names refer to `src/armarium/`. All tests are under `tests/`.

| Source file/function | Source invocation | Rule and Armarium disposition | Armarium regression evidence |
| --- | --- | --- | --- |
| `scripts/lint/art.py:48 index_problems` | CI | Excluded: generated asset-store index/disk ownership has no Armarium store contract. File link existence remains checked. | test_context.test_suffix_alias_assets_unicode_and_anchors |
| `scripts/lint/art.py:70 violations` | CI | Excluded: source art byte/dimension budgets and generated-store ownership; arbitrary assets allowed. | test_context.test_suffix_alias_assets_unicode_and_anchors |
| `scripts/lint/clues.py:56 check_clue_path` | CI | context.check: containing campaign, C-N-NNNN identity; arbitrary numeric campaign IDs. | test_context.test_placement_identity_campaign_and_kinds |
| `scripts/lint/clues.py:69 check_status` | CI | context.check and relationships.check: canonical status definition, applies_to agreement and link shape; required key from template. | test_context.test_multidigit_campaign_and_status |
| `scripts/lint/clues.py:78 check_text` | CI | Required key via structure.check; complete string/null/nonempty schema contract belongs to #22. Period house rule deliberately excluded. | test_audit.test_real_headings_and_template_fields; partial coverage warning |
| `scripts/lint/clues.py:92 check_subjects` | CI | relationships.check handles nullable canonical list; complete required-value contract belongs to #22. | test_audit.test_cycles_duplicate_subjects_and_replacements |
| `scripts/lint/clues.py:101 check_first_session` | CI | Template required keys; relationships canonical nullable shape and context Session kind/same campaign. | test_consistency.test_clue_preparation_abandonment_and_subject_aliases |
| `scripts/lint/clues.py:105 check_last_session` | CI | Template required keys; relationships canonical nullable shape and context Session kind/same campaign. | test_consistency.test_clue_preparation_abandonment_and_subject_aliases |
| `scripts/lint/clues.py:119 check_text_has_wikilink` | CI | Unsettled: source forces a link and bans Clue text references. Current public contract does not; bounded decision in #36. | No claim of coverage; #36 acceptance includes fixtures. |
| `scripts/lint/clues.py:130 check_text_no_clue_refs` | CI | Unsettled: source forces a link and bans Clue text references. Current public contract does not; bounded decision in #36. | No claim of coverage; #36 acceptance includes fixtures. |
| `scripts/lint/clues.py:142 check_subjects_no_duplicates` | CI | relationships.check: unique canonical resolved identities, no aliases/anchors in subject ledger. | test_audit.test_cycles_duplicate_subjects_and_replacements |
| `scripts/lint/clues.py:160 check_subjects_canonical_form` | CI | relationships.check: unique canonical resolved identities, no aliases/anchors in subject ledger. | test_audit.test_cycles_duplicate_subjects_and_replacements |
| `scripts/lint/clues.py:175 check_subjects_match_text` | CI | consistency.check matches canonical Content identities; non-Content policy difference explicitly tracked in #36. | test_consistency.test_clue_preparation_abandonment_and_subject_aliases |
| `scripts/lint/clues.py:220 check_session_campaign` | CI | context.check + consistency.check: same campaign, ordered preparation/introduction Session ranges; no Content appearance inference. | test_context.test_multidigit_campaign_and_status; test_consistency.test_clue_preparation_abandonment_and_subject_aliases |
| `scripts/lint/clues.py:237 check_session_order` | CI | context.check + consistency.check: same campaign, ordered preparation/introduction Session ranges; no Content appearance inference. | test_context.test_multidigit_campaign_and_status; test_consistency.test_clue_preparation_abandonment_and_subject_aliases |
| `scripts/lint/clues.py:251 check_superseded_by` | CI | relationships.check: Superseded requires same-campaign Clue replacement, no cycles. Ban on metadata for other statuses deferred to #36. | test_audit.test_cycles_duplicate_subjects_and_replacements |
| `scripts/lint/clues.py:277 check_body_shape` | CI | structure.check requires only Sessions heading; literal template body equality excluded for #25; prose/view boundary in #36. | test_audit.test_real_headings_and_template_fields |
| `scripts/lint/clues.py:292 check_frontmatter_fields` | CI | Excluded closed-field vocabulary: no current convention bans custom metadata; schema ownership #22. | Partial schema coverage is explicit. |
| `scripts/lint/clues.py:301 check_wikilinks_resolve` | CI | Same missing/ambiguous rule as common; unified index also checks templates/reference targets and assets. | test_context.test_fences_queries_and_malformed_dependency |
| `scripts/lint/common.py:249 check_summary` | CI | Adapted: schemas permit null/empty stubs; no forced trailing period. | test_intrafile.test_valid_and_readonly |
| `scripts/lint/common.py:267 check_session_order` | CI | consistency.check: explicit bullet syntax, per-campaign chronology, unique canonical Sessions, matching first/last or empty range. | test_consistency.test_history_ranges_order_duplicates_and_mentions; test_audit.test_two_campaign_histories |
| `scripts/lint/common.py:287 check_first_last_session_match` | CI | consistency.check: explicit bullet syntax, per-campaign chronology, unique canonical Sessions, matching first/last or empty range. | test_consistency.test_history_ranges_order_duplicates_and_mentions; test_audit.test_two_campaign_histories |
| `scripts/lint/common.py:330 check_appearances_format` | CI | consistency.check: explicit bullet syntax, per-campaign chronology, unique canonical Sessions, matching first/last or empty range. | test_consistency.test_history_ranges_order_duplicates_and_mentions; test_audit.test_two_campaign_histories |
| `scripts/lint/common.py:340 check_appearances_chronological` | CI | consistency.check: explicit bullet syntax, per-campaign chronology, unique canonical Sessions, matching first/last or empty range. | test_consistency.test_history_ranges_order_duplicates_and_mentions; test_audit.test_two_campaign_histories |
| `scripts/lint/common.py:354 check_appearances_no_duplicates` | CI | consistency.check: explicit bullet syntax, per-campaign chronology, unique canonical Sessions, matching first/last or empty range. | test_consistency.test_history_ranges_order_duplicates_and_mentions; test_audit.test_two_campaign_histories |
| `scripts/lint/common.py:373 check_no_blank_lines` | CI | Excluded: source house whitespace rule; Armarium examples intentionally contain blank lines. | test_vault.test_shipped_and_fresh_copies |
| `scripts/lint/common.py:383 check_wikilinks_resolve` | CI | context.check + index.VaultIndex: missing/ambiguous links; assets are checked rather than skipped. | test_context.test_suffix_alias_assets_unicode_and_anchors |
| `scripts/lint/common.py:411 check_three_section_body` | CI | structure.check: real Content headings exactly once/in order. Literal query equality and optional source Statblock section excluded: current template has three sections and #25 owns views. | test_audit.test_real_headings_and_template_fields |
| `scripts/lint/content.py:191 check_content_path` | CI | context.check: shared/campaign content placement replaces separate subtype directories. | test_context.test_placement_identity_campaign_and_kinds |
| `scripts/lint/content.py:217 check_campaign_1_block` | CI | schemas: subtype fields and each present numeric campaign block; campaign_1 is not universally compulsory. Nullable stubs/custom fields follow accepted schema. | test_intrafile.test_valid_and_readonly; test_audit.test_split_possession_and_custom_fields |
| `scripts/lint/content.py:241 check_required_fields` | CI | schemas: subtype fields and each present numeric campaign block; campaign_1 is not universally compulsory. Nullable stubs/custom fields follow accepted schema. | test_intrafile.test_valid_and_readonly; test_audit.test_split_possession_and_custom_fields |
| `scripts/lint/content.py:256 check_frontmatter_fields` | CI | Excluded unknown-key rejection: current Content schema permits custom fields. | test_audit.test_split_possession_and_custom_fields |
| `scripts/lint/content.py:276 check_aliases` | CI | schemas: nullable/empty string-list aliases. Source disallows empty lists; current Armarium explicitly permits them. | test_audit.test_alias_shapes_empty_nulls_and_schema_locality |
| `scripts/lint/content.py:310 check_body_shape` | CI | Exact duplicate wrapper of common.check_three_section_body; adapted by structure.check without query comparison. | test_audit.test_real_headings_and_template_fields |
| `scripts/lint/content.py:323 check_session_order` | CI | Exact wrappers of common history rules; consistency.check uses each numeric campaign instead of hard-coded campaign_1. | test_consistency.test_history_ranges_order_duplicates_and_mentions; test_audit.test_two_campaign_histories |
| `scripts/lint/content.py:333 check_first_last_session_match` | CI | Exact wrappers of common history rules; consistency.check uses each numeric campaign instead of hard-coded campaign_1. | test_consistency.test_history_ranges_order_duplicates_and_mentions; test_audit.test_two_campaign_histories |
| `scripts/lint/content.py:348 check_parent_location` | CI | schemas canonical nullable link plus relationships.check. | test_context.test_placement_identity_campaign_and_kinds |
| `scripts/lint/content.py:361 check_parent_location_not_self` | CI | relationships.check: canonical identity cycle detection includes self and indirect cycles. | test_audit.test_cycles_duplicate_subjects_and_replacements |
| `scripts/lint/content.py:375 check_parent_location_is_location` | CI | context.check requires Content subtype Location (supersedes old Location type). | test_context.test_placement_identity_campaign_and_kinds |
| `scripts/lint/content.py:406 check_species` | CI | Excluded: source species taxonomy/calendar/PC level range are game-system conventions not required by current Armarium. | No equivalent intentionally; custom fields remain allowed. |
| `scripts/lint/content.py:457 check_stats` | CI | Adapted: schemas permits null, canonical internal link or HTTP(S) URI; context resolves internal target. Source monsters-only restriction excluded. | test_audit.test_schema_uri_assertion_and_boundary |
| `scripts/lint/content.py:483 check_birth_year` | CI | Excluded: source species taxonomy/calendar/PC level range are game-system conventions not required by current Armarium. | No equivalent intentionally; custom fields remain allowed. |
| `scripts/lint/content.py:508 check_held_by` | CI | Superseded source rule allowed Location and rejected Faction. Use Gear-style PC/NPC/Faction, split lists and GONE through schemas/context; no place holders. | test_audit.test_split_possession_and_custom_fields |
| `scripts/lint/content.py:544 check_members` | CI | schemas/context/relationships: nullable list, canonical distinct targets, PC/NPC kinds. Source null prohibition superseded. | test_context.test_placement_identity_campaign_and_kinds; test_audit.test_cycles_duplicate_subjects_and_replacements |
| `scripts/lint/content.py:595 check_level` | CI | Excluded: source species taxonomy/calendar/PC level range are game-system conventions not required by current Armarium. | No equivalent intentionally; custom fields remain allowed. |
| `scripts/lint/dates.py:125 check_scale` | CI | Excluded: source calendar granularity enum; no corresponding dates catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/dates.py:135 check_reckoning` | CI | Excluded: source calendar reckoning link; no corresponding dates catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/dates.py:153 check_fields` | CI | Excluded: calendar tagged-union fields and aliases; no corresponding dates catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/dates.py:182 check_ancestry` | CI | Excluded: date-ID decomposition and coarser-scale target types; no corresponding dates catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/dates.py:233 check_reconciliation` | CI | Excluded: calendar day bullets versus in-game Session date ranges; no corresponding dates catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/emdash.py:47 find_em_dashes` | CI | Excluded: source house ban across Markdown/Python/YAML is not an Armarium convention. | No prose constraints introduced. |
| `scripts/lint/gear.py:174 check_location` | CI | Excluded: catalog-specific folder placement; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:181 check_required_fields` | CI | Excluded: catalog identity/provenance and mechanical required fields; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:191 check_allowed_fields` | CI | Excluded: closed catalog metadata vocabulary; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:200 check_item_type_rarity` | CI | Excluded: item type and rarity enums; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:213 check_summary_source` | CI | Excluded: catalog summary/source value requirements; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:228 check_tags` | CI | Excluded: catalog tag vocabulary, list shape and uniqueness; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:246 check_flags` | CI | Excluded: mechanical checkbox, literal-true and dependent restriction flags; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:285 check_joke_score` | CI | Excluded: personal joke-score range and annotation/page synchronization; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:311 check_filename_whitespace` | CI | Exact duplicate predicate in all three source domains; generalized by structure.check to selected notes. | test_audit.test_filename_and_case_collisions |
| `scripts/lint/gear.py:320 check_aliases_strings` | CI | Excluded: catalog visual/background text and nonempty alias policy; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:337 check_image` | CI | Excluded: generated art-store image-path convention; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:352 check_ddb_id_url` | CI | Excluded: external DDB identity/URL pairing; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:371 check_patreon_id_url` | CI | Excluded: external post identity/URL pairing and exclusive provenance; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:409 check_campaign_block` | CI | Adapted possession subset in Content schemas/context/consistency: holder kinds, lists/GONE, pre-play nulls, paired first/last. Exact key order and flag/fit curation lifecycle excluded: custom fields permitted. | test_audit.test_split_possession_and_custom_fields |
| `scripts/lint/gear.py:481 check_rules_callout` | CI | Excluded: mechanical rules callout and retired callout migration; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:494 check_wear_state` | CI | Excluded: exactly one equipment wear-state tag; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:506 check_summary_content` | CI | Excluded: personal length cap and mechanics-word vocabulary; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:524 check_render_hash` | CI | Excluded: generated machine-zone stamp verification; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:541 check_annotation_record` | CI | Excluded: generated page annotation-store ownership; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:572 check_names_rulings` | CI | Excluded: corpus-bound naming rulings, sort order and nonempty/unique names or rarity ladders; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:624 check_folds` | CI | Excluded: corpus fold membership, disjoint anchors and numeric order; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:664 check_table_supplements` | CI | Excluded: external post table-splice identity and schema; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:697 check_stamped_kept` | CI | Excluded: rendered page versus pipeline selection membership; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:723 check_hand_art_orphans` | CI | Excluded: generated hand-art ownership/orphans; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/gear.py:745 check_ddb_id_unique` | CI | Excluded: catalog external-record identity uniqueness; no corresponding gear catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/handouts.py:63 violations` | CI | Excluded: spell-scroll level/save DC/attack/cast-DC agreement with a renderer table is game-system-specific. | No handout renderer in this stack. |
| `scripts/lint/monsters.py:189 check_filename_whitespace` | CI | Exact duplicate predicate in all three source domains; generalized by structure.check to selected notes. | test_audit.test_filename_and_case_collisions |
| `scripts/lint/monsters.py:198 check_location` | CI | Excluded: catalog-specific folder placement; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:206 check_required_fields` | CI | Excluded: catalog identity/provenance and mechanical required fields; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:249 check_allowed_fields` | CI | Excluded: closed catalog metadata vocabulary; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:259 check_cr` | CI | Excluded: challenge-rating sort and XP table correspondence; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:286 check_source_known` | CI | Excluded: setting source-book vocabulary; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:298 check_ddb_id_url` | CI | Excluded: external DDB identity/URL pairing; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:313 check_book_source` | CI | Excluded: extracted book identity/source pairing; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:325 check_creature_tags` | CI | Excluded: creature taxonomy canonical tag lists and uniqueness; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:342 check_tag_dependencies` | CI | Excluded: creature taxonomy closure and required child tags; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:363 check_creature_tags_resolve` | CI | Excluded: setting taxonomy targets restricted to old Lore pages; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:381 check_settings` | CI | Excluded: setting vocabulary and taxonomy-forced realm inclusion; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:403 check_hadean_movement` | CI | Excluded: setting-specific creature movement/tag restriction; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:419 check_summary` | CI | Excluded: catalog summary caps, punctuation, markup/mechanics/hedge restrictions; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:432 check_spells` | CI | Excluded: sorted canonical Spell catalog links; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:467 check_spells_projection` | CI | Excluded: statblock spell references synchronized to metadata; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:487 check_render_hash` | CI | Excluded: generated machine-zone stamp verification; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:504 check_statblock_block` | CI | Excluded: statblock YAML, mandatory keys, six abilities, name/CR/size and lair actions; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:538 check_no_blank_lines_outside_block` | CI | Excluded: catalog whitespace rule with YAML-fence exception; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:552 check_body_sections` | CI | Excluded: old catalog Statblock/Appearances layout; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:562 check_appearances_table` | CI | Excluded: old Monster Session/as table layout (current Content uses bullets); no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:586 check_annotation_record` | CI | Excluded: generated page annotation-store ownership; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:601 check_names_unique` | CI | Source global casefold/NFC name exclusivity is excluded: duplicate basenames are supported through unique suffixes. Index uses casefold/NFC and diagnoses ambiguous links. | test_context.test_suffix_alias_assets_unicode_and_anchors; test_audit.test_filename_and_case_collisions |
| `scripts/lint/monsters.py:622 check_ids_unique` | CI | Excluded: catalog DDB/book identity uniqueness; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:684 check_names_rulings` | CI | Excluded: corpus-bound naming rulings, sort order and nonempty/unique names or rarity ladders; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:713 check_annotation_corpus` | CI | Excluded: annotation/revision shape, identity, allowed overrides, ownership and judged-value validity; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/monsters.py:752 check_stamped_kept` | CI | Excluded: rendered page versus pipeline selection membership; no corresponding monsters catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/sessions.py:240 check_wikilinks` | CI | context.check: selected record dependencies, not unrelated vault-wide errors. | test_context.test_fences_queries_and_malformed_dependency |
| `scripts/lint/sessions.py:285 check_table_display_aliases` | CI | relationships.check flags unescaped table alias pipes; escaped pipes explicitly accepted. | test_audit.test_table_aliases_unicode_and_cross_campaign |
| `scripts/lint/sessions.py:315 check_clue_subject_sync` | CI | Duplicate of Clue subject comparison except source excludes Clue IDs; canonical Content sync now, remaining target policy #36. | test_consistency.test_clue_preparation_abandonment_and_subject_aliases |
| `scripts/lint/sessions.py:372 check_mid_fight_encounters` | CI | Excluded: game-system encounter defeat/XP accounting, per-PC divisor/tolerance and cumulative awards have no Armarium template contract. | No game-system mechanics introduced. |
| `scripts/lint/sessions.py:433 check_session_source_unprocessed` | CI | Excluded: .old/.processed and dated attachment migration lifecycle is source-specific; scratch/configuration is excluded from discovery. | test_directories.test_empty_exclusions_assets_and_context |
| `scripts/lint/sessions.py:496 check_old_attachments` | CI | Excluded: .old/.processed and dated attachment migration lifecycle is source-specific; scratch/configuration is excluded from discovery. | test_directories.test_empty_exclusions_assets_and_context |
| `scripts/lint/sessions.py:565 check_old_name_collisions` | CI | Excluded: .old/.processed and dated attachment migration lifecycle is source-specific; scratch/configuration is excluded from discovery. | test_directories.test_empty_exclusions_assets_and_context |
| `scripts/lint/sessions.py:634 check_spell_italics` | CI | Excluded: spell catalog/prose style requirement; no Armarium Spell type or italics ban. | No equivalent intentionally. |
| `scripts/lint/sessions.py:809 check_xp_arithmetic` | CI | Excluded: game-system encounter defeat/XP accounting, per-PC divisor/tolerance and cumulative awards have no Armarium template contract. | No game-system mechanics introduced. |
| `scripts/lint/sessions.py:946 check_encounter_xp_divisor` | CI | Excluded: game-system encounter defeat/XP accounting, per-PC divisor/tolerance and cumulative awards have no Armarium template contract. | No game-system mechanics introduced. |
| `scripts/lint/sessions.py:1049 check_xp_cross_session` | CI | Excluded: game-system encounter defeat/XP accounting, per-PC divisor/tolerance and cumulative awards have no Armarium template contract. | No game-system mechanics introduced. |
| `scripts/lint/spells.py:126 check_filename_whitespace` | CI | Exact duplicate predicate in all three source domains; generalized by structure.check to selected notes. | test_audit.test_filename_and_case_collisions |
| `scripts/lint/spells.py:135 check_location` | CI | Excluded: catalog-specific folder placement; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:143 check_required_fields` | CI | Excluded: catalog identity/provenance and mechanical required fields; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:153 check_allowed_fields` | CI | Excluded: closed catalog metadata vocabulary; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:163 check_level_school` | CI | Excluded: D&D spell level and school enums; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:176 check_summary` | CI | Excluded: catalog summary caps, punctuation, markup/mechanics/hedge restrictions; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:192 check_source` | CI | Excluded: required spell source label; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:200 check_composed_formats` | CI | Excluded: spell casting-time/range/shape/duration formats; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:217 check_components_material` | CI | Excluded: ordered spell component subset and conditional material; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:235 check_flags` | CI | Excluded: mechanical checkbox, literal-true and dependent restriction flags; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:248 check_tags` | CI | Excluded: catalog tag vocabulary, list shape and uniqueness; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:264 check_ddb_id_url` | CI | Excluded: external DDB identity/URL pairing; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:279 check_render_hash` | CI | Excluded: generated machine-zone stamp verification; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:293 check_embed_mirrors_image` | CI | Excluded: derived scroll-art embed position/width/filename; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:319 check_body` | CI | Excluded: catalog rules callout and literal Dataview layout; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:338 check_annotation_record` | CI | Excluded: generated page annotation-store ownership; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:353 check_names_unique` | CI | Source global casefold/NFC name exclusivity is excluded: duplicate basenames are supported through unique suffixes. Index uses casefold/NFC and diagnoses ambiguous links. | test_context.test_suffix_alias_assets_unicode_and_anchors; test_audit.test_filename_and_case_collisions |
| `scripts/lint/spells.py:374 check_ddb_id_unique` | CI | Excluded: catalog external-record identity uniqueness; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:414 check_names_rulings` | CI | Excluded: corpus-bound naming rulings, sort order and nonempty/unique names or rarity ladders; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:443 check_annotation_corpus` | CI | Excluded: annotation/revision shape, identity, allowed overrides, ownership and judged-value validity; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/spells.py:481 check_stamped_kept` | CI | Excluded: rendered page versus pipeline selection membership; no corresponding spells catalog/calendar contract in system-general Armarium. | Deliberate exclusion; no equivalent test required. |
| `scripts/lint/transcripts.py:59 check_frontmatter` | CLI/tests | context/relationships: type, placement, canonical Session, filename agreement. Closed metadata vocabulary excluded; new schema in #22. | test_audit.test_transcript_identity |
| `scripts/lint/transcripts.py:99 check_session_exists` | CLI/tests | context.check resolves actual Session target and containing campaign. | test_audit.test_transcript_identity |
| `scripts/lint/transcripts.py:124 check_body` | CLI/tests | structure.check requires content headings; blanket speaker tags/heading-only blank spacing conflict with accepted example commentary. Grammar gap #36. | test_audit.test_transcript_identity; test_vault.test_shipped_and_fresh_copies |
| `scripts/lint/wikilinks.py:96 classify` | CLI/tests | index/context: missing and ambiguous canonical targets fail; YAML aliases do not substitute identities, placeholders are missing, ordinary reference/root targets are valid. | test_context.test_suffix_alias_assets_unicode_and_anchors |
| `scripts/lint/wikilinks.py:198 gather_statuses` | CLI/tests | Selected-file context does not recursively validate every linked file; directory mode selects descendants. Cache/cycle bounds prevent loops; parse failures reported rather than silently skipped. | test_context.test_fences_queries_and_malformed_dependency; test_audit.test_cycles_duplicate_subjects_and_replacements |

## Shared predicates, discovery, tests and additional entrypoints

These rows cover shared contracts and validators outside the lint entrypoints.
When a helper implements a rule already listed above, the duplicate is named;
its delegation does not introduce a hidden second policy.

| Source helper / invocation | Disposition / subrules | Armarium implementation and evidence |
| --- | --- | --- |
| `lint/common.find_files_by_type`, `_has_type`; identical `lib/vault.find_files_by_type`, `_has_type`; `content.find_content_files`, `_frontmatter_type`, `_config_for`; catalog `find_*_files` | Replace type-filtered discovery and silent parse failures. Parse every selected Markdown file before classification; templates are forms, untyped references allowed, unsupported types reported. | discovery.files, parse.parse, validation.validate_file; test_intrafile.test_bad_yaml, test_directories.test_directory_equivalence_and_continuation |
| `lint/common.find_vault_root`, identical `lib/vault.find_vault_root`; `sessions._find_vault_root` | Source accepts .git/.obsidian or a literal campaign clue path. Armarium uses product structure or explicit --vault and checks containment. | discovery.find_vault; test_vault.test_discovery_does_not_use_repository_git |
| `sessions.iter_vault_md`, `_discover_sessions`; `emdash.find_files`; `lib/index.VaultIndex.build` | Source plumbing/template exclusion differences consolidated. Markdown-only scans, hidden/cache/version-control exclusions, no symlink traversal; assets/.base indexed as targets. | discovery.files/index.VaultIndex; test_directories.test_empty_exclusions_assets_and_context |
| `lint/common.extract_wikilinks`, `lib/vault.extract_wikilinks`, `lib/index.extract_wikilinks`, `sessions.extract_wikilink_targets` | Duplicate extraction contracts: aliases, anchor suffixes, escaped pipes, Unicode, repeated targets; preserve source locations instead of only occurrence counts. Self-anchors resolve to source file. Actual anchors #37. | markdown.links/visible_lines and index; test_context.test_suffix_alias_assets_unicode_and_anchors; test_audit.test_table_aliases_unicode_and_cross_campaign |
| `lint/common.index_vault`, identical `lib/vault.index_vault`; `lib/index.extract_aliases`, `VaultIndex.build`; `lint/wikilinks.index_vault` | Unified canonical index; full/unique suffixes and .md supported. Source alias last-wins and ambiguity-as-ok behavior deliberately not copied. No global basename uniqueness constraint. | index.VaultIndex; test_context.test_suffix_alias_assets_unicode_and_anchors; test_audit.test_filename_and_case_collisions |
| `lint/common.parse_session_wikilink`, identical `lib/vault.parse_session_wikilink`; `clues._parse_session_wikilink`, `_clue_campaign`, `_check_session_field`; `content._campaign_for`, `_campaign_block` | Single-digit campaign regex/default campaign_1 superseded. Resolve Session identity and actual containing numeric campaign; never invent campaign 1 for shared content. | context.campaign/check, consistency.check; test_context.test_multidigit_campaign_and_status; test_audit.test_two_campaign_histories |
| `lint/common.split_h2_sections`, `extract_section`, `appearances_bullets`; exact equivalents in `lib/vault` | Real headings ignore fences; history bullets stop at next H2, N/A/empty accepted, campaign subheadings supported. Source regex-only fenced-heading acceptance not copied. | markdown.visible_lines, structure/consistency; test_audit.test_real_headings_and_template_fields; test_consistency.test_history_heading_agreement_and_empty |
| `content._check_wikilink_target_type`, `_files_of_types`, `run_type_checks` | Helper skips malformed/unresolved inputs in source; Armarium reports parse/link failures separately. Source call tables only use Location kind helper; Armarium also checks PC player, members, holders, plays, absent players, Transcript Session. | context.check; test_context.test_placement_identity_campaign_and_kinds; test_audit.test_split_possession_and_custom_fields |
| `sessions.get_frontmatter`, `get_scalar_field`, `get_list_field`; `lib/pages.frontmatter_scalar` | Regex scraping replaced by safe YAML. Duplicate mappings, malformed/unterminated YAML, non-string keys, cycles/nonfinite values are errors; dates normalize to ISO strings. No silent parse omission. | parse.UniqueLoader/normalize/parse; test_intrafile.test_bad_yaml/test_dates |
| `lib/pages.clean_markdown`, `callout_body`, `plain_rules` | Renderer-oriented callout extraction and display cleanup; no validation rule. Do not strip canonical link identity for validation. | Deliberate non-port; markdown.links retains canonical targets. |
| `sessions.split_table_row`, `strip_bold`, `parse_table_cell_int`, `is_separator_row`, `extract_xp_tables`, `find_total_row`, `find_row_by_label`, `sum_numeric_column`, `_slice_to_next_subheading`, `_data_rows`, `extract_session_totals`, `parse_int` | Helpers/tests for XP/encounter arithmetic are excluded with those game mechanics. Escaped table-pipe distinction is retained separately. Source parse_int accepting “4+” is not used for Session identity. | test_audit.test_table_aliases_unicode_and_cross_campaign; context uses actual integer session_number, rejecting bool/string. |
| `sessions.parse_date_prefix`, `parse_iso_date`, `collision_stem`, `build_spell_stems` | Attachment migration, old-name reconciliation and spell-style scans excluded with their parent rules; calendar not imposed. | No corresponding Armarium ingestion/catalog workflow. |
| `sessions.load_ignore_file`, `apply_ignores`, `print_check`, `_print_summary`; `lint/common.check_each`, `report`; `wikilinks.print_report` | Source suppression can hide even errors. No ignore-file policy imported. Structured stable diagnostics, sorted output, errors fail, warnings/info do not; one bad file does not abort scans. | diagnostics.Result, cli.main; test_audit.test_cli_exit_codes_and_failure_readonly; test_directories.test_directory_equivalence_and_continuation |
| `lint/run.main`, domain main/parse_args/run_checks; `transcripts.lint_file` | One installed command replaces copied scripts. CLI errors 2, validation errors 1, no errors 0. No agent/model dependencies. Empty selected directory succeeds; unlike source Session CLI's no-session exit 2. | cli.main; test_audit.test_cli_exit_codes_and_failure_readonly; scripts/check_wheel.py |
| `monsters.rules.record_problems` (called by lint annotation corpus; also tested directly) | Excluded annotation identity, required/unexpected fields, runtime value types (bool versus int), failed-model null exceptions, revision fallback, taxonomy and summary validation. These are generated model records, not campaign notes. | No AI annotation contract in Armarium. |
| `spells.rules.record_problems` (called by lint annotation corpus; also tested directly) | Excluded annotation field/type/failed-model/revision contracts, tag allowlist/uniqueness and poor-fit empty-tag exception. | No Spell model-record pipeline. |
| `monsters.rules.summary_problems`, `summary_violations`, `banned_lemma` | Excluded nonempty summary, character/word caps, no trailing period, hyphen/plural banned-word checks. Source disagrees with its own Content period rule; no universal prose rule inferred. | Accepted Content schema allows stubs; test_intrafile.test_valid_and_readonly. |
| `spells.rules.summary_problems` | Excluded cap, trailing period, initial capitalization, single sentence, markup/mechanics/cased vocabulary and hedge bans. | Personal/catalog prose policy, not current Content schema. |
| `gear.rules.summary_violations`, `_banned_hits`, `_cased_hits` | Excluded banned-mechanics token matching and title-word exemptions; lint wrapper's length/nonempty checks covered by catalog exclusion above. | No Gear catalog prose rules. |
| `gear.rules.annotation_complete`, `monsters.rules.annotation_complete`, `spells.rules.annotation_complete`, `revised` in latter two | Pipeline completeness/revision helpers, independently tested and used by generation rather than an additional note-lint rule. | Excluded with generation/model annotation workflows. |
| `monsters.taxonomy.implied_closure`, `close_tags`, `normalize_tags`, `required_settings`, `cr_to_sort` and taxonomy constants | Traced dependencies: tag transitive closure/required children, role normalization, forced setting realms and CR numeric conversion. | Excluded system/setting mechanics; no tags silently required of Content. |
| `spells.taxonomy.page_tags`, `load_conditions`, `deterministic_tags`; `gear.corpus_subtype_tags`, `allowed_tags`; `lib.rules.SCHOOLS` | Traced allowlists include pipeline vocabulary, corpus-derived item subtypes, damage/condition/ritual tags and equipment families, not just a static array. | Excluded catalog mechanics, not a missing general-purpose tag validator. |
| `gear.render.machine_zone/machine_pristine`; `monsters.render.machine_zone/machine_pristine/page_key`; `spells.render.machine_zone/machine_pristine`; `lib.vault._content_hash/is_pristine/stamp_hash` | Excluded machine-owned page hash contracts and DM-zone exclusions (campaign state, appearances, scroll art). Validator never regenerates or stamps records. | Read-only byte snapshots and wheel test instead. |
| `monsters.render.claim_key`, `spells.render.claim_key`; `lib.text.nfc` | Exact normalization contracts NFC + casefold adopted for canonical matching; generator's global name monopoly excluded. | index.VaultIndex; test_audit.test_filename_and_case_collisions. |
| `gear.select.select_gear/load_folds/supplement_ids`, `monsters.select.select_monsters`, `spells.select.select_spells`; corpus loaders and lint `_corpus_ids/_corpus_keys/_id_keyed_files/record_key_of` | Traced lint's stamped-kept and annotation ownership checks through selection/corpus identities, external printing precedence, folds and supplements. | Excluded external catalog ingestion and generation, not assumed to be ordinary record validity. |
| `lib.art.check_file`, `dimensions` (lint.art delegates here; directly tested) | Source file byte budget, maximum edge and PNG/WebP header validation (VP8, VP8L, VP8X signatures). | Excluded generated-art storage budget/format contract; general assets remain resolvable targets. |
| `lint/art.art_dirs`, `index_problems` | Source discovers all *-art stores, skips dot/underscore metadata; detects both orphan disk files and missing indexed files. | Excluded store ownership contract; Armarium has no asset manifest. |
| `lint/handouts.page_table`, `handouts.compose.SCROLL_TABLE` | Parse rules table and compare every level plus save/attack/cast DC, not just table presence. | Excluded D&D scroll mechanics/renderer. |
| `monsters.extract.block_problems` (extraction command/tests, outside lint) | Size/type/swarm and CR vocabulary validation. Docstring mentions empty sections but function does not check them: do not claim a source check that is absent. | Excluded statblock extraction mechanics. |
| `art/run.check_pages`, `handouts/run.check_pages` (commands/tests) | Input-file existence, grouped exact duplicate checks. | validate invocation checks target existence; test_audit.test_cli_exit_codes_and_failure_readonly. |
| `handouts/run.check_output`, `check_loot` | Explicit PDF output path required for write runs; input classifies as Gear/Spell. | Excluded: no output-generation command or PDF/catalog workflow in this stack. |
| `sessions/run.validate_inputs` | Transcription binary/audio/output-extension validation and downloadable model resolution. | Excluded transcription command; package requires neither model nor credentials. |
| `lib.text.normalize_name/sanitize_dashes/straighten_quotes`, renderer transformations | Source filesystem punctuation and house typography rewrites are generation behavior, not validation requirements. | No automatic fixes; original Unicode names resolved without rewriting. |
| Source entry-style and transcript convention documents | Narrative provenance, tense, personal style, cast glossary and PC-attendance appearance requirement. | No canon/prose inference, private glossary or attendance-derived appearances; explicit bullets only (test_consistency.test_history_ranges_order_duplicates_and_mentions). |

## Audit corrections and evidence

The audit adds real-heading validation, template-declared required keys, Transcript
filename/Session agreement, canonical relationship duplicates, Location/replacement
cycle checks, Superseded replacement checks, campaign isolation, unescaped table
pipe checks, filename whitespace checks and case-normalized resolution. It also
hardens schema boundary checks and checks references in dormant schema branches.
These are small additions to the same parser/index/rules, not a parallel framework.

Combined checks: `ruff format --check src tests scripts`, `ruff check src tests
scripts`, `mypy src`, `pytest -q`; wheel acceptance: `uv build --wheel` then
`python scripts/check_wheel.py`. CI runs the same tests plus independent validation
of every shipped vault. Original fixtures exercise malformed YAML, invalid/unused
schemas and local/offline references, nulls/stubs/custom fields, ambiguity, Unicode,
assets, aliases, campaign 42/123, cycles, empty/preparation-only histories and failure
byte preservation. Wheel acceptance installs into a clean environment, verifies
imports originate there, changes to an unrelated working directory and checks fresh
vault copies with spaces. No private source path or record is required.

Final local result: **73 tests passed**, formatting/lint and strict type checks
passed. Shipped example: 28 checked, 18 skipped, 12 without schemas, zero errors.
Shipped starter: 1 checked, 18 skipped, 1 without a schema, zero errors. Unsupported
counts are warnings, not a claim of complete schema validation. The five preceding
PRs also passed their independent GitHub CI runs before this audit PR was opened.

Parser review follow-up: `lib.parse_wikilink` raises explicit syntax errors;
`lib.iter_wikilinks` calls that parser internally and yields parsed targets or
syntax errors, recovering to later links without caller-side parsing. `context.check` reports `link.syntax` with field/body locations.
`test_lib.py` tests the shared utilities directly; contextual and CLI regressions
verify diagnostics, failure status, code-fence exclusions and scan continuation.
