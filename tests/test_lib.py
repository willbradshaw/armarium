"""Shared link utilities reject malformed syntax and preserve scan recovery."""

from pathlib import Path

import pytest

from armarium.lib import iter_wikilinks, parse_wikilink


@pytest.mark.parametrize(
    ("value", "canonical", "expected"),
    [
        ("[[types/Content.md]]", True, "types/Content.md"),
        ("[[Café|Display]]", False, "Café"),
        (r"[[Café\|Display]]", False, "Café"),
        ("[[Note#Heading|Display]]", False, "Note"),
        ("[[#^block]]", False, ""),
        ("[[campaign_2/reference/Campaign]]", True, "campaign_2/reference/Campaign"),
        (
            "[[reference/views/clue-index.base#Closed]]",
            False,
            "reference/views/clue-index.base",
        ),
    ],
)
def test_parse_wikilink(value: str, canonical: bool, expected: str) -> None:
    assert parse_wikilink(value, canonical=canonical) == expected


@pytest.mark.parametrize(
    ("value", "canonical", "message"),
    [
        ("[[Note|Display]]", True, "canonical wikilinks"),
        ("[[Note#Heading]]", True, "canonical wikilinks"),
        ("[[#Heading]]", True, "canonical wikilinks"),
        ("[[ ]]", False, "target must not be empty"),
        ("[[]]", False, "balanced double brackets"),
        ("[[Note\ncontinued]]", False, "one line"),
        ("text [[Note]]", False, "balanced double brackets"),
        ("[[Unclosed", False, "balanced double brackets"),
        ("[[Outer [[Inner]]", False, "balanced double brackets"),
        (None, True, "must be a string"),
    ],
)
def test_parse_wikilink_rejects_invalid_input(
    value: object, canonical: bool, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        parse_wikilink(value, canonical=canonical)


def test_iter_wikilinks_reports_errors_and_recovers() -> None:
    text = "text [[]] [[broken [[Good]] then ]] [[open"
    results = list(iter_wikilinks(text))
    assert len(results) == 5
    assert results[2] == "Good"
    for index in (0, 1, 3, 4):
        error = results[index]
        assert isinstance(error, ValueError)
        assert "balanced double brackets" in str(error)


def test_iter_wikilinks_reports_multiline_links() -> None:
    results = list(iter_wikilinks("[[first\nsecond]]"))
    assert len(results) == 1
    assert isinstance(results[0], ValueError)
    assert "one line" in str(results[0])
    assert list(iter_wikilinks("ordinary [text]")) == []


def test_iter_wikilinks_returns_parsed_targets_and_preserves_self_anchors() -> None:
    text = r"[[Café\|Display]] [[Note#Heading|Label]] [[#^block]] [[ ]] [[Café]]"
    results = list(iter_wikilinks(text))
    assert results[:3] == ["Café", "Note", ""]
    assert isinstance(results[3], ValueError)
    assert "target must not be empty" in str(results[3])
    assert results[4] == "Café"


def test_iter_wikilinks_accepts_named_base_embeds_and_preparation_lists() -> None:
    text = (
        "![[reference/views/clue-index.base#Active]]\n"
        'prepared_clues: ["[[C-2-0001]]", "[[C-2-0002]]"]\n'
        "![[reference/views/prepared-clues.base]]\n"
    )
    assert list(iter_wikilinks(text)) == [
        "reference/views/clue-index.base",
        "C-2-0001",
        "C-2-0002",
        "reference/views/prepared-clues.base",
    ]


@pytest.mark.parametrize("vault", ["starter", "example"])
def test_shipped_vault_link_syntax(vault: str) -> None:
    """Exercise current templates, shared records, both campaigns and Base embeds.

    This checks only syntax, not target existence, scope or view execution.
    """
    root = Path(__file__).resolve().parents[1] / "vaults" / vault
    files = list(root.rglob("*.md"))
    assert files
    for path in files:
        errors = [
            str(item)
            for item in iter_wikilinks(path.read_text())
            if isinstance(item, ValueError)
        ]
        assert not errors, (path.relative_to(root), errors)
