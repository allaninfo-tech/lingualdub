# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""Middleware package — protocol, chain, registry and built-ins."""

from lingualdub.middleware.base import ExecutionContext, MiddlewareChain, MiddlewareProtocol
from lingualdub.middleware.consent_mw import ConsentMiddleware
from lingualdub.middleware.logging_mw import LoggingMiddleware
from lingualdub.middleware.registry import MiddlewareRegistry
from lingualdub.middleware.timing_mw import TimingMiddleware

__all__ = [
    "ExecutionContext",
    "MiddlewareProtocol",
    "MiddlewareChain",
    "MiddlewareRegistry",
    "LoggingMiddleware",
    "TimingMiddleware",
    "ConsentMiddleware",
]
