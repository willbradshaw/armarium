"""Configure command logging and render validation results."""

import logging

from armarium.lib import Result

logger = logging.getLogger("armarium")


class _LogFormatter(logging.Formatter):
    """Format local timestamps to hundredths of a second."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Render a log record's creation time.

        Args:
            record: Record whose timestamp should be formatted.
            datefmt: Optional explicit strftime format, overriding the default.

        Returns:
            str: Local time as YYYY-MM-DD HH:MM:SS.SS, or the requested format.
        """
        timestamp = super().formatTime(record, datefmt or "%Y-%m-%d %H:%M:%S")
        return timestamp if datefmt else f"{timestamp}.{int(record.msecs) // 10:02d}"


def configure_logging() -> None:
    """Configure this command's logger to emit timestamped messages to stderr.

    Returns:
        None: Replace this logger's handlers so repeated main calls do not
            duplicate output. Other application loggers are left unchanged.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(_LogFormatter("[%(asctime)s] %(levelname)s: %(message)s"))
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False


def report_diagnostics(result: Result) -> None:
    """Log findings at their severity, followed by coverage counts at INFO.

    Args:
        result: Validation findings and counts to report without modifying them.

    Returns:
        None: Emit log records through the Armarium logger.
    """
    levels = {"error": logging.ERROR, "warning": logging.WARNING, "info": logging.INFO}
    for diagnostic in result.diagnostics:
        location = diagnostic.path
        if diagnostic.line:
            location += f":{diagnostic.line}"
        if diagnostic.field:
            location += f" [{diagnostic.field}]"
        logger.log(
            levels[diagnostic.severity],
            "%s: %s: %s",
            location,
            diagnostic.rule,
            diagnostic.message,
        )
    logger.info(
        "%s checked, %s skipped, %s unsupported",
        result.checked,
        result.skipped,
        result.unsupported,
    )
