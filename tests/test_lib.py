"""Shared link utilities reject malformed syntax and preserve scan recovery."""

from pathlib import Path

import pytest

from armarium.lib import _find_wikilink_candidates, iter_wikilinks, parse_wikilink

_INVALID_BRACKETS = "use [[target]] with balanced double brackets on one line"


class TestParseWikilink:
    @pytest.mark.parametrize(
        ("value", "canonical", "expected"),
        [
            ("[[types/Content.md]]", True, "types/Content.md"),
            ("[[Café|Display]]", False, "Café"),
            (r"[[Café\|Display]]", False, "Café"),
            ("[[Note#Heading|Display]]", False, "Note"),
            ("[[#^block]]", False, ""),
            (
                "[[campaign_2/reference/Campaign]]",
                True,
                "campaign_2/reference/Campaign",
            ),
            (
                "[[reference/views/clue-index.base#Closed]]",
                False,
                "reference/views/clue-index.base",
            ),
        ],
    )
    def test_valid(self, value: str, canonical: bool, expected: str) -> None:
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
    def test_invalid(self, value: object, canonical: bool, message: str) -> None:
        with pytest.raises(ValueError, match=message):
            parse_wikilink(value, canonical=canonical)


class TestFindWikilinkCandidates:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("", []),
            ("ordinary [text]", []),
            ("before [[One]] and [[Two]]", ["[[One]]", "[[Two]]"]),
            ("[[]]", ["[[]]"]),
            ("[[first\nsecond]]", ["[[first\nsecond]]"]),
            ("[[open", ["[[open"]),
            ("[[broken [[Good]] then ]]", ["[[broken ", "[[Good]]", "]]"]),
        ],
    )
    def test_candidates(self, text: str, expected: list[str]) -> None:
        assert list(_find_wikilink_candidates(text)) == expected


class TestIterWikilinks:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("", []),
            ("ordinary [text]", []),
            (
                r"[[Café\|Display]] [[Note#Heading|Label]] [[#^block]] [[Café]]",
                ["Café", "Note", "", "Café"],
            ),
            (
                "[[first\nsecond]]",
                [ValueError(_INVALID_BRACKETS)],
            ),
            (
                "[[ ]] [[Good]]",
                [ValueError("wikilink target must not be empty"), "Good"],
            ),
            (
                "[[]] [[broken [[Good]] then ]] [[open",
                [
                    ValueError(_INVALID_BRACKETS),
                    ValueError(_INVALID_BRACKETS),
                    "Good",
                    ValueError(_INVALID_BRACKETS),
                    ValueError(_INVALID_BRACKETS),
                ],
            ),
        ],
    )
    def test_results(self, text: str, expected: list[str | ValueError]) -> None:
        results = list(iter_wikilinks(text))
        assert len(results) == len(expected)
        for actual, wanted in zip(results, expected):
            assert type(actual) is type(wanted)
            assert str(actual) == str(wanted)

    def test_named_base_embeds_and_preparation_lists(self) -> None:
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
    def test_shipped_vault_link_syntax(self, vault: str) -> None:
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
