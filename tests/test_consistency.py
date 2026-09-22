"""Histories track explicit appearances; Clue preparation is independent."""

from pathlib import Path

from test_intrafile import VALID, write

from armarium.validation import validate


def sessions(vault: Path) -> None:
    for number in (1, 2):
        path = vault / f"campaigns/campaign_1/sessions/S-1-{number:03}.md"
        path.write_text(
            f'---\ntype: "[[types/Session]]"\nsession_number: {number}\n'
            'campaign: "[[Campaign]]"\n---\n'
        )


def history(
    vault: Path, bullets: str, first: str = "S-1-001", last: str = "S-1-002"
) -> Path:
    sessions(vault)
    return write(
        vault,
        VALID.replace(
            "summary:",
            f'summary:\ncampaign_1:\n  first_session: "[[{first}]]"\n'
            f'  last_session: "[[{last}]]"',
        ).replace("- N/A", bullets),
    )


def test_history_ranges_order_duplicates_and_mentions(vault: Path) -> None:
    path = history(vault, "- [[S-1-001]]: Appeared.\n- [[S-1-002]]: Returned.")
    assert not validate(path).failed
    path.write_text(
        path.read_text().replace("- [[S-1-002]]: Returned.", "- [[S-1-001]]: Repeated.")
    )
    rules = {d.rule for d in validate(path).diagnostics}
    assert {"history.duplicate", "history.range"} <= rules
    path = history(vault, "- [[S-1-002]]: Later.\n- [[S-1-001]]: Earlier.")
    assert "history.order" in {d.rule for d in validate(path).diagnostics}
    path.write_text(VALID + "\n[[S-1-001]]")
    assert "history.format" in {d.rule for d in validate(path).diagnostics}
    path.write_text(VALID.replace("## Notes", "## Notes\nMention [[S-1-001]]."))
    assert not validate(path).failed


def test_clue_preparation_abandonment_and_subject_aliases(vault: Path) -> None:
    sessions(vault)
    write(vault, VALID)
    clue = vault / "campaigns/campaign_1/clues/C-1-0001.md"
    clue.write_text(
        '---\ntype: "[[types/Clue]]"\nstatus: "[[Abandoned]]"\n'
        'text: "Maybe [[content/Test|this entity]] did it."\n'
        'subjects: ["[[Test]]"]\nfirst_session: "[[S-1-001]]"\n'
        "last_session:\n---\n## Sessions\n"
    )
    assert not validate(clue).failed
    clue.write_text(clue.read_text().replace('subjects: ["[[Test]]"]', "subjects: []"))
    assert "clue.subjects" in {d.rule for d in validate(clue).diagnostics}


def test_history_heading_agreement_and_empty(vault: Path) -> None:
    path = history(vault, "### campaign_42\n- [[S-1-001]]: Appeared.", last="S-1-001")
    assert "history.campaign" in {d.rule for d in validate(path).diagnostics}
    path.write_text(
        VALID.replace(
            "summary:", "summary:\ncampaign_42:\n  first_session:\n  last_session:"
        )
    )
    assert not validate(path).failed
