# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Testing utilities for LingualDub.

Provides isolated framework instances and lifecycle capture helpers
for deterministic lifecycle tests (LCY-004), and DI fakes for EXE-007.
"""

from lingualdub.testing.di import (
    FakeLanguage,
    FakeRegistry,
    FakeResourceManager,
    TestContainer,
    assert_resolved_as,
)
from lingualdub.testing.lifecycle import (
    LifecycleCapture,
    TestFramework,
    assert_lifecycle_sequence,
)

__all__ = [
    "TestFramework",
    "LifecycleCapture",
    "assert_lifecycle_sequence",
    "TestContainer",
    "FakeRegistry",
    "FakeResourceManager",
    "FakeLanguage",
    "assert_resolved_as",
]
