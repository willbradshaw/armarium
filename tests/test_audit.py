"""Regression cases for concrete omissions found by tracing the source validators."""

import json
import subprocess
import sys
import unicodedata
from pathlib import Path

from test_consistency import sessions
from test_intrafile import VALID, write

from armarium.index import VaultIndex
from armarium.validation import validate


def rules(path: Path) -> set[str]:
    return {d.rule for d in validate(path).diagnostics if d.severity == "error"}


def test_real_headings_and_template_fields(vault: Path) -> None:
    path = write(vault, VALID.replace("## Notes", "```markdown\n## Notes") + "\n```")
    assert "body.headings" in rules(path)
    path.write_text(VALID.replace("## Notes", "## Notes\n## Notes"))
    assert "body.headings" in rules(path)
    clue = vault / "campaigns/campaign_1/clues/C-1-0001.md"
    clue.write_text('---\ntype: "[[types/Clue]]"\n---\n## Notes\n')
    assert {"record.required", "body.headings"} <= rules(clue)


def test_transcript_identity(vault: Path) -> None:
    sessions(vault)
    path = vault / "campaigns/campaign_1/sessions/transcripts/Wrong.md"
    path.write_text(
        '---\ntype: "[[types/Transcript]]"\nsession: "[[S-1-001]]"\n'
        "---\n## Opening\n[GM] Begin.\n"
    )
    assert "record.identity" in rules(path)
    correct = path.with_name("S-1-001 Transcript.md")
    path.rename(correct)
    assert not rules(correct)


def test_cycles_duplicate_subjects_and_replacements(vault: Path) -> None:
    a = write(
        vault,
        VALID.replace(
            "subtype: Lore", 'subtype: Location\nparent_location: "[[Other]]"'
        ),
    )
    b = vault / "content/Other.md"
    b.write_text(
        VALID.replace("subtype: Lore", 'subtype: Location\nparent_location: "[[Test]]"')
    )
    assert "relationship.cycle" in rules(a)
    clue = vault / "campaigns/campaign_1/clues/C-1-0001.md"
    clue.write_text(
        '---\ntype: "[[types/Clue]]"\nstatus: "[[Superseded]]"\n'
        'text: "[[Test]] might matter."\n'
        'subjects: ["[[Test]]", "[[content/Test]]"]\n'
        "first_session:\nlast_session:\n---\n## Sessions\n"
    )
    assert {"relationship.duplicate", "clue.replacement"} <= rules(clue)
    clue.write_text(
        clue.read_text().replace("text:", 'superseded_by: "[[C-1-0001]]"\ntext:')
    )
    assert "relationship.cycle" in rules(clue)
    clue.write_text(clue.read_text().replace("[[C-1-0001]]", "[[Test]]"))
    assert "clue.replacement" in rules(clue)


def test_table_aliases_unicode_and_cross_campaign(vault: Path) -> None:
    path = write(vault, VALID.replace("## Notes", "## Notes\n| [[Test|name]] |"))
    assert "link.table-pipe" in rules(path)
    path.write_text(path.read_text().replace("Test|name", "Test\\|name"))
    assert not rules(path)
    unicode_path = vault / "content" / (unicodedata.normalize("NFD", "Café") + ".md")
    unicode_path.write_text("page")
    assert VaultIndex(vault).resolve("CAFÉ", path)[0] == unicode_path
    other = vault / "campaigns/campaign_42/content"
    other.mkdir(parents=True)
    (other / "Foreign.md").write_text(VALID)
    clue = vault / "campaigns/campaign_1/clues/C-1-0001.md"
    clue.write_text('---\ntype: "[[types/Clue]]"\n---\n## Sessions\n[[Foreign]]')
    assert "campaign.isolation" in rules(clue)


def test_schema_uri_assertion_and_boundary(vault: Path, tmp_path: Path) -> None:
    path = write(
        vault, VALID.replace("subtype: Lore", 'subtype: NPC\nstats: "https://bad host"')
    )
    assert "schema.instance" in rules(path)
    schema = vault / "reference/schemas/content.schema.json"
    outside = tmp_path / "outside.json"
    outside.write_text("{}")
    schema.write_text(json.dumps({"$ref": outside.as_uri()}))
    assert "schema.invalid" in rules(path)
    schema.unlink()
    schema.symlink_to(outside)
    assert "schema.invalid" in rules(path)


def test_cli_exit_codes_and_failure_readonly(vault: Path) -> None:
    path = write(vault, VALID)
    command = [
        sys.executable,
        "-c",
        "from armarium.cli import main; raise SystemExit(main())",
        "validate",
        str(path),
    ]
    assert subprocess.run(command, capture_output=True).returncode == 0
    path.write_text("---\nx: [\n---\n")
    before = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
    failed = subprocess.run(command, capture_output=True, text=True)
    assert failed.returncode == 1 and "parse.invalid" in failed.stdout
    assert before == {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
    assert subprocess.run(command + ["--unknown"], capture_output=True).returncode == 2


def test_unused_schema_references_are_checked(vault: Path) -> None:
    schema = vault / "reference/schemas/unused.schema.json"
    schema.write_text('{"$defs":{"unused":{"$ref":"missing.json"}}}')
    assert any(
        d.rule == "schema.invalid" and d.path.endswith("unused.schema.json")
        for d in validate(vault).diagnostics
    )
    schema.write_text('{"$defs":{"unused":{"$ref":"https://example.invalid/schema"}}}')
    assert "schema.invalid" in rules(vault)


def test_split_possession_and_custom_fields(vault: Path) -> None:
    sessions(vault)
    holder = vault / "content/Holder.md"
    holder.write_text(VALID.replace("subtype: Lore", "subtype: Faction\nmembers: []"))
    text = VALID.replace(
        "subtype: Lore",
        "subtype: Object\ncustom: allowed\n"
        'campaign_1:\n  first_session: "[[S-1-001]]"\n'
        '  last_session: "[[S-1-001]]"\n'
        '  held_by: ["[[Holder]]", GONE]',
    )
    path = write(vault, text.replace("- N/A", "- [[S-1-001]]: Acquired."))
    assert not rules(path)
    path.write_text(path.read_text().replace("[[Holder]]", "[[types/Content]]"))
    assert "target.kind" in rules(path)


def test_two_campaign_histories(vault: Path) -> None:
    sessions(vault)
    other = vault / "campaigns/campaign_42/sessions"
    other.mkdir(parents=True)
    (other / "S-42-005.md").write_text(
        '---\ntype: "[[types/Session]]"\nsession_number: 5\n---\n'
    )
    path = write(
        vault,
        VALID.replace(
            "summary:",
            "summary:\n"
            'campaign_1:\n  first_session: "[[S-1-001]]"\n'
            '  last_session: "[[S-1-001]]"\n'
            'campaign_42:\n  first_session: "[[S-42-005]]"\n'
            '  last_session: "[[S-42-005]]"',
        ).replace(
            "- N/A",
            "### campaign_1\n- [[S-1-001]]: Appeared.\n"
            "### campaign_42\n- [[S-42-005]]: Appeared separately.",
        ),
    )
    assert not rules(path)


def test_alias_shapes_empty_nulls_and_schema_locality(vault: Path) -> None:
    path = write(vault, VALID.replace("summary:", "aliases: []\nsummary:"))
    assert not rules(path)
    path.write_text(VALID.replace("summary:", "aliases: 3\nsummary:"))
    assert "schema.instance" in rules(path)
    path.write_text(VALID)
    (vault / "reference/schemas/content.schema.json").write_text("false")
    assert "schema.instance" in rules(path)


def test_filename_and_case_collisions(vault: Path) -> None:
    path = vault / "content/ Leading.md"
    path.write_text(VALID)
    assert "record.filename" in rules(path)
    other = vault / "extra"
    other.mkdir()
    (other / "leading.md").write_text("page")
    (vault / "content/Leading.md").write_text("page")
    index = VaultIndex(vault)
    assert index.resolve("LEADING", path)[1] == "link.ambiguous"
    assert index.resolve("extra/LEADING", path)[0] == other / "leading.md"


def test_blank_vault_reference_contracts(vault: Path) -> None:
    (vault / "reference/statuses/Pending.md").write_text(
        '---\napplies_to: "[[types/Content]]"\n---\n'
    )
    (vault / "reference/templates/Clue.md").write_text(
        '---\ntype: "[[types/Content]]"\n---\n'
    )
    assert {"vault.status", "vault.template"} <= rules(vault)


def test_asset_cannot_satisfy_record_relationship(vault: Path) -> None:
    (vault / "assets/holder.txt").write_text("asset")
    path = write(
        vault, VALID.replace("subtype: Lore", 'subtype: PC\nplayer: "[[holder.txt]]"')
    )
    assert "target.kind" in rules(path)


def test_cli_reports_link_syntax_and_directory_continues(vault: Path) -> None:
    path = write(vault, VALID.replace("## Notes", "## Notes\n[[broken"))
    (path.parent / "Another.md").write_text(VALID)
    before = path.read_bytes()
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from armarium.cli import main; raise SystemExit(main())",
            "validate",
            str(path.parent),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "link.syntax" in result.stdout and "content/Test.md:" in result.stdout
    assert "2 checked" in result.stdout
    assert path.read_bytes() == before
