"""Configure shared application logging."""

import logging
import time

logger = logging.getLogger("armarium")


class _LogFormatter(logging.Formatter):
    """Format UTC timestamps to hundredths of a second."""

    converter = staticmethod(time.gmtime)

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Render a log record's creation time.

        Args:
            record: Record whose timestamp should be formatted.
            datefmt: Optional explicit strftime format, overriding the default.

        Returns:
            str: UTC time as YYYY-MM-DD HH:MM:SS.SS UTC, or the requested format.
        """
        timestamp = super().formatTime(record, datefmt or "%Y-%m-%d %H:%M:%S")
        return (
            timestamp if datefmt else f"{timestamp}.{int(record.msecs) // 10:02d} UTC"
        )


def configure_logging() -> None:
    """Configure this command's logger to emit timestamped messages to stderr.

    Replace this logger's handlers so repeated calls do not duplicate output.
    Other application loggers are left unchanged.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(_LogFormatter("[%(asctime)s] %(levelname)s: %(message)s"))
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
