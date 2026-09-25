# Isles validation coverage audit

Source: the private Isles repository at revision `5d9ede98be34500909e8440670f85f1f37bc4ddb`,
inspected read-only on 2026-09-25. Only source module and function identifiers
appear here; no source records or machine paths. Armarium references are to
`src/armarium/` on `main` at the merge of #69, with evidence given as test
classes under `tests/`.

## Method

Every top-level function in `scripts/lint/*.py` was listed (151 definitions, of
which 141 are checks; the rest are `main`, `parse_args`, `run_checks` and
`check_each` plumbing) and traced through its domain's dispatch:
`content._CHECKS_NO_INDEX`/`_CHECKS_WITH_INDEX`, `clues.main`, the per-session and
vault-wide lists in `sessions.main`, `transcripts.lint_file`, `wikilinks.main` and
the catalog domains. Shared helpers in `scripts/lib/{vault,index,pages,rules,text}.py`
and the lint tests in `scripts/tests/lint/test_lint_*.py` were read for
delegated rules and edge cases. `.github/workflows/lint.yml` invokes the gear,
monsters, spells, art, handouts, clues, content, dates, emdash and sessions
domains (sessions against `campaign_1/sessions/` only). `transcripts` and
`wikilinks` are reachable from `scripts/lint/run.py` and tested, but no
workflow runs them; they are marked **CLI** below. Everything else is **CI**.

Dispositions:

- **Covered** — the rule holds in Armarium, possibly with a broader scope.
- **Adapted** — the intent holds but the contract differs; the difference is stated.
- **Gap** — in scope and not implemented; each gap is listed under *Gaps* with its PR or issue.
- **Excluded** — deliberately not ported; the reason is one of:
  *catalog* (Gear/Monster/Spell/Date catalogs, external IDs, generated art and
  render stamps, AI annotation stores), *mechanics* (D&D XP, spell and
  statblock rules), *house style* (prose, punctuation and whitespace rules of
  the source vault), or *pipeline* (ingestion, migration and generation
  workflows). Armarium has no corresponding record types, templates or commands.

## Checks

| Source | Run | Disposition | Armarium |
| --- | --- | --- | --- |
| `art.py:48 index_problems` | CI | Excluded: catalog (generated art-store index). | — |
| `art.py:70 violations` | CI | Excluded: catalog (art byte and dimension budget). | — |
| `clues.py:56 check_clue_path` | CI | Covered: Clues live under `campaigns/campaign_N/clues` as `C-N-NNNN`; any N. | `validate_placement`, `validate_filename`; TestValidatePlacement, TestValidateFilename |
| `clues.py:69 check_status` | CI | Covered: `status` must link a Status whose `applies_to` names the record's Type. | `LINK_TARGETS`, `_validate_wikilink_status`; TestValidateWikilinkStatus |
| `clues.py:78 check_text` | CI | Adapted: non-blank string by schema; the trailing-period rule is house style. | `clue.schema.json`; TestSchemaValidate |
| `clues.py:92 check_subjects` | CI | Covered: null or a list of canonical links to Content in the Clue's campaign or shared `content/`. | schema, `RECORD_LINK_TARGETS`; TestLinkTargets |
| `clues.py:101 check_first_session` | CI | Covered: null or a canonical link to a Session in the same campaign. | `RECORD_LINK_TARGETS`; TestLinkTargets, TestValidateClue |
| `clues.py:105 check_last_session` | CI | Covered, plus `last_session` requires and cannot precede `first_session`. | `validate_clue`; TestValidateClue |
| `clues.py:119 check_text_has_wikilink` | CI | Adapted: a Clue may have no linked subjects (`subjects: []`); #36 records the decision. | `validate_clue` |
| `clues.py:130 check_text_no_clue_refs` | CI | Covered: every link in `text` must be Content, so a Clue reference is `link.type`. | `RECORD_LINK_TARGETS`; TestLinkTargets |
| `clues.py:142 check_subjects_no_duplicates` | CI | **Gap**: repeated targets in `subjects` are not reported. | Gap 3 |
| `clues.py:160 check_subjects_canonical_form` | CI | Covered: schema forbids aliases and anchors in `subjects`. | `clue.schema.json`; TestSchemaValidate |
| `clues.py:175 check_subjects_match_text` | CI | Covered: `subjects` must equal the set of records linked in `text`. | `validate_clue`; TestValidateClue |
| `clues.py:220 check_session_campaign` | CI | Covered: Session links stay in the Clue's campaign. | `RECORD_LINK_TARGETS`; TestLinkTargets |
| `clues.py:237 check_session_order` | CI | Covered by ordinal comparison of the linked Sessions. | `validate_clue`; TestValidateClue |
| `clues.py:251 check_superseded_by` | CI | Adapted: Superseded requires `superseded_by` linking a Clue in the campaign (schema plus `_link_targets`). **Gap**: replacement cycles. Metadata on other statuses: #36. | `_link_targets`; TestLinkTargets; Gap 2 |
| `clues.py:277 check_body_shape` | CI | Adapted: body is exactly a `## Sessions` heading and one `.base` embed; the embed target is not compared literally (#25). | `clue.schema.json`; TestSchemaValidate |
| `clues.py:292 check_frontmatter_fields` | CI | Excluded: schemas allow custom fields (`additionalProperties: true`). | — |
| `clues.py:301 check_wikilinks_resolve` | CI | Covered: every link in frontmatter and body must resolve uniquely. | `validate_wikilinks`; TestValidateWikilinks |
| `common.py:249 check_summary` | CI | Adapted: `summary` is required, null or non-blank; the trailing period is house style. | `content.schema.json`; TestSchemaValidate |
| `common.py:267 check_session_order` | CI | Covered: Appearances are chronological within each campaign and campaigns are in order. | `validate_appearances`; TestValidateAppearances, TestCheckCampaignHistory |
| `common.py:287 check_first_last_session_match` | CI | Covered: each `campaign_N.first_session`/`last_session` names the earliest/latest appearance, or both are null with no appearances. | `_check_campaign_history`; TestCheckCampaignHistory |
| `common.py:330 check_appearances_format` | CI | Covered: one list of `[[S-N-NNN]]: text` items or a lone `N/A`; malformed sections reported once at the heading. | `_read_appearances`; TestReadAppearances |
| `common.py:340 check_appearances_chronological` | CI | Covered. | `_check_campaign_history`; TestCheckCampaignHistory |
| `common.py:354 check_appearances_no_duplicates` | CI | Covered. | `_check_campaign_history`; TestCheckCampaignHistory |
| `common.py:373 check_no_blank_lines` | CI | Excluded: house style. | — |
| `common.py:383 check_wikilinks_resolve` | CI | Covered, including assets and `.base` targets. | `validate_wikilinks`, `VaultIndex.resolve`; TestVaultIndexResolve |
| `common.py:411 check_three_section_body` | CI | Adapted: `## Notes`, `## Active Clues`, `## Appearances` in order with exactly one `.base` embed under Active Clues; no literal template comparison (#25). | `content.schema.json`; TestSchemaValidate |
| `content.py:191 check_content_path` | CI | Covered: `content/` or `campaigns/campaign_N/content/`; subtype directories are not used. | `validate_placement`; TestValidatePlacement |
| `content.py:217 check_campaign_1_block` | CI | Adapted: any `campaign_N` block is validated; none is compulsory. Blocks must name an existing campaign compatible with the record's location. | `validate_campaigns`; TestValidateCampaigns |
| `content.py:241 check_required_fields` | CI | Covered: required keys per subtype by schema. | `content.schema.json`; TestSchemaValidate |
| `content.py:256 check_frontmatter_fields` | CI | Excluded: custom fields allowed. | — |
| `content.py:276 check_aliases` | CI | Adapted: null or a list of non-empty strings; an empty list is allowed. | `content.schema.json`; TestSchemaValidate |
| `content.py:310 check_body_shape` | CI | As `common.check_three_section_body`. | — |
| `content.py:323 check_session_order` | CI | As `common.check_session_order`. | — |
| `content.py:333 check_first_last_session_match` | CI | As `common.check_first_last_session_match`. | — |
| `content.py:348 check_parent_location` | CI | Covered: null or a canonical link. | schema; TestSchemaValidate |
| `content.py:361 check_parent_location_not_self` | CI | **Gap**: self-reference and cycles are not reported. | Gap 2 |
| `content.py:375 check_parent_location_is_location` | CI | Covered: must link Content with subtype Location in the same campaign or shared content. | `RECORD_LINK_TARGETS`; TestLinkTargets |
| `content.py:406 check_species` | CI | Excluded: catalog (species taxonomy). | — |
| `content.py:457 check_stats` | CI | Adapted: NPC `stats` is null, a canonical link or an HTTP(S) URL; the link must resolve. | `content.schema.json`; TestSchemaValidate |
| `content.py:483 check_birth_year` | CI | Excluded: catalog (calendar). | — |
| `content.py:508 check_held_by` | CI | Adapted: Object `campaign_N.held_by` is null before play, then a holder, list of holders or `GONE`; holders are PC, NPC or Faction Content in that campaign. | schema, `_link_targets`; TestLinkTargets |
| `content.py:544 check_members` | CI | Covered: null or a list of PC/NPC Content in the Faction's campaign. **Gap**: duplicates. | `RECORD_LINK_TARGETS`; TestLinkTargets; Gap 3 |
| `content.py:595 check_level` | CI | Excluded: mechanics. | — |
| `dates.py:125 check_scale` | CI | Excluded: catalog (calendar). | — |
| `dates.py:135 check_reckoning` | CI | Excluded: catalog (calendar). | — |
| `dates.py:153 check_fields` | CI | Excluded: catalog (calendar). | — |
| `dates.py:182 check_ancestry` | CI | Excluded: catalog (calendar). | — |
| `dates.py:233 check_reconciliation` | CI | Excluded: catalog (calendar). | — |
| `emdash.py:47 find_em_dashes` | CI | Excluded: house style. | — |
| `gear.py:174 check_location` | CI | Excluded: catalog. | — |
| `gear.py:181 check_required_fields` | CI | Excluded: catalog. | — |
| `gear.py:191 check_allowed_fields` | CI | Excluded: catalog. | — |
| `gear.py:200 check_item_type_rarity` | CI | Excluded: catalog. | — |
| `gear.py:213 check_summary_source` | CI | Excluded: catalog. | — |
| `gear.py:228 check_tags` | CI | Excluded: catalog. | — |
| `gear.py:246 check_flags` | CI | Excluded: mechanics. | — |
| `gear.py:285 check_joke_score` | CI | Excluded: catalog. | — |
| `gear.py:311 check_filename_whitespace` | CI | **Gap**: filenames with leading, trailing or doubled spaces are not reported for any record. | Gap 4 |
| `gear.py:320 check_aliases_strings` | CI | Excluded: catalog. | — |
| `gear.py:337 check_image` | CI | Excluded: catalog (generated art). | — |
| `gear.py:352 check_ddb_id_url` | CI | Excluded: catalog (external IDs). | — |
| `gear.py:371 check_patreon_id_url` | CI | Excluded: catalog (external IDs). | — |
| `gear.py:409 check_campaign_block` | CI | Adapted: the possession subset is the Object `held_by` contract above; flag and fit curation is catalog. | schema, `_link_targets` |
| `gear.py:481 check_rules_callout` | CI | Excluded: mechanics. | — |
| `gear.py:494 check_wear_state` | CI | Excluded: mechanics. | — |
| `gear.py:506 check_summary_content` | CI | Excluded: house style. | — |
| `gear.py:524 check_render_hash` | CI | Excluded: pipeline (render stamps). | — |
| `gear.py:541 check_annotation_record` | CI | Excluded: pipeline (annotation store). | — |
| `gear.py:572 check_names_rulings` | CI | Excluded: catalog. | — |
| `gear.py:624 check_folds` | CI | Excluded: catalog. | — |
| `gear.py:664 check_table_supplements` | CI | Excluded: catalog. | — |
| `gear.py:697 check_stamped_kept` | CI | Excluded: pipeline. | — |
| `gear.py:723 check_hand_art_orphans` | CI | Excluded: pipeline (generated art). | — |
| `gear.py:745 check_ddb_id_unique` | CI | Excluded: catalog (external IDs). | — |
| `handouts.py:63 violations` | CI | Excluded: mechanics (scroll table). | — |
| `monsters.py:189 check_filename_whitespace` | CI | As `gear.check_filename_whitespace`. | Gap 4 |
| `monsters.py:198 check_location` | CI | Excluded: catalog. | — |
| `monsters.py:206 check_required_fields` | CI | Excluded: catalog. | — |
| `monsters.py:249 check_allowed_fields` | CI | Excluded: catalog. | — |
| `monsters.py:259 check_cr` | CI | Excluded: mechanics. | — |
| `monsters.py:286 check_source_known` | CI | Excluded: catalog. | — |
| `monsters.py:298 check_ddb_id_url` | CI | Excluded: catalog (external IDs). | — |
| `monsters.py:313 check_book_source` | CI | Excluded: catalog. | — |
| `monsters.py:325 check_creature_tags` | CI | Excluded: catalog (taxonomy). | — |
| `monsters.py:342 check_tag_dependencies` | CI | Excluded: catalog (taxonomy). | — |
| `monsters.py:363 check_creature_tags_resolve` | CI | Excluded: catalog (taxonomy). | — |
| `monsters.py:381 check_settings` | CI | Excluded: catalog. | — |
| `monsters.py:403 check_hadean_movement` | CI | Excluded: mechanics. | — |
| `monsters.py:419 check_summary` | CI | Excluded: house style. | — |
| `monsters.py:432 check_spells` | CI | Excluded: catalog. | — |
| `monsters.py:467 check_spells_projection` | CI | Excluded: mechanics. | — |
| `monsters.py:487 check_render_hash` | CI | Excluded: pipeline. | — |
| `monsters.py:504 check_statblock_block` | CI | Excluded: mechanics. | — |
| `monsters.py:538 check_no_blank_lines_outside_block` | CI | Excluded: house style. | — |
| `monsters.py:552 check_body_sections` | CI | Excluded: catalog (old Monster layout). | — |
| `monsters.py:562 check_appearances_table` | CI | Excluded: catalog (old table layout; Content uses lists). | — |
| `monsters.py:586 check_annotation_record` | CI | Excluded: pipeline. | — |
| `monsters.py:601 check_names_unique` | CI | Adapted: duplicate basenames are allowed and links to them are `link.ambiguous`; matching is NFC-normalised and case-sensitive. **Gap**: case-only differences. | `VaultIndex`; TestVaultIndexResolve; Gap 5 |
| `monsters.py:622 check_ids_unique` | CI | Excluded: catalog (external IDs). | — |
| `monsters.py:684 check_names_rulings` | CI | Excluded: catalog. | — |
| `monsters.py:713 check_annotation_corpus` | CI | Excluded: pipeline. | — |
| `monsters.py:752 check_stamped_kept` | CI | Excluded: pipeline. | — |
| `sessions.py:240 check_wikilinks` | CI | Covered: every link in a Session must resolve; `prepared_*`, `players_absent` and `campaign` are type-bound. | `validate_wikilinks`, `RECORD_LINK_TARGETS`; TestLinkTargets |
| `sessions.py:285 check_table_display_aliases` | CI | **Gap**: an unescaped `|` inside a wikilink in a table row breaks the table in Obsidian and is not reported. | Gap 1 |
| `sessions.py:315 check_clue_subject_sync` | CI | Covered on the Clue side by `validate_clue`; the source's Clue-ID exclusion is superseded by the Content-only rule for `text`. | TestValidateClue |
| `sessions.py:372 check_mid_fight_encounters` | CI | Excluded: mechanics (XP). | — |
| `sessions.py:433 check_session_source_unprocessed` | CI | Excluded: pipeline (transcription attachments). | — |
| `sessions.py:496 check_old_attachments` | CI | Excluded: pipeline. | — |
| `sessions.py:565 check_old_name_collisions` | CI | Excluded: pipeline. | — |
| `sessions.py:634 check_spell_italics` | CI | Excluded: house style. | — |
| `sessions.py:809 check_xp_arithmetic` | CI | Excluded: mechanics. | — |
| `sessions.py:946 check_encounter_xp_divisor` | CI | Excluded: mechanics. | — |
| `sessions.py:1049 check_xp_cross_session` | CI | Excluded: mechanics. | — |
| `spells.py:126 check_filename_whitespace` | CI | As `gear.check_filename_whitespace`. | Gap 4 |
| `spells.py:135 check_location` | CI | Excluded: catalog. | — |
| `spells.py:143 check_required_fields` | CI | Excluded: catalog. | — |
| `spells.py:153 check_allowed_fields` | CI | Excluded: catalog. | — |
| `spells.py:163 check_level_school` | CI | Excluded: mechanics. | — |
| `spells.py:176 check_summary` | CI | Excluded: house style. | — |
| `spells.py:192 check_source` | CI | Excluded: catalog. | — |
| `spells.py:200 check_composed_formats` | CI | Excluded: mechanics. | — |
| `spells.py:217 check_components_material` | CI | Excluded: mechanics. | — |
| `spells.py:235 check_flags` | CI | Excluded: mechanics. | — |
| `spells.py:248 check_tags` | CI | Excluded: catalog. | — |
| `spells.py:264 check_ddb_id_url` | CI | Excluded: catalog (external IDs). | — |
| `spells.py:279 check_render_hash` | CI | Excluded: pipeline. | — |
| `spells.py:293 check_embed_mirrors_image` | CI | Excluded: pipeline (generated art). | — |
| `spells.py:319 check_body` | CI | Excluded: catalog. | — |
| `spells.py:338 check_annotation_record` | CI | Excluded: pipeline. | — |
| `spells.py:353 check_names_unique` | CI | As `monsters.check_names_unique`. | Gap 5 |
| `spells.py:374 check_ddb_id_unique` | CI | Excluded: catalog (external IDs). | — |
| `spells.py:414 check_names_rulings` | CI | Excluded: catalog. | — |
| `spells.py:443 check_annotation_corpus` | CI | Excluded: pipeline. | — |
| `spells.py:481 check_stamped_kept` | CI | Excluded: pipeline. | — |
| `transcripts.py:59 check_frontmatter` | CLI | Covered: declared type, placement under `sessions/transcripts`, canonical `session` link, filename `S-N-NNN Transcript`. | `validate_placement`, `validate_filename`, `validate_identity_links`; TestValidateIdentityLinks |
| `transcripts.py:99 check_session_exists` | CLI | Covered: `session` must link a Session in the same campaign and the filename must match it. | `RECORD_LINK_TARGETS`, `validate_identity_links`; TestValidateIdentityLinks |
| `transcripts.py:124 check_body` | CLI | Adapted: at least one level-two heading followed by an attributed `[Speaker] line`; per-utterance attribution grammar is #36. | `transcript.schema.json`; TestSchemaValidate |
| `wikilinks.py:96 classify` | CLI | Covered: missing and ambiguous targets are errors; YAML aliases are not link targets; templates and reference pages are ordinary targets. | `VaultIndex.resolve`; TestVaultIndexResolve |
| `wikilinks.py:198 gather_statuses` | CLI | Adapted: only selected files are validated; linked notes are parsed once each and parse failures are `link.malformed`. | `linked_note`, `VaultIndex.parse`; TestLinkedNote, TestVaultIndexParse |

## Shared helpers and entrypoints

| Source | Disposition | Armarium |
| --- | --- | --- |
| `common.find_files_by_type`, `lib/vault.find_files_by_type`, `content.find_content_files`, catalog `find_*_files` | Adapted: every Markdown file in the selection is parsed and classified by its `type` link; a missing or non-canonical type is `record.type`, an unknown type `schema.unsupported`, templates are skipped with an info diagnostic. | `validate_markdown`, `find_files`; TestValidateMarkdown |
| `common.find_vault_root`, `lib/vault.find_vault_root`, `sessions._find_vault_root` | Adapted: the vault is the nearest ancestor with the product layout, or `--vault`; `.git`/`.obsidian` are not markers. | `find_vault`, `check_vault`; TestFindVault |
| `sessions.iter_vault_md`, `emdash.find_files`, `lib/index.VaultIndex.build` | Adapted: one discovery routine; hidden entries, caches and symlinks excluded. | `find_files`; TestFindFiles |
| `common.extract_wikilinks`, `lib/vault.extract_wikilinks`, `lib/index.extract_wikilinks`, `sessions.extract_wikilink_targets` | Covered: one parser for aliases, anchors, escaped pipes and embeds; malformed links are `link.syntax` at their line; anchors are checked (#37). | `lib.split_wikilink`, `iter_wikilinks`, `Note.links`; TestSplitWikilink, TestIterWikilinks, TestNoteLinks |
| `common.index_vault`, `lib/vault.index_vault`, `lib/index.VaultIndex`, `wikilinks.index_vault` | Adapted: one index keyed by every trailing path with and without `.md`; ambiguity is an error rather than last-wins. | `VaultIndex`; TestVaultIndex |
| `common.parse_session_wikilink`, `clues._parse_session_wikilink`, `content._campaign_for` | Adapted: campaigns are `campaign_N` for any N; a record's campaign is its containing directory, never a default. | `find_campaign`, `CAMPAIGN_NAME`; TestFindCampaign |
| `common.split_h2_sections`, `extract_section`, `appearances_bullets` | Adapted: the body is parsed with markdown-it into sections and blocks; headings inside code fences are not headings. Schema body regexes remain textual. | `parse.Body`, `Section`, `Block`; TestBody, TestSectionNest |
| `content._check_wikilink_target_type` | Covered for every type-bound field, not only Location. | `linked_note`, `Target`; TestLinkedNote, TestTarget |
| `sessions.get_frontmatter`, `get_scalar_field`, `lib/pages.frontmatter_scalar` | Adapted: frontmatter is parsed by a strict YAML loader; duplicate keys and malformed YAML are `parse.invalid`. | `Note.parse`, `Frontmatter`; TestFrontmatter, TestNoteParse |
| `sessions.load_ignore_file`, `apply_ignores`, `common.report`, `wikilinks.print_report` | Adapted: no suppression file; sorted stable diagnostics, errors fail the run, one bad file does not stop the scan. | `Result`, `cli.main`; TestResult, TestMain |
| `lint/run.main` and domain `main`s | Adapted: one command, `armarium validate <path>`; exit 2 for usage, 1 for errors, 0 otherwise. | `cli`; TestMain, TestParseArgs |
| `lib.text.nfc`, `render.claim_key` | Adapted: NFC normalisation for link resolution; no casefold (see Gap 5). | `VaultIndex` |
| `lib.rules`, `lib.art`, `lib.render`, `lib.annotate`, `lib.ingest`, `lib.transcribe`, `lib.store` | Excluded: catalog, pipeline. | — |

Armarium also checks things the source did not: vault infrastructure
(`validate_vault`: required directories, Type/Status/template definitions,
`campaign_N` layout, schema/Type correspondence), per-vault JSON schemas for
every type, `record.placement` for every built-in type, Session
`session_number`/filename agreement, and heading and block anchors.

## Gaps

1. **Table display aliases** (`sessions.check_table_display_aliases`): report an
   unescaped `|` inside a wikilink on a table row. Body table blocks are
   already parsed, so the check reads `Block.kind == "table"` text.
2. **Reference cycles** (`content.check_parent_location_not_self`,
   `clues.check_superseded_by`): report a `parent_location` or `superseded_by`
   chain that returns to the record, including self-links.
3. **Duplicate targets** (`clues.check_subjects_no_duplicates`,
   `content.check_members`): report a link list (`subjects`, `members`,
   `held_by`, `players_absent`, `prepared_*`) naming the same file twice.
4. **Filename whitespace** (`*.check_filename_whitespace`): report leading,
   trailing or doubled spaces in any record filename.
5. **Case-only collisions** (`*.check_names_unique`): Obsidian resolves links
   case-insensitively; Armarium resolves case-sensitively, so `[[quay nine]]`
   is `link.missing` here and works in Obsidian, while two files differing only
   in case are silently both accepted. Decision needed: casefold the index (then
   such pairs become `link.ambiguous`) or keep strict matching.

Gaps 1–4 are small additions to `validate.py` and are being raised as separate
pull requests. Gap 5 needs a decision first. Unsettled conventions stay in
#36 (Clue text with no links, replacement metadata on non-Superseded Clues,
Transcript attribution grammar) and #25 (view execution and embed targets).
