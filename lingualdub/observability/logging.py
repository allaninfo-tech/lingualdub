# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Structured logging — PRO-001.

Provides JSON/text structured logging with consistent fields and
config-controlled level/format. Sensitive fields are redacted via
``RedactionFilter`` (PRO-005).

Every log record includes:
    timestamp, level, event, run_id, pipeline_name, stage_name, language, duration_ms

Usage:
    from lingualdub.observability.logging import configure_logging, get_logger
    from lingualdub.config import load_config

    cfg = load_config()
    configure_logging(cfg)
    logger = get_logger(__name__)
    logger.info("pipeline.start", extra={"run_id": "...", "pipeline_name": "..."} )

Falls back to standard logging if ``structlog`` is not installed; does not
require external dependency.
"""

from __future__ import annotations

import contextlib
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from lingualdub.observability.redaction import RedactionFilter

# Suppress noisy logging errors during interpreter shutdown (closed stdout)
logging.raiseExceptions = False

__all__ = ["configure_logging", "get_logger", "JSONFormatter", "TextFormatter"]

_DEFAULT_SENSITIVE_FIELDS = [
    "api_key",
    "access_token",
    "speaker_reference",
    "voice_path",
    "consent_record",
    "email",
]


class JSONFormatter(logging.Formatter):
    """JSON structured formatter with required fields (PRO-001)."""

    def format(self, record: logging.LogRecord) -> str:
        # Ensure required fields exist, using defaults if not provided via extra
        data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            "run_id": getattr(record, "run_id", "-"),
            "pipeline_name": getattr(record, "pipeline_name", "-"),
            "stage_name": getattr(record, "stage_name", "-"),
            "language": getattr(record, "language", "-"),
            "duration_ms": getattr(record, "duration_ms", 0),
        }
        # Add any extra fields that are not sensitive and not already in data
        for key, value in record.__dict__.items():
            if key in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "process",
                "processName",
                "message",
            ):
                continue
            if key not in data:
                data[key] = value
        # Ensure exc_info is serialized if present
        if record.exc_info and record.exc_info[0] is not None:
            data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter with same fields."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
        level = record.levelname
        event = record.getMessage()
        run_id = getattr(record, "run_id", "-")
        pipeline_name = getattr(record, "pipeline_name", "-")
        stage_name = getattr(record, "stage_name", "-")
        language = getattr(record, "language", "-")
        duration_ms = getattr(record, "duration_ms", 0)
        base = f"{timestamp} {level} {event} run_id={run_id} pipeline={pipeline_name} stage={stage_name} lang={language} duration_ms={duration_ms}"
        if record.exc_info and record.exc_info[0] is not None:
            base += f" exc={self.formatException(record.exc_info)}"
        return base


def _get_level(level_str: str) -> int:
    return getattr(logging, level_str.upper(), logging.INFO)


_configured = False
_configured_level: str | None = None
_configured_format: str | None = None


def configure_logging(
    config: Any | None = None, level: str | None = None, log_format: str | None = None
) -> None:
    """Configure root logging with structured formatter and redaction.

    Args:
        config: Optional :class:`FrameworkConfig` to read ``log_level``,
            ``log_format``, ``log_redaction_enabled``, ``sensitive_fields``.
        level: Explicit level override (takes precedence over config).
        log_format: Explicit format override (``json`` or ``text``).
    """
    global _configured, _configured_level, _configured_format

    # Resolve level/format from config if not explicitly passed
    cfg_level = level
    cfg_format = log_format
    redact_enabled = True
    sensitive_fields: list[str] | None = None

    if config is not None:
        try:
            cfg_level = cfg_level or getattr(config, "log_level", None)
            cfg_format = cfg_format or getattr(config, "log_format", None)
            redact_enabled = bool(getattr(config, "log_redaction_enabled", True))
            sensitive_fields = getattr(config, "sensitive_fields", None)
        except Exception:
            pass

    cfg_level = (cfg_level or "INFO").upper()
    cfg_format = (cfg_format or "json").lower()

    # Avoid reconfiguring if same settings already applied (but allow level change)
    # We always reconfigure handlers to ensure redaction filter updated
    root = logging.getLogger()
    # Clear existing handlers for clean state (only if we previously configured or level/format differs)
    # But don't clear if user has custom handlers outside our control? For framework, we clear lingualdub handlers only.
    # Simplify: clear all handlers and re-add
    for h in list(root.handlers):
        root.removeHandler(h)
    # Also clear lingualdub loggers' handlers
    for name in list(logging.Logger.manager.loggerDict.keys()):
        if name.startswith("lingualdub"):
            lg = logging.getLogger(name)
            for h in list(lg.handlers):
                lg.removeHandler(h)
            lg.filters.clear()
            lg.propagate = True

    handler = logging.StreamHandler(sys.stdout)
    if cfg_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(TextFormatter())

    # Add redaction filter if enabled
    if redact_enabled:
        filt = RedactionFilter(sensitive_fields=sensitive_fields)
        handler.addFilter(filt)
        root.addFilter(filt)

    root.addHandler(handler)
    root.setLevel(_get_level(cfg_level))
    # Also set lingualdub loggers to same level
    logging.getLogger("lingualdub").setLevel(_get_level(cfg_level))

    _configured = True
    _configured_level = cfg_level
    _configured_format = cfg_format


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the given name (structured).

    Ensures that if logging hasn't been configured yet, a default JSON
    configuration is applied.
    """
    if not _configured:
        with contextlib.suppress(Exception):
            configure_logging()
    return logging.getLogger(name)
