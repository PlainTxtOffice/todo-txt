"""Configure repository logging for console, app, and request channels."""

from __future__ import annotations

import logging
import logging.config
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.config.path_handler import LOGS_DIR

MAX_LOG_BYTES = 1_000_000
LOG_BACKUP_COUNT = 3
ROOT_LOG_LEVEL = "DEBUG"
FILE_LOG_LEVEL = "DEBUG"
CONSOLE_LOG_LEVEL = "INFO"
EST = timezone(timedelta(hours=-5), name="EST")


class EstFormatter(logging.Formatter):
    """Format timestamps in fixed EST using a 12-hour clock."""

    def formatTime(
        self,
        record: logging.LogRecord,
        datefmt: str | None = None,
    ) -> str:
        """Render log-record time in fixed EST with an optional date format."""
        dt = datetime.fromtimestamp(record.created, tz=EST)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat(timespec="minutes")


def _rotating_handler_factory(filename: str) -> RotatingFileHandler:
    """Create a rotating file handler with shared sizing and naming rules."""
    handler = RotatingFileHandler(
        filename=filename,
        maxBytes=MAX_LOG_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    source_path = Path(filename)

    def _rotated_log_namer(default_name: str) -> str:
        rotated_path = Path(default_name)
        rotation_suffix = rotated_path.suffix.lstrip(".")
        base_stem = source_path.stem
        base_stem = base_stem.removesuffix(".log")
        return str(rotated_path.with_name(f"{base_stem}.{rotation_suffix}.log"))

    handler.namer = _rotated_log_namer
    return handler


def configure_logging(project_name: str | None = None) -> None:
    """Configure application logging using dictConfig."""
    logs_dir = LOGS_DIR
    api_dir = logs_dir / "api"
    logs_dir.mkdir(parents=True, exist_ok=True)
    api_dir.mkdir(parents=True, exist_ok=True)

    if not project_name:
        project_name = logs_dir.parent.name
    safe_project_name = project_name.replace(" ", "_")

    config: dict[str, object] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "file_detail": {
                "()": EstFormatter,
                "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %I:%M%p",
            },
            "console_minimal": {
                "format": "%(message)s",
            },
        },
        "handlers": {
            "app_file": {
                "()": _rotating_handler_factory,
                "filename": str(logs_dir / f"{safe_project_name}.log"),
                "formatter": "file_detail",
                "level": FILE_LOG_LEVEL,
            },
            "api_file": {
                "()": _rotating_handler_factory,
                "filename": str(api_dir / "http.log"),
                "formatter": "file_detail",
                "level": FILE_LOG_LEVEL,
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console_minimal",
                "level": CONSOLE_LOG_LEVEL,
            },
        },
        "loggers": {
            "requests": {
                "level": FILE_LOG_LEVEL,
                "handlers": ["api_file"],
                "propagate": False,
            },
            "urllib3": {
                "level": FILE_LOG_LEVEL,
                "handlers": ["api_file"],
                "propagate": False,
            },
        },
        "root": {
            "level": ROOT_LOG_LEVEL,
            "handlers": ["app_file", "console"],
        },
    }
    logging.config.dictConfig(config)
