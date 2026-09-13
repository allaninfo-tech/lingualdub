# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Distributed tracing — PRO-003.

Creates a span per pipeline execution and child spans per stage. Trace/span
IDs are propagated into ``Result.provenance``.

Backends:
- NoOpTracingBackend (default)
- OpenTelemetryTracingBackend (optional, requires opentelemetry-api)
- CaptureTracingBackend (for tests)
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

__all__ = [
    "TracingBackend",
    "NoOpTracingBackend",
    "OpenTelemetryTracingBackend",
    "CaptureTracingBackend",
    "get_tracing_backend",
    "set_tracing_backend",
]


@runtime_checkable
class TracingBackend(Protocol):
    """Protocol for tracing backends."""

    def start_span(
        self, name: str, parent_id: str | None = None, attributes: dict[str, Any] | None = None
    ) -> str:
        """Start a span and return its span_id."""

    def end_span(
        self, span_id: str, status: str = "ok", attributes: dict[str, Any] | None = None
    ) -> None: ...

    def get_trace_id(self) -> str | None: ...

    def get_current_span_id(self) -> str | None: ...


class NoOpTracingBackend:
    """Default — no-op, zero overhead."""

    def start_span(
        self, name: str, parent_id: str | None = None, attributes: dict[str, Any] | None = None
    ) -> str:
        return ""

    def end_span(
        self, span_id: str, status: str = "ok", attributes: dict[str, Any] | None = None
    ) -> None:
        pass

    def get_trace_id(self) -> str | None:
        return None

    def get_current_span_id(self) -> str | None:
        return None


class CaptureTracingBackend(NoOpTracingBackend):
    """Capture backend for tests — records hierarchy."""

    def __init__(self) -> None:
        self.spans: list[dict[str, Any]] = []
        self._active: dict[str, dict[str, Any]] = {}
        self._trace_id = uuid.uuid4().hex

    def start_span(
        self, name: str, parent_id: str | None = None, attributes: dict[str, Any] | None = None
    ) -> str:
        span_id = uuid.uuid4().hex[:16]
        rec = {
            "name": name,
            "span_id": span_id,
            "parent_id": parent_id,
            "attributes": dict(attributes or {}),
            "start": time.time(),
            "end": None,
            "status": None,
        }
        self.spans.append(rec)
        self._active[span_id] = rec
        return span_id

    def end_span(
        self, span_id: str, status: str = "ok", attributes: dict[str, Any] | None = None
    ) -> None:
        rec = self._active.get(span_id)
        if rec is not None:
            rec["end"] = time.time()
            rec["status"] = status
            if attributes:
                rec["attributes"].update(attributes)
            self._active.pop(span_id, None)

    def get_trace_id(self) -> str | None:
        return self._trace_id

    def get_current_span_id(self) -> str | None:
        if self._active:
            return list(self._active.keys())[-1]
        return None

    def clear(self) -> None:
        self.spans.clear()
        self._active.clear()
        self._trace_id = uuid.uuid4().hex


class OpenTelemetryTracingBackend:
    """OpenTelemetry backend — optional.

    Requires ``opentelemetry-api``. Falls back to NoOp if not installed.
    Creates spans via ``opentelemetry.trace``.
    """

    def __init__(self) -> None:
        self._enabled = False
        self._tracer = None
        try:
            from opentelemetry import trace  # type: ignore

            self._trace = trace  # type: ignore[assignment]
            self._tracer = trace.get_tracer("lingualdub")  # type: ignore[assignment]
            self._enabled = True
        except ImportError:
            logger.debug("opentelemetry-api not installed, tracing disabled", exc_info=True)
            self._trace = None  # type: ignore[assignment]
        self._spans: dict[str, Any] = {}
        self._trace_id: str | None = None

    def start_span(
        self, name: str, parent_id: str | None = None, attributes: dict[str, Any] | None = None
    ) -> str:
        if not self._enabled or self._tracer is None:
            return uuid.uuid4().hex[:16]
        try:
            # Simplified: create span without explicit parent handling
            span = self._tracer.start_span(name, attributes=attributes)  # type: ignore[attr-defined]
            span_id = uuid.uuid4().hex[:16]
            # Store span object for end
            self._spans[span_id] = span
            # Try to get trace id from span context
            try:
                ctx = span.get_span_context()  # type: ignore[attr-defined]
                self._trace_id = format(ctx.trace_id, "032x")  # type: ignore[attr-defined]
            except Exception:
                self._trace_id = uuid.uuid4().hex
            return span_id
        except Exception as exc:
            logger.debug("OpenTelemetry start_span failed: %s", exc, exc_info=True)
            return uuid.uuid4().hex[:16]

    def end_span(
        self, span_id: str, status: str = "ok", attributes: dict[str, Any] | None = None
    ) -> None:
        if not self._enabled:
            return
        span = self._spans.pop(span_id, None)
        if span is not None:
            try:
                if attributes:
                    for k, v in attributes.items():
                        span.set_attribute(k, v)  # type: ignore[attr-defined]
                span.end()  # type: ignore[attr-defined]
            except Exception:
                logger.debug("OpenTelemetry end_span failed", exc_info=True)

    def get_trace_id(self) -> str | None:
        return self._trace_id

    def get_current_span_id(self) -> str | None:
        if self._spans:
            return list(self._spans.keys())[-1]
        return None


# Global backend

_global_backend: TracingBackend = NoOpTracingBackend()


def get_tracing_backend() -> TracingBackend:
    return _global_backend


def set_tracing_backend(backend: TracingBackend) -> None:
    global _global_backend
    _global_backend = backend
