# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Testing utilities for LingualDub.

Provides isolated framework instances, lifecycle capture, DI fakes, builders,
matchers, pipeline harness, and fake clock (REL-005 + LCY-004 + EXE-007).
"""

from lingualdub.testing.builders import (
    LanguageBuilder,
    ResourceBuilder,
    ResultBuilder,
    SegmentBuilder,
)
from lingualdub.testing.clock import FakeClock
from lingualdub.testing.di import (
    FakeLanguage,
    FakeRegistry,
    FakeResourceManager,
    TestContainer,
    assert_resolved_as,
)
from lingualdub.testing.fakes import (
    FakeAlignment,
    FakeASR,
    FakeEvaluator,
    FakeTranslation,
    FakeTTS,
)
from lingualdub.testing.lifecycle import (
    LifecycleCapture,
    TestFramework,
    assert_lifecycle_sequence,
)
from lingualdub.testing.matchers import (
    assert_resource_valid,
    assert_result_complete,
    assert_result_degraded,
    assert_result_failed,
    assert_result_has_language,
    assert_result_has_segment,
    assert_result_partial,
)
from lingualdub.testing.pipeline import PipelineTestHarness

__all__ = [
    "TestFramework",
    "LifecycleCapture",
    "assert_lifecycle_sequence",
    "TestContainer",
    "FakeRegistry",
    "FakeResourceManager",
    "FakeLanguage",
    "assert_resolved_as",
    # Builders
    "LanguageBuilder",
    "ResourceBuilder",
    "SegmentBuilder",
    "ResultBuilder",
    # Fakes
    "FakeASR",
    "FakeTranslation",
    "FakeTTS",
    "FakeAlignment",
    "FakeEvaluator",
    # Matchers
    "assert_result_complete",
    "assert_result_failed",
    "assert_result_partial",
    "assert_result_degraded",
    "assert_result_has_segment",
    "assert_result_has_language",
    "assert_resource_valid",
    # Harness / Clock
    "PipelineTestHarness",
    "FakeClock",
]
