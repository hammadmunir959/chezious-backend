"""Structured JSON logging for CheziousBot"""

import logging
import json
import sys
import os
from datetime import datetime, timezone
from typing import Any
from logging.handlers import RotatingFileHandler
from contextvars import ContextVar

from app.core.config import settings

# Context variables for request tracking
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
session_id_var: ContextVar[str | None] = ContextVar("session_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)





class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context variables if present
        if request_id := request_id_var.get():
            log_data["request_id"] = request_id

        if session_id := session_id_var.get():
            log_data["session_id"] = session_id

        if user_id := user_id_var.get():
            log_data["user_id"] = user_id

        # Add extra fields from record
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging() -> None:
    """Configure structured logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)

    
    # 1. File Handler (JSON) - Captures EVERYTHING
    # Ensure logs directory exists
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    file_handler = RotatingFileHandler(
        filename=f"{log_dir}/app.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=1,
        encoding="utf-8"
    )
    file_handler.setFormatter(JSONFormatter())
    
    # 2. Console Handler (Standard Text) - For app internal logs
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_formatter = logging.Formatter("%(levelname)s:     %(name)s - %(message)s")
    stream_handler.setFormatter(stream_formatter)
    
    # Configure Root Logger
    root_logger.handlers = [file_handler, stream_handler]

    # 3. Attach File Handler to external loggers
    
    # Group A: Keep Console + Add File (Uvicorn, FastAPI)
    # We do NOT remove existing handlers (so Uvicorn keeps its console output)
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        log = logging.getLogger(logger_name)
        log.addHandler(file_handler)
        log.propagate = False
        
    # Group B: Silence Console + Add File (Database, Migrations)
    # We remove default handlers to stop them from printing to console
    for logger_name in ["sqlalchemy.engine", "alembic"]:
        log = logging.getLogger(logger_name)
        log.handlers = []
        log.addHandler(file_handler)
        log.propagate = False

    # Silence noisy ones if needed
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for setting log context variables.
    """

    def __init__(
        self,
        request_id: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ):
        self.request_id = request_id
        self.session_id = session_id
        self.user_id = user_id
        self._tokens: list = []

    def __enter__(self):
        if self.request_id:
            self._tokens.append(request_id_var.set(self.request_id))
        if self.session_id:
            self._tokens.append(session_id_var.set(self.session_id))
        if self.user_id:
            self._tokens.append(user_id_var.set(self.user_id))
        return self

    def __exit__(self, *args):
        for token in reversed(self._tokens):
            token.var.reset(token)
