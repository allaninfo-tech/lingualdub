# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""Tests for LCY-004 lifecycle testing utilities."""

from __future__ import annotations

import threading

import pytest

from lingualdub.lifecycle import LifecycleState
from lingualdub.testing.lifecycle import LifecycleCapture, TestFramework, assert_lifecycle_sequence


def test_test_framework_provides_isolated_initialized_instance():
    with TestFramework() as fw:
        assert fw.lifecycle is not None
        assert fw.state == LifecycleState.UNINITIALIZED
        assert fw.capture is not None
        # Fresh instance should have empty hook registries
        assert fw.lifecycle.list_startup_hooks() == []
        assert fw.lifecycle.list_shutdown_hooks() == []
    # After exit, torn down to STOPPED
    assert fw.lifecycle.state == LifecycleState.STOPPED


def test_lifecycle_capture_records_all_transitions():
    with TestFramework() as fw:
        fw.lifecycle.transition(LifecycleState.CONFIGURING)
        fw.lifecycle.transition(LifecycleState.CONFIGURED)
        fw.lifecycle.transition(LifecycleState.INITIALIZING)
        assert fw.capture.sequence == [
            LifecycleState.UNINITIALIZED,
            LifecycleState.CONFIGURING,
            LifecycleState.CONFIGURED,
            LifecycleState.INITIALIZING,
        ]
        assert_lifecycle_sequence(
            fw.capture,
            [
                LifecycleState.UNINITIALIZED,
                LifecycleState.CONFIGURING,
                LifecycleState.CONFIGURED,
                LifecycleState.INITIALIZING,
            ],
        )
        # Raw history also works
        assert_lifecycle_sequence(
            fw.lifecycle,
            [
                LifecycleState.UNINITIALIZED,
                LifecycleState.CONFIGURING,
                LifecycleState.CONFIGURED,
                LifecycleState.INITIALIZING,
            ],
        )


def test_lifecycle_capture_detached_records_shutdown():
    fw = TestFramework()
    fw2 = fw  # alias
    with fw:
        fw.lifecycle.transition(LifecycleState.CONFIGURING)
        fw.lifecycle.transition(LifecycleState.CONFIGURED)
        fw.lifecycle.transition(LifecycleState.INITIALIZING)
        fw.lifecycle.transition(LifecycleState.READY)
    # After exit, shutdown should have added SHUTTING_DOWN and STOPPED
    assert LifecycleState.SHUTTING_DOWN in fw.capture.sequence
    assert LifecycleState.STOPPED in fw.capture.sequence
    assert fw2.capture.sequence[-1] == LifecycleState.STOPPED


def test_two_concurrent_test_framework_contexts_do_not_share_state():
    with TestFramework() as fw1, TestFramework() as fw2:
        assert fw1.lifecycle is not fw2.lifecycle
        assert fw1.capture is not fw2.capture
        fw1.lifecycle.transition(LifecycleState.CONFIGURING)
        fw2.lifecycle.transition(LifecycleState.CONFIGURING)
        fw2.lifecycle.transition(LifecycleState.CONFIGURED)
        assert len(fw1.history) == 2
        assert len(fw2.history) == 3
        assert fw1.capture.sequence != fw2.capture.sequence
        # Hook isolation
        fw1.lifecycle.register_startup_hook("a", lambda: None)
        assert fw2.lifecycle.list_startup_hooks() == []
        assert fw1.lifecycle.list_startup_hooks() == ["a"]


def test_concurrent_test_framework_thread_isolation():
    results: dict[str, list[LifecycleState]] = {}

    def run_in_thread(name: str, barrier: threading.Barrier):
        with TestFramework() as fw:
            barrier.wait()
            fw.lifecycle.transition(LifecycleState.CONFIGURING)
            fw.lifecycle.transition(LifecycleState.CONFIGURED)
            results[name] = list(fw.capture.sequence)

    barrier = threading.Barrier(2)
    t1 = threading.Thread(target=run_in_thread, args=("t1", barrier))
    t2 = threading.Thread(target=run_in_thread, args=("t2", barrier))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results["t1"] == [
        LifecycleState.UNINITIALIZED,
        LifecycleState.CONFIGURING,
        LifecycleState.CONFIGURED,
    ]
    assert results["t2"] == [
        LifecycleState.UNINITIALIZED,
        LifecycleState.CONFIGURING,
        LifecycleState.CONFIGURED,
    ]
    # Ensure they were independent objects (different ids)
    # We already checked via barrier sync and separate histories


def test_assert_lifecycle_sequence_mismatch_raises():
    from lingualdub.lifecycle import FrameworkLifecycle

    lc = FrameworkLifecycle()
    cap = LifecycleCapture(lc)
    lc.transition(LifecycleState.CONFIGURING)
    with pytest.raises(AssertionError) as exc:
        assert_lifecycle_sequence(cap, [LifecycleState.UNINITIALIZED, LifecycleState.READY])
    assert "Expected" in str(exc.value)
    assert "Actual" in str(exc.value)


def test_lifecycle_capture_clear_and_detach():
    from lingualdub.lifecycle import FrameworkLifecycle

    lc = FrameworkLifecycle()
    cap = LifecycleCapture(lc)
    lc.transition(LifecycleState.CONFIGURING)
    assert len(cap.sequence) == 2
    cap.clear()
    # clear should reset to current history
    assert cap.sequence == [LifecycleState.UNINITIALIZED, LifecycleState.CONFIGURING]
    cap.detach()
    lc.transition(LifecycleState.CONFIGURED)
    # After detach, capture should not have updated (still old)
    assert cap.sequence == [LifecycleState.UNINITIALIZED, LifecycleState.CONFIGURING]
    # But lifecycle history did update
    assert lc.history == [
        LifecycleState.UNINITIALIZED,
        LifecycleState.CONFIGURING,
        LifecycleState.CONFIGURED,
    ]


def test_test_framework_shortcut_properties():
    with TestFramework() as fw:
        assert fw.state == LifecycleState.UNINITIALIZED
        assert fw.history == [LifecycleState.UNINITIALIZED]
        fw.lifecycle.transition(LifecycleState.CONFIGURING)
        assert fw.state == LifecycleState.CONFIGURING
        assert fw.history[-1] == LifecycleState.CONFIGURING
