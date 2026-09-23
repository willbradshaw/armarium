"""Shared syntax and vault-discovery utilities."""

import logging
from pathlib import Path
from typing import Literal

import pytest

from armarium.lib import (
    Diagnostic,
    Result,
    ValidationError,
    VaultNotFoundError,
    _find_wikilink_candidates,
    check_vault,
    find_children,
    find_files,
    find_vault,
    iter_wikilinks,
    parse_wikilink,
)

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


class TestFindVault:
    @pytest.mark.parametrize(
        "target", [".", "content", "content/note.md", "content/new.md"]
    )
    @pytest.mark.parametrize("relative", [False, True])
    def test_inferred_root(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        target: str,
        relative: bool,
    ) -> None:
        root = tmp_path / "vault with spaces"
        (root / "reference/types").mkdir(parents=True)
        (root / "campaigns").mkdir()
        (root / "content").mkdir()
        (root / "content/note.md").write_text("note")
        monkeypatch.chdir(tmp_path)
        path = root / target
        assert (
            find_vault(path.relative_to(tmp_path) if relative else path)
            == root.resolve()
        )

    def test_nearest_vault(self, tmp_path: Path) -> None:
        nested = tmp_path / "outer/nested"
        for root in (tmp_path / "outer", nested):
            (root / "reference/types").mkdir(parents=True)
            (root / "campaigns").mkdir()
        assert find_vault(nested / "note.md") == nested.resolve()

    @pytest.mark.parametrize("marker", [".git", "reference/types", "campaigns"])
    def test_incomplete_structure(self, tmp_path: Path, marker: str) -> None:
        (tmp_path / marker).mkdir(parents=True)
        with pytest.raises(ValueError, match="cannot infer vault"):
            find_vault(tmp_path / "note.md")

    def test_inferred_symlink_cannot_select_destination_vault(
        self, tmp_path: Path
    ) -> None:
        first, second = tmp_path / "first", tmp_path / "second"
        for root in (first, second):
            (root / "reference/types").mkdir(parents=True)
            (root / "campaigns").mkdir()
        (second / "note.md").write_text("outside")
        link = first / "note.md"
        link.symlink_to(second / "note.md")
        with pytest.raises(ValueError, match="escapes the inferred vault"):
            find_vault(link)


class TestCheckVault:
    @pytest.mark.parametrize("relative", [False, True])
    def test_explicit_root_without_markers(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: bool
    ) -> None:
        root = tmp_path / "incomplete"
        root.mkdir()
        monkeypatch.chdir(tmp_path)
        selected = Path("incomplete") if relative else root
        assert check_vault(selected / "new.md", selected) == root.resolve()

    @pytest.mark.parametrize(
        "problem", ["missing-root", "file-root", "outside", "symlink-escape"]
    )
    def test_invalid_explicit_boundary(self, tmp_path: Path, problem: str) -> None:
        root = tmp_path / "vault"
        target = root / "note.md"
        if problem == "file-root":
            root.write_text("file")
        elif problem != "missing-root":
            root.mkdir()
            outside = tmp_path / "outside.md"
            outside.write_text("outside")
            if problem == "outside":
                target = outside
            else:
                target.symlink_to(outside)
        with pytest.raises(ValueError, match="selected vault directory"):
            check_vault(target, root)


class TestFindFiles:
    @pytest.mark.parametrize("relative", [False, True])
    def test_sorted_files_of_all_types(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: bool
    ) -> None:
        names = ["z.md", "nested/Café.md", "assets/map.png", "view.base", "schema.json"]
        for name in names:
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name)
        monkeypatch.chdir(tmp_path)
        root = Path(".") if relative else tmp_path
        assert find_files(root) == sorted(root / name for name in names)
        assert all((tmp_path / name).read_text() == name for name in names)

    @pytest.mark.parametrize(
        "excluded",
        [".git", ".obsidian", ".scratch", ".hidden", "__pycache__", "node_modules"],
    )
    def test_excluded_directories(self, tmp_path: Path, excluded: str) -> None:
        directory = tmp_path / "nested" / excluded
        directory.mkdir(parents=True)
        (directory / "ignored.md").write_text("ignored")
        (tmp_path / ".gitkeep").touch()
        assert find_files(tmp_path) == []

    @pytest.mark.parametrize("kind", ["file", "directory", "broken", "cycle"])
    def test_ignores_symlinks(self, tmp_path: Path, kind: str) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        target = tmp_path / "target"
        if kind == "file":
            target.write_text("outside")
        elif kind == "directory":
            target.mkdir()
            (target / "outside.md").write_text("outside")
        elif kind == "cycle":
            target = root
        (root / "link").symlink_to(target)
        assert find_files(root) == []

    def test_empty_directory(self, tmp_path: Path) -> None:
        assert find_files(tmp_path) == []

    @pytest.mark.parametrize("kind", ["missing", "file", "symlink"])
    def test_invalid_root(self, tmp_path: Path, kind: str) -> None:
        root = tmp_path / "root"
        if kind == "file":
            root.write_text("file")
        elif kind == "symlink":
            root.symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(ValueError, match="real directory"):
            find_files(root)


class TestDiagnosticReport:
    @pytest.mark.parametrize(
        ("severity", "level", "line", "field", "location"),
        [
            ("error", logging.ERROR, 0, "", "note.md"),
            ("warning", logging.WARNING, 3, "", "note.md:3"),
            ("info", logging.INFO, 0, "type", "note.md [type]"),
            ("error", logging.ERROR, 3, "type", "note.md:3 [type]"),
        ],
    )
    def test_finding(
        self,
        caplog: pytest.LogCaptureFixture,
        severity: Literal["error", "warning", "info"],
        level: int,
        line: int,
        field: str,
        location: str,
    ) -> None:
        diagnostic = Diagnostic(
            "note.md",
            "record.type",
            "A finding",
            line=line,
            field=field,
            severity=severity,
        )
        with caplog.at_level(logging.INFO, logger="armarium"):
            diagnostic.report()
        assert caplog.record_tuples == [
            ("armarium", level, f"{location}: record.type: A finding"),
        ]


class TestResultReport:
    @pytest.mark.parametrize("with_findings", [False, True])
    def test_findings_then_counts(
        self, caplog: pytest.LogCaptureFixture, with_findings: bool
    ) -> None:
        findings = (
            [
                Diagnostic("first.md", "first", "First", severity="warning"),
                Diagnostic("second.md", "second", "Second"),
            ]
            if with_findings
            else []
        )
        result = Result(findings, checked=2, skipped=1, unsupported=1)
        with caplog.at_level(logging.INFO, logger="armarium"):
            result.report()
        expected = (
            [
                ("armarium", logging.WARNING, "first.md: first: First"),
                ("armarium", logging.ERROR, "second.md: second: Second"),
            ]
            if with_findings
            else []
        )
        assert caplog.record_tuples == expected + [
            ("armarium", logging.INFO, "2 checked, 1 skipped, 1 unsupported"),
        ]
        assert result == Result(findings, checked=2, skipped=1, unsupported=1)


class TestResultFailedFiles:
    @pytest.mark.parametrize(
        ("findings", "expected"),
        [
            ([], 0),
            ([("a.md", "warning"), ("b.md", "info")], 0),
            ([("a.md", "error")], 1),
            ([("a.md", "error"), ("a.md", "error")], 1),
            ([("a.md", "error"), ("b.md", "error"), ("c.md", "warning")], 2),
        ],
    )
    def test_distinct_error_paths(
        self,
        findings: list[tuple[str, Literal["error", "warning", "info"]]],
        expected: int,
    ) -> None:
        result = Result(
            [
                Diagnostic(path, "test", "Finding", severity=severity)
                for path, severity in findings
            ]
        )
        assert result.failed_files == expected


class TestValidationError:
    def test_preserves_message(self) -> None:
        error = ValidationError("2 files failed validation")
        assert isinstance(error, Exception)
        assert str(error) == "2 files failed validation"


class TestResultAdd:
    @pytest.mark.parametrize("empty", [False, True])
    def test_combines_without_mutating_inputs(self, empty: bool) -> None:
        left = Result([Diagnostic("z.md", "z", "Error")], checked=1, skipped=2)
        right = (
            Result()
            if empty
            else Result(
                [Diagnostic("a.md", "a", "Warning", severity="warning")],
                checked=2,
                unsupported=1,
            )
        )
        combined = left + right
        assert combined.checked == (1 if empty else 3)
        assert combined.skipped == 2
        assert combined.unsupported == (0 if empty else 1)
        assert [d.path for d in combined.diagnostics] == (
            ["z.md"] if empty else ["a.md", "z.md"]
        )
        assert sum([left, right], Result()) == combined
        combined.diagnostics.clear()
        assert len(left.diagnostics) == 1
        assert len(right.diagnostics) == (0 if empty else 1)

    def test_unsupported_operand(self) -> None:
        assert Result().__add__(object()) is NotImplemented


class TestVaultNotFoundError:
    def test_discovery_failure_is_specific(self, tmp_path: Path) -> None:
        with pytest.raises(VaultNotFoundError, match="cannot infer vault"):
            find_vault(tmp_path)
        assert isinstance(VaultNotFoundError("Missing"), ValueError)


class TestFindChildren:
    def test_sorted_immediate_children_and_exclusions(self, tmp_path: Path) -> None:
        for name in ("folder", ".git", "__pycache__", "node_modules"):
            (tmp_path / name).mkdir()
            (tmp_path / name / "nested.md").write_text("nested")
        (tmp_path / "a.md").write_text("visible")
        (tmp_path / ".hidden.md").write_text("hidden")
        (tmp_path / "link").symlink_to(tmp_path / "folder", target_is_directory=True)
        assert find_children(tmp_path) == [tmp_path / "a.md", tmp_path / "folder"]

    @pytest.mark.parametrize("kind", ["missing", "file", "symlink"])
    def test_invalid_root(self, tmp_path: Path, kind: str) -> None:
        root = tmp_path / "root"
        if kind == "file":
            root.write_text("file")
        elif kind == "symlink":
            root.symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(ValueError, match="real directory"):
            find_children(root)
