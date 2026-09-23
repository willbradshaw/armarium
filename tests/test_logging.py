"""Logging configuration, timestamps and validation reporting."""

import logging
import time
from collections.abc import Iterator

import pytest

from armarium.logging import (
    _LogFormatter,
    configure_logging,
    logger,
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
            (0, None, "2026-01-02 03:04:05.00 UTC"),
            (129, None, "2026-01-02 03:04:05.12 UTC"),
            (999, None, "2026-01-02 03:04:05.99 UTC"),
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
        assert formatter.converter is time.gmtime
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
