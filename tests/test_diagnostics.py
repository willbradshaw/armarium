"""Failure policy and aggregation contracts shared by validation callers."""

from typing import Literal

import pytest

from armarium.lib import Diagnostic, Result


class TestDiagnostic:
    def test_sorting_preserves_locations(self) -> None:
        field_error = Diagnostic(
            "content/A.md", "schema.required", "Missing name", field="frontmatter.name"
        )
        line_error = Diagnostic("content/B.md", "parse.invalid", "Invalid YAML", line=4)
        other_rule = Diagnostic("content/A.md", "link.missing", "Missing target")
        findings = [line_error, field_error, other_rule]
        expected = [other_rule, field_error, line_error]
        assert sorted(findings) == sorted(reversed(findings)) == expected
        assert expected[1].field == "frontmatter.name"
        assert expected[2].line == 4


class TestResult:
    def test_independent_findings(self) -> None:
        first, second = Result(), Result()
        first.diagnostics.append(
            Diagnostic("content/Test.md", "parse.invalid", "Invalid YAML", line=3)
        )
        assert first.failed
        assert second.diagnostics == []
        assert not second.failed
        first.diagnostics.clear()
        assert not first.failed


class TestResultFailed:
    @pytest.mark.parametrize(
        ("severities", "failed"),
        [
            ([], False),
            (["warning"], False),
            (["info"], False),
            (["error"], True),
            (["warning", "info", "error"], True),
        ],
    )
    def test_severity(
        self, severities: list[Literal["error", "warning", "info"]], failed: bool
    ) -> None:
        result = Result(
            diagnostics=[
                Diagnostic("content/Test.md", "test.rule", "Finding", severity=severity)
                for severity in severities
            ],
            checked=3,
            skipped=2,
            unsupported=1,
        )
        assert result.failed is failed
