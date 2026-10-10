"""Enterprise logging configuration."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from backend.settings import get_settings


def _kv_formatter() -> logging.Formatter:
    # Use a simple key=value formatter to keep logs structured without
    # introducing external JSON dependencies.
    return logging.Formatter(
        "time=%(asctime)s level=%(levelname)s logger=%(name)s msg=%(message)s"
    )


def configure_logging(log_dir: Optional[str] = "logs") -> None:
    """Configure console and rotating file logging handlers.

    Creates a few named loggers used by different subsystems so their
    output can be filtered independently in production.
    """

    settings = get_settings()
    base = Path(log_dir)
    base.mkdir(exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())
    root_logger.handlers.clear()

    formatter = _kv_formatter()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    info_handler = RotatingFileHandler(base / "qshield_twin.log", maxBytes=1_048_576, backupCount=5)
    info_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(base / "qshield_twin.error.log", maxBytes=1_048_576, backupCount=5)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(info_handler)
    root_logger.addHandler(error_handler)

    # Subsystem loggers
    logging.getLogger("qshield.request").setLevel(settings.log_level.upper())
    logging.getLogger("qshield.websocket").setLevel(settings.log_level.upper())
    logging.getLogger("qshield.performance").setLevel(settings.log_level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
