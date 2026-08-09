"""PII-safe logging (SEC-10/SEC-11): masking helpers and a logging filter.

Default posture: bfs_core loggers emit positions and codes, never raw values.
Where a value is unavoidable in a persisted message, mask it first.
"""

from __future__ import annotations

import logging
import re

_IBAN_RE = re.compile(r"\b([A-Z]{2}\d{2})[A-Z0-9]{6,26}([A-Z0-9]{4})\b")
_LONG_NUMBER_RE = re.compile(r"\b(\d{2})\d{4,}(\d{2})\b")


def mask_value(text: str) -> str:
    """Mask account-number-like tokens: IBANs to 'DE89…3000' style, long digit
    runs to first/last two digits."""
    masked = _IBAN_RE.sub(lambda m: f"{m.group(1)}…{m.group(2)}", text)
    return _LONG_NUMBER_RE.sub(lambda m: f"{m.group(1)}…{m.group(2)}", masked)


class RedactingFilter(logging.Filter):
    """Attach to any persisted-log handler: masks account-like tokens in every
    record message (defence in depth on top of the no-PII logging policy)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask_value(str(record.msg))
        if record.args:
            record.args = tuple(
                mask_value(a) if isinstance(a, str) else a for a in record.args
            )
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(RedactingFilter())
    return logger
