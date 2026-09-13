# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Observability package — PRO-001/002/003/005.

Exports:
- logging: structured logging (PRO-001)
- metrics: pluggable metrics backend (PRO-002)
- tracing: distributed tracing (PRO-003)
- redaction: sensitive field filtering (PRO-005)
"""

from lingualdub.observability.logging import (
    configure_logging,
    get_logger,
)
from lingualdub.observability.metrics import (
    MetricsBackend,
    NoOpMetricsBackend,
    PrometheusMetricsBackend,
)
from lingualdub.observability.redaction import RedactionFilter
from lingualdub.observability.tracing import (
    NoOpTracingBackend,
    OpenTelemetryTracingBackend,
    TracingBackend,
)

__all__ = [
    "configure_logging",
    "get_logger",
    "MetricsBackend",
    "NoOpMetricsBackend",
    "PrometheusMetricsBackend",
    "TracingBackend",
    "NoOpTracingBackend",
    "OpenTelemetryTracingBackend",
    "RedactionFilter",
]
