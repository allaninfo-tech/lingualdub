# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Logging middleware — EXT-006.

Logs pipeline execution start, end and error with structured data.
"""

from __future__ import annotations

import logging

from lingualdub.core.result import Result
from lingualdub.middleware.base import ExecutionContext

logger = logging.getLogger(__name__)

__all__ = ["LoggingMiddleware"]


class LoggingMiddleware:
    """Logs pipeline execution lifecycle.

    Attributes:
        name: Middleware name.
        priority: Ordering key (lower = outermost). ``10`` for logging.
    """

    name: str = "logging"
    priority: int = 10
    __stability__: str = "stable"

    def before(self, context: ExecutionContext) -> ExecutionContext | None:
        logger.info(
            "Pipeline %r starting (run_id=%r, input=%r)",
            context.pipeline_name,
            context.run_id,
            getattr(context.input, "id", str(type(context.input).__name__)),
        )
        return None

    def after(self, context: ExecutionContext, result: Result) -> Result:
        logger.info(
            "Pipeline %r completed (run_id=%r, status=%r, segments=%r)",
            context.pipeline_name,
            context.run_id,
            getattr(result, "status", "unknown"),
            len(getattr(result, "segments", [])),
        )
        return result

    def on_error(self, context: ExecutionContext, error: Exception) -> None:
        logger.error(
            "Pipeline %r failed (run_id=%r): %s",
            context.pipeline_name,
            context.run_id,
            error,
            exc_info=True,
        )
        return None

    def __repr__(self) -> str:
        return f"LoggingMiddleware(name={self.name!r}, priority={self.priority})"
