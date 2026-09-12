# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Lifecycle testing utilities — LCY-004.

Provides:
- :class:`TestFramework` — isolated FrameworkLifecycle per test
- :class:`LifecycleCapture` — records state transitions in order
- :func:`assert_lifecycle_sequence` — assert helper
"""

# mypy: disable-error-code="no-any-return, exit-return"
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lingualdub.lifecycle import FrameworkLifecycle, LifecycleState

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

__all__ = [
    "TestFramework",
    "LifecycleCapture",
    "assert_lifecycle_sequence",
]


class LifecycleCapture:
    """
    Records all lifecycle state transitions in order.

    Wraps a :class:`FrameworkLifecycle` instance and records every
    state change, including forced transitions performed by ``shutdown()``
    (partial-init handling) and normal ``transition()`` calls.

    Usage:
        lc = FrameworkLifecycle()
        capture = LifecycleCapture(lc)
        lc.transition(LifecycleState.CONFIGURING)
        assert capture.sequence == [LifecycleState.UNINITIALIZED, LifecycleState.CONFIGURING]
    """

    __test__ = False

    def __init__(self, lifecycle: FrameworkLifecycle | None = None) -> None:
        self._lifecycle: FrameworkLifecycle | None = None
        self._sequence: list[LifecycleState] = []
        self._original_transition = None  # type: ignore[assignment]
        self._original_shutdown = None  # type: ignore[assignment]
        self._original_handle_atexit = None  # type: ignore[assignment]
        if lifecycle is not None:
            self.attach(lifecycle)

    def attach(self, lifecycle: FrameworkLifecycle) -> None:
        """
        Attach to a lifecycle instance and start capturing.

        Args:
            lifecycle: FrameworkLifecycle to observe.
        """
        if self._lifecycle is not None:
            # Detach previous if any
            self.detach()
        self._lifecycle = lifecycle
        # Seed with current history (includes UNINITIALIZED)
        self._sequence = list(lifecycle.history)
        # Wrap transition to capture in real time
        self._original_transition = lifecycle.transition  # type: ignore[assignment]

        def _wrapped_transition(target: LifecycleState) -> None:  # type: ignore[no-untyped-def]
            result = self._original_transition(target)  # type: ignore[misc]
            # Sync sequence from lifecycle.history (covers forced direct appends as well)
            # Use history as source of truth after transition
            self._sequence = list(lifecycle.history)
            return result

        lifecycle.transition = _wrapped_transition  # type: ignore[method-assign]

        # Wrap shutdown to capture forced transitions
        self._original_shutdown = lifecycle.shutdown  # type: ignore[assignment]

        def _wrapped_shutdown() -> None:  # type: ignore[no-untyped-def]
            # Capture before length to detect forced appends
            result = self._original_shutdown()  # type: ignore[misc]
            self._sequence = list(lifecycle.history)
            return result

        lifecycle.shutdown = _wrapped_shutdown  # type: ignore[method-assign]

        # Also wrap _handle_atexit to capture
        if hasattr(lifecycle, "_handle_atexit"):
            self._original_handle_atexit = lifecycle._handle_atexit  # type: ignore[assignment]

            def _wrapped_handle() -> None:  # type: ignore[no-untyped-def]
                result = self._original_handle_atexit()  # type: ignore[misc]
                self._sequence = list(lifecycle.history)
                return result

            lifecycle._handle_atexit = _wrapped_handle  # type: ignore[method-assign]

    def detach(self) -> None:
        """Detach from lifecycle and restore original methods."""
        import contextlib

        if self._lifecycle is None:
            return
        if self._original_transition is not None:
            with contextlib.suppress(Exception):
                self._lifecycle.transition = self._original_transition  # type: ignore[method-assign]
        if self._original_shutdown is not None:
            with contextlib.suppress(Exception):
                self._lifecycle.shutdown = self._original_shutdown  # type: ignore[method-assign]
        if self._original_handle_atexit is not None and hasattr(self._lifecycle, "_handle_atexit"):
            with contextlib.suppress(Exception):
                self._lifecycle._handle_atexit = self._original_handle_atexit  # type: ignore[method-assign]
        self._lifecycle = None

    @property
    def sequence(self) -> list[LifecycleState]:
        """
        Captured sequence in order.

        Synced with lifecycle.history to include forced transitions not
        via wrapped methods (e.g., direct _state manipulation).
        """
        if self._lifecycle is not None and len(self._lifecycle.history) != len(self._sequence):
            # Sync any history entries not yet captured (defensive)
            # For cases where history was appended directly without wrapper
            self._sequence = list(self._lifecycle.history)
        return list(self._sequence)

    @property
    def history(self) -> list[LifecycleState]:
        """Alias for :attr:`sequence`."""
        return self.sequence

    def clear(self) -> None:
        """Clear captured sequence (keeps current history as seed)."""
        if self._lifecycle is not None:
            self._sequence = list(self._lifecycle.history)
        else:
            self._sequence.clear()

    def __repr__(self) -> str:
        seq = [s.value for s in self.sequence]
        return f"LifecycleCapture(sequence={seq})"


def assert_lifecycle_sequence(
    capture: LifecycleCapture | FrameworkLifecycle | Sequence[LifecycleState],
    expected: Sequence[LifecycleState],
) -> None:
    """
    Assert that captured lifecycle sequence matches expected.

    Args:
        capture: LifecycleCapture instance, FrameworkLifecycle, or raw sequence.
        expected: Expected sequence of LifecycleState values.

    Raises:
        AssertionError: If sequences differ.
    """
    if isinstance(capture, LifecycleCapture):
        actual = capture.sequence
    elif isinstance(capture, FrameworkLifecycle):
        actual = list(capture.history)
    elif isinstance(capture, (list, tuple)):
        # Raw sequence passed directly
        actual = list(capture)  # type: ignore[arg-type]
    else:
        # Fallback: try to get .sequence or .history
        actual = list(getattr(capture, "sequence", getattr(capture, "history", capture)))  # type: ignore[arg-type]

    # Normalise expected to list
    expected_list = list(expected)

    if actual != expected_list:
        actual_str = " → ".join(s.value if hasattr(s, "value") else str(s) for s in actual)
        expected_str = " → ".join(s.value if hasattr(s, "value") else str(s) for s in expected_list)
        raise AssertionError(
            f"Lifecycle sequence mismatch.\n"
            f"  Expected: {expected_str}\n"
            f"  Actual:   {actual_str}\n"
            f"  Expected list: {expected_list!r}\n"
            f"  Actual list:   {actual!r}"
        )


class TestFramework:
    """
    Isolated framework instance for deterministic lifecycle tests.

    Context manager that provides a fresh :class:`FrameworkLifecycle` per
    test and tears it down after. Each instance is isolated — two concurrent
    ``TestFramework`` contexts do not share state (hooks, history, or
    lifecycle).

    Example:
        from lingualdub.testing.lifecycle import TestFramework, assert_lifecycle_sequence
        from lingualdub.lifecycle import LifecycleState

        def test_example():
            with TestFramework() as fw:
                fw.lifecycle.transition(LifecycleState.CONFIGURING)
                fw.lifecycle.transition(LifecycleState.CONFIGURED)
                assert_lifecycle_sequence(
                    fw.capture,
                    [LifecycleState.UNINITIALIZED, LifecycleState.CONFIGURING, LifecycleState.CONFIGURED],
                )
            # After exit, fw.lifecycle is STOPPED and isolated from next test

        # Minimal:
        with TestFramework() as fw:
            assert fw.lifecycle.state == LifecycleState.UNINITIALIZED
    """

    __test__ = False

    def __init__(self) -> None:
        self.lifecycle = FrameworkLifecycle()
        self.capture = LifecycleCapture(self.lifecycle)
        self._entered = False

    def __enter__(self) -> TestFramework:
        self._entered = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:  # type: ignore[no-untyped-def]
        try:
            # Ensure teardown even if test raised
            if self.lifecycle.state != LifecycleState.STOPPED:
                # Use shutdown for deterministic teardown (handles partial init)
                self.lifecycle.shutdown()
        except Exception:
            logger.debug("Exception during TestFramework teardown", exc_info=True)
        finally:
            # Detach capture to restore original methods for GC
            import contextlib

            with contextlib.suppress(Exception):
                self.capture.detach()
        # Do not suppress test exception
        return False

    @property
    def state(self) -> LifecycleState:
        """Shortcut to ``self.lifecycle.state``."""
        return self.lifecycle.state

    @property
    def history(self) -> list[LifecycleState]:
        """Shortcut to ``self.lifecycle.history``."""
        return self.lifecycle.history

    def __repr__(self) -> str:
        return f"TestFramework(lifecycle={self.lifecycle!r}, capture={self.capture!r})"
