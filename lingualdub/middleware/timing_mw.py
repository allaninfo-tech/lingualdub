# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Timing middleware — EXT-006.

Measures execution time and adds ``execution_time_ms`` to ``Result.metadata``.
"""

from __future__ import annotations

import time

from lingualdub.core.result import Result
from lingualdub.middleware.base import ExecutionContext

__all__ = ["TimingMiddleware"]


class TimingMiddleware:
    """Adds ``execution_time_ms`` to result metadata.

    Attributes:
        name: Middleware name.
        priority: ``20`` — inner to logging so timing excludes logging overhead? Actually lower outermost, so 20 runs after logging's before and before pipeline, and after is called before logging's after? Either way timing is bounded.
    """

    name: str = "timing"
    priority: int = 20
    __stability__: str = "stable"

    def __init__(self) -> None:
        self._start: float | None = None

    def before(self, context: ExecutionContext) -> None:
        self._start = time.perf_counter()
        # Also stash in context metadata for potential nested access
        context.metadata["timing_start"] = self._start
        return None

    def after(self, context: ExecutionContext, result: Result) -> Result:
        end = time.perf_counter()
        start = self._start if self._start is not None else context.metadata.get("timing_start")
        if start is None:
            start = end
        elapsed_ms = max(1, int((end - start) * 1000))
        # Result is frozen — produce new via replace
        # Ensure metadata is copied
        new_metadata = dict(result.metadata)
        new_metadata["execution_time_ms"] = elapsed_ms
        try:
            return result.replace(metadata=new_metadata)
        except Exception:
            # Fallback: mutate if replace not available (should not happen)
            result.metadata["execution_time_ms"] = elapsed_ms  # type: ignore[index]
            return result

    def on_error(self, context: ExecutionContext, error: Exception) -> None:
        # Even on error we want to ensure timing captured if result is produced via on_error recovery?
        # Clean up start to avoid stale value for next run (middleware instance may be reused)
        self._start = None
        return None

    def __repr__(self) -> str:
        return f"TimingMiddleware(name={self.name!r}, priority={self.priority})"
