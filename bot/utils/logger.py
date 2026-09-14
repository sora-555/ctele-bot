"""Logging setup: console + rotating file, with secret redaction."""

from __future__ import annotations

import contextlib
import logging
import logging.handlers
import os
import sys
from pathlib import Path

_SECRETS: list[str] = []


class RedactFilter(logging.Filter):
    """Blanks out configured secrets (bot token, DSN password) in log output."""

    def filter(self, record: logging.LogRecord) -> bool:
        if _SECRETS:
            try:
                message = record.getMessage()
            except Exception:
                return True
            redacted = message
            for secret in _SECRETS:
                if secret and secret in redacted:
                    redacted = redacted.replace(secret, "***")
            if redacted != message:
                record.msg = redacted
                record.args = ()
        return True


def register_secret(value: str | None) -> None:
    if value:
        _SECRETS.append(value)


def setup_logging(level: str = "INFO", log_dir: str = "logs") -> logging.Logger:
    root = logging.getLogger()
    if root.handlers:
        return root

    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Titles from the source are frequently non-Latin, so never let an encoding
    # error in a log line take the process down (or spam a traceback).
    if hasattr(sys.stderr, "reconfigure"):
        with contextlib.suppress(ValueError, OSError):
            sys.stderr.reconfigure(errors="replace")
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.addFilter(RedactFilter())
    root.addHandler(console)

    try:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "bot.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
            errors="replace",
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RedactFilter())
        root.addHandler(file_handler)
    except OSError:
        root.warning("file logging disabled: %s is not writable", log_dir)

    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    return root