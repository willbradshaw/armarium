"""Context uses the complete vault but reports only selected-record dependencies."""

from pathlib import Path

from test_intrafile import VALID, write

from armarium.index import VaultIndex
from armarium.validation import validate


def context_rules(path: Path) -> set[str]:
    """Context assertions remain focused as later stages add history rules."""
    return {rule for rule in rules(path) if not rule.startswith("history.")}


def rules(path: Path) -> set[str]:
    return {d.rule for d in validate(path).diagnostics if d.severity == "error"}


def test_suffix_alias_assets_unicode_and_anchors(vault: Path) -> None:
    path = write(
        vault,
        VALID + "\n[[types/Content]] [[Test.md#Heading|Display]] "
        "[[#^block]] ![[hand out.txt]] [[Café\\|Display]]",
    )
    (vault / "assets/hand out.txt").write_text("asset")
    (vault / "content/Café.md").write_text("untyped page")
    assert not context_rules(path)
    (vault / "content/Other.md").write_text("---\naliases: [Nickname]\n---\n")
    path.write_text(VALID + "[[Nickname]]")
    assert "link.missing" in rules(path)
    (vault / "content/Content.md").write_text("another basename")
    path.write_text(VALID + "[[Content]]")
    assert "link.ambiguous" in rules(path)
    path.write_text(VALID + "[[types/Content]]")
    assert not context_rules(path)


def test_fences_queries_and_malformed_dependency(vault: Path) -> None:
    path = write(vault, VALID + "\n```markdown\n[[Missing]]\n```\n")
    (vault / "content/Bad.md").write_text("---\nx: [\n---\n")
    assert not context_rules(path)
    path.write_text(VALID + "\n```dataview\nWHERE x = [[Missing]]\n```\n")
    assert "link.missing" in rules(path)
    path.write_text(VALID + "`= [[Missing]].text`")
    assert "link.missing" in rules(path)
    path.write_text(VALID + "[[Bad]]")
    assert "link.malformed" in rules(path)


def test_placement_identity_campaign_and_kinds(vault: Path) -> None:
    path = vault / "campaigns/campaign_1/sessions/S-1-001.md"
    path.write_text(
        '---\ntype: "[[types/Session]]"\nsession_number: 2\n'
        'campaign: "[[types/Content]]"\n---\n'
    )
    assert {"record.identity", "campaign.mismatch"} <= rules(path)
    moved = vault / "content/S-1-001.md"
    moved.write_text(path.read_text())
    assert "record.placement" in rules(moved)
    pc = write(
        vault, VALID.replace("subtype: Lore", 'subtype: PC\nplayer: "[[types/Player]]"')
    )
    assert "target.kind" in rules(pc)
    pc.write_text(
        VALID.replace("subtype: Lore", 'subtype: Location\nparent_location: "[[Test]]"')
    )
    assert not context_rules(pc)
    pc.write_text(
        VALID.replace("subtype: Lore", 'subtype: Faction\nmembers: ["[[Test]]"]')
    )
    assert "target.kind" in rules(pc)


def test_multidigit_campaign_and_status(vault: Path) -> None:
    directory = vault / "campaigns/campaign_42"
    (directory / "sessions").mkdir(parents=True)
    (directory / "reference").mkdir()
    (directory / "reference/Campaign.md").write_text("overview")
    path = directory / "sessions/S-42-002.md"
    path.write_text(
        '---\ntype: "[[types/Session]]"\nsession_number: 2\n'
        'campaign: "[[campaign_42/reference/Campaign]]"\n---\n'
    )
    assert not context_rules(path)
    content = write(
        vault,
        VALID.replace(
            "summary:",
            'summary:\ncampaign_1:\n  first_session: "[[S-42-002]]"\n'
            '  last_session: "[[S-42-002]]"',
        ),
    )
    assert "campaign.mismatch" in rules(content)
    path.write_text(
        path.read_text().replace(
            "session_number: 2", 'status: "[[Pending]]"\nsession_number: 2'
        )
    )
    assert "status.applicability" in rules(path)


def test_symlink_not_indexed(vault: Path, tmp_path: Path) -> None:
    outside = tmp_path / "secret.md"
    outside.write_text("private")
    (vault / "content/escape.md").symlink_to(outside)
    assert (
        VaultIndex(vault).resolve("escape", vault / "content/Test.md")[1]
        == "link.missing"
    )


def test_invalid_link_syntax_reports_locations_and_continues(vault: Path) -> None:
    path = write(vault, VALID.replace("## Notes", "## Notes\n[[broken [[Missing]]"))
    before = path.read_bytes()
    result = validate(path)
    syntax = [d for d in result.diagnostics if d.rule == "link.syntax"]
    expected_line = path.read_text().splitlines().index("[[broken [[Missing]]") + 1
    assert len(syntax) == 1 and syntax[0].line == expected_line
    assert syntax[0].path == "content/Test.md" and syntax[0].severity == "error"
    assert "link.missing" in {d.rule for d in result.diagnostics}
    assert result.failed and path.read_bytes() == before


def test_bad_wikilinks_in_frontmatter_and_body(vault: Path) -> None:
    path = write(
        vault,
        VALID.replace("summary:", 'summary: "[[ ]]"').replace(
            "## Notes", "## Notes\n[[]]\n[[unclosed\nstray ]]"
        ),
    )
    result = validate(path)
    errors = [d for d in result.diagnostics if d.rule == "link.syntax"]
    assert len(errors) == 4
    assert any(d.field == "summary" for d in errors)
    assert len([d for d in errors if d.line]) == 3


def test_invalid_wikilinks_ignore_examples_but_check_queries(vault: Path) -> None:
    path = write(
        vault, VALID.replace("## Notes", "## Notes\n```markdown\n[[broken\n```\n")
    )
    assert not validate(path).failed
    path.write_text(path.read_text().replace("```markdown", "```dataview"))
    assert "link.syntax" in rules(path)
    path.write_text(VALID.replace("## Notes", "## Notes\n`= [[broken`"))
    assert "link.syntax" in rules(path)
