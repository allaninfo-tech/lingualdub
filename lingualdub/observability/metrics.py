# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Metrics backend — PRO-002.

Pluggable metrics interface with NoOp and Prometheus backends.
Framework instruments: pipeline execution count, stage latency histogram,
error count, pool utilization gauge.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

__all__ = [
    "MetricsBackend",
    "NoOpMetricsBackend",
    "PrometheusMetricsBackend",
    "get_metrics_backend",
    "set_metrics_backend",
]

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class MetricsBackend(Protocol):
    """Protocol for metrics backends."""

    def counter(
        self, name: str, value: float = 1, labels: dict[str, str] | None = None
    ) -> None: ...

    def histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None: ...

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None: ...


# ---------------------------------------------------------------------------
# NoOp
# ---------------------------------------------------------------------------


class NoOpMetricsBackend:
    """Default backend — zero overhead, no-ops all calls."""

    def counter(self, name: str, value: float = 1, labels: dict[str, str] | None = None) -> None:
        pass

    def histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        pass

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        pass


# ---------------------------------------------------------------------------
# Capture backend for testing
# ---------------------------------------------------------------------------


class CaptureMetricsBackend(NoOpMetricsBackend):
    """In-memory capture backend for tests — records all calls."""

    def __init__(self) -> None:
        self.counters: list[tuple[str, float, dict]] = []
        self.histograms: list[tuple[str, float, dict]] = []
        self.gauges: list[tuple[str, float, dict]] = []

    def counter(self, name: str, value: float = 1, labels: dict[str, str] | None = None) -> None:
        self.counters.append((name, value, dict(labels or {})))

    def histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        self.histograms.append((name, value, dict(labels or {})))

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        self.gauges.append((name, value, dict(labels or {})))

    def clear(self) -> None:
        self.counters.clear()
        self.histograms.clear()
        self.gauges.clear()


# ---------------------------------------------------------------------------
# Prometheus backend (optional)
# ---------------------------------------------------------------------------


class PrometheusMetricsBackend:
    """Prometheus backend — requires ``prometheus_client``.

    Falls back to NoOp if the package is not installed, but logs a warning.

    Example:
        backend = PrometheusMetricsBackend()
        backend.counter("lingualdub_pipeline_executions_total", 1, {"pipeline": "dubbing"})
    """

    def __init__(self) -> None:
        self._enabled = False
        self._counters: dict[str, Any] = {}
        self._histograms: dict[str, Any] = {}
        self._gauges: dict[str, Any] = {}
        try:
            import prometheus_client  # type: ignore

            self._prom = prometheus_client  # type: ignore[assignment]
            self._enabled = True
        except ImportError:
            logger.debug(
                "prometheus_client not installed, PrometheusMetricsBackend disabled", exc_info=True
            )
            self._prom = None  # type: ignore[assignment]

    def _get_counter(self, name: str, labels: dict[str, str] | None):
        if not self._enabled:
            return None
        key = (name, tuple(sorted((labels or {}).keys())))
        if key not in self._counters:
            try:
                from prometheus_client import Counter  # type: ignore

                labelnames = list(sorted((labels or {}).keys())) if labels else []
                # sanitize name: prometheus expects valid metric name
                c = Counter(name, f"Counter {name}", labelnames=labelnames)
                self._counters[key] = c
            except Exception as exc:
                logger.debug("Failed to create Counter %r: %s", name, exc, exc_info=True)
                return None
        return self._counters[key]

    def _get_histogram(self, name: str, labels: dict[str, str] | None):
        if not self._enabled:
            return None
        key = (name, tuple(sorted((labels or {}).keys())))
        if key not in self._histograms:
            try:
                from prometheus_client import Histogram  # type: ignore

                labelnames = list(sorted((labels or {}).keys())) if labels else []
                h = Histogram(name, f"Histogram {name}", labelnames=labelnames)
                self._histograms[key] = h
            except Exception as exc:
                logger.debug("Failed to create Histogram %r: %s", name, exc, exc_info=True)
                return None
        return self._histograms[key]

    def _get_gauge(self, name: str, labels: dict[str, str] | None):
        if not self._enabled:
            return None
        key = (name, tuple(sorted((labels or {}).keys())))
        if key not in self._gauges:
            try:
                from prometheus_client import Gauge  # type: ignore

                labelnames = list(sorted((labels or {}).keys())) if labels else []
                g = Gauge(name, f"Gauge {name}", labelnames=labelnames)
                self._gauges[key] = g
            except Exception as exc:
                logger.debug("Failed to create Gauge %r: %s", name, exc, exc_info=True)
                return None
        return self._gauges[key]

    def counter(self, name: str, value: float = 1, labels: dict[str, str] | None = None) -> None:
        c = self._get_counter(name, labels)
        if c is None:
            return
        try:
            if labels:
                c.labels(**labels).inc(value)
            else:
                c.inc(value)
        except Exception:
            logger.debug("Prometheus counter inc failed for %r", name, exc_info=True)

    def histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        h = self._get_histogram(name, labels)
        if h is None:
            return
        try:
            if labels:
                h.labels(**labels).observe(value)
            else:
                h.observe(value)
        except Exception:
            logger.debug("Prometheus histogram observe failed for %r", name, exc_info=True)

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        g = self._get_gauge(name, labels)
        if g is None:
            return
        try:
            if labels:
                g.labels(**labels).set(value)
            else:
                g.set(value)
        except Exception:
            logger.debug("Prometheus gauge set failed for %r", name, exc_info=True)

    def generate(self) -> bytes:
        """Generate Prometheus exposition output (for testing)."""
        if not self._enabled or self._prom is None:
            return b""
        try:
            from prometheus_client import generate_latest  # type: ignore

            return generate_latest()  # type: ignore[no-any-return]
        except Exception:
            return b""


# ---------------------------------------------------------------------------
# Global backend management
# ---------------------------------------------------------------------------

_global_backend: MetricsBackend = NoOpMetricsBackend()


def get_metrics_backend() -> MetricsBackend:
    return _global_backend


def set_metrics_backend(backend: MetricsBackend) -> None:
    global _global_backend
    _global_backend = backend


def configure_metrics(config: Any | None = None) -> None:
    """Configure global metrics backend from FrameworkConfig."""
    backend_name = "noop"
    if config is not None:
        try:
            backend_name = getattr(config, "metrics_backend", "noop") or "noop"
        except Exception:
            backend_name = "noop"
    backend_name = str(backend_name).lower()
    if backend_name == "prometheus":
        set_metrics_backend(PrometheusMetricsBackend())
    else:
        set_metrics_backend(NoOpMetricsBackend())
