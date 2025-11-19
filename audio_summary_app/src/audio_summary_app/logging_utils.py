"""
Lightweight debug logging utilities for Audio Summary.

Writes to a single rotating-style log file intended for support diagnostics.
Logging is disabled by default and can be enabled via Config / Settings.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional


LOG_NAME = "audio_summary_app"


def _default_log_path() -> Path:
    """
    Default log path.

    On macOS we follow the convention used in ISSUES.md:
      ~/Library/Logs/Audio Summary/last.log
    On other platforms this still produces a sensible per-user location.
    """
    home = Path.home()
    return home / "Library" / "Logs" / "Audio Summary" / "last.log"


def get_logger(enabled: bool, log_file_path: Optional[str] = None) -> Optional[logging.Logger]:
    """
    Return a module-level logger configured to write to the given file.

    If `enabled` is False, returns None so callers can skip logging.
    Subsequent calls reuse the same logger/handler.
    """
    if not enabled:
        return None

    log_path = Path(log_file_path) if log_file_path else _default_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOG_NAME)
    if logger.handlers:
        return logger

    handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def log_debug(logger: Optional[logging.Logger], message: str) -> None:
    if logger:
        logger.debug(message)


def log_info(logger: Optional[logging.Logger], message: str) -> None:
    if logger:
        logger.info(message)


def log_warning(logger: Optional[logging.Logger], message: str) -> None:
    if logger:
        logger.warning(message)


def log_error(logger: Optional[logging.Logger], message: str) -> None:
    if logger:
        logger.error(message)

