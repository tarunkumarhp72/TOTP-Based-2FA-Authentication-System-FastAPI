# app/core/logging.py
import logging
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import json

from app.core.config import settings

# Context variable to carry request_id across async boundaries
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON for machine parsing."""

    MASKED_FIELDS = {"password", "token", "secret", "totp_secret", "backup_codes"}

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(""),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach extra fields from LogRecord, masking sensitive ones
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in (
                "message", "msg", "args", "exc_info", "exc_text",
                "stack_info", "levelname", "name", "pathname", "filename",
                "module", "funcName", "lineno", "created", "msecs",
                "relativeCreated", "thread", "threadName", "processName",
                "process", "taskName",
            ):
                continue
            log_entry[key] = "***REDACTED***" if key in self.MASKED_FIELDS else value

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def _get_log_file_path() -> Path:
    """Generate log file path with structure: logs/year/month/YYYY-MM-DD.log"""
    now = datetime.now(timezone.utc)
    log_dir = Path("logs") / str(now.year) / f"{now.month:02d}"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"{now.strftime('%Y-%m-%d')}.log"


def setup_logging() -> None:
    """Configure application-wide structured logging."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove default handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)

    # File handler with year/month/date structure
    log_file = _get_log_file_path()
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DB_ECHO else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Call after setup_logging()."""
    return logging.getLogger(name)


def generate_request_id() -> str:
    return str(uuid.uuid4())