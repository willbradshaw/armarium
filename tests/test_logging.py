"""Logging configuration, timestamps and validation reporting."""

import logging
import time
from collections.abc import Iterator
from typing import Literal

import pytest

from armarium.lib import Diagnostic, Result
from armarium.logging import (
    _LogFormatter,
    configure_logging,
    logger,
    report_diagnostics,
)


@pytest.fixture(autouse=True)
def preserve_logger() -> Iterator[None]:
    handlers, level, propagate = logger.handlers[:], logger.level, logger.propagate
    yield
    logger.handlers, logger.level, logger.propagate = handlers, level, propagate


class TestLogFormatter:
    def test_level_and_message(self) -> None:
        record = logging.LogRecord(
            "test", logging.WARNING, "", 1, "Hello %s", ("world",), None
        )
        output = _LogFormatter("[%(asctime)s] %(levelname)s: %(message)s").format(
            record
        )
        assert output.endswith("] WARNING: Hello world")


class TestLogFormatterFormatTime:
    @pytest.mark.parametrize(
        ("milliseconds", "datefmt", "expected"),
        [
            (0, None, "2026-01-02 03:04:05.00"),
            (129, None, "2026-01-02 03:04:05.12"),
            (999, None, "2026-01-02 03:04:05.99"),
            (129, "%Y", "2026"),
        ],
    )
    def test_timestamp(
        self, milliseconds: int, datefmt: str | None, expected: str
    ) -> None:
        record = logging.LogRecord("test", logging.INFO, "", 1, "message", (), None)
        record.created = 1767323045
        record.msecs = milliseconds
        formatter = _LogFormatter()
        formatter.converter = time.gmtime
        assert formatter.formatTime(record, datefmt) == expected


class TestConfigureLogging:
    def test_repeated_setup_does_not_duplicate_or_change_root(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        root_handlers = logging.getLogger().handlers[:]
        configure_logging()
        configure_logging()
        logger.debug("Hidden message")
        logger.info("One message")
        output = capsys.readouterr()
        assert output.out == ""
        assert output.err.count("One message") == 1
        assert "Hidden message" not in output.err
        assert logging.getLogger().handlers == root_handlers


class TestReportDiagnostics:
    @pytest.mark.parametrize(
        ("severity", "level", "line", "field", "location"),
        [
            ("error", logging.ERROR, 0, "", "note.md"),
            ("warning", logging.WARNING, 3, "", "note.md:3"),
            ("info", logging.INFO, 0, "type", "note.md [type]"),
            ("error", logging.ERROR, 3, "type", "note.md:3 [type]"),
        ],
    )
    def test_findings(
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
        result = Result([diagnostic], checked=1)
        with caplog.at_level(logging.INFO, logger="armarium"):
            report_diagnostics(result)
        assert caplog.record_tuples == [
            ("armarium", level, f"{location}: record.type: A finding"),
            ("armarium", logging.INFO, "1 checked, 0 skipped, 0 unsupported"),
        ]
        assert result == Result([diagnostic], checked=1)

    @pytest.mark.parametrize("counts", [(0, 0, 0), (2, 1, 1)])
    def test_counts_without_findings(
        self, caplog: pytest.LogCaptureFixture, counts: tuple[int, int, int]
    ) -> None:
        checked, skipped, unsupported = counts
        with caplog.at_level(logging.INFO, logger="armarium"):
            report_diagnostics(
                Result(checked=checked, skipped=skipped, unsupported=unsupported)
            )
        assert caplog.record_tuples == [
            (
                "armarium",
                logging.INFO,
                f"{checked} checked, {skipped} skipped, {unsupported} unsupported",
            ),
        ]
