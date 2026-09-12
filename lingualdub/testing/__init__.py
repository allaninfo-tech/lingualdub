# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Testing utilities for LingualDub.

Provides isolated framework instances and lifecycle capture helpers
for deterministic lifecycle tests (LCY-004).
"""

from lingualdub.testing.lifecycle import (
    LifecycleCapture,
    TestFramework,
    assert_lifecycle_sequence,
)

__all__ = [
    "TestFramework",
    "LifecycleCapture",
    "assert_lifecycle_sequence",
]
