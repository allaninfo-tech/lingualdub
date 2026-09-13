# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Fake clock for deterministic time control — REL-005.

    from lingualdub.testing.clock import FakeClock
    import time

    clock = FakeClock(start=0.0)
    assert clock.time() == 0.0
    clock.advance(1.5)
    assert clock.now() == 1.5
    clock.sleep(0.5)
    assert clock.time() == 2.0

Tests can inject ``FakeClock`` where a ``time.time``-like callable is expected,
or monkeypatch ``time.monotonic`` via ``clock.install()`` (best-effort).
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone
from typing import Any

__all__ = ["FakeClock"]


class FakeClock:
    """Deterministic clock starting at ``start``.

    Thread-safe for single-threaded tests; not intended for concurrent use.

    Attributes:
        _time: Current fake time in seconds since epoch (or monotonic origin).

    Example:
        clock = FakeClock(start=1000.0)
        clock.advance(0.5)
        assert clock.time() == 1000.5
    """

    def __init__(self, start: float = 0.0) -> None:
        if not isinstance(start, (int, float)) or isinstance(start, bool):
            raise ValueError(f"start must be a number, got {type(start).__name__}: {start!r}.")
        self._time: float = float(start)
        self._sleeps: list[float] = []  # record of sleep calls for assertions
        self._installed: bool = False
        self._prev_time: Any = None  # type: ignore[assignment]
        self._prev_monotonic: Any = None  # type: ignore[assignment]

    def now(self) -> float:
        """Return current fake time."""
        return self._time

    def time(self) -> float:
        """Alias for :meth:`now` (``time.time`` compatibility)."""
        return self._time

    def monotonic(self) -> float:
        """Fake ``time.monotonic``."""
        return self._time

    def advance(self, seconds: float) -> None:
        """Advance clock by ``seconds`` (may be fractional)."""
        if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
            raise ValueError(
                f"advance seconds must be a number, got {type(seconds).__name__}: {seconds!r}."
            )
        if seconds < 0:
            raise ValueError(f"advance seconds must be >= 0, got {seconds!r}.")
        self._time += float(seconds)

    def sleep(self, seconds: float) -> None:
        """Advance clock as if ``time.sleep(seconds)`` was called (no real delay).

        Records the call in ``sleeps`` for assertion.
        """
        self.advance(seconds)
        self._sleeps.append(float(seconds))

    @property
    def sleeps(self) -> list[float]:
        """Copy of sleep durations recorded via :meth:`sleep`."""
        return list(self._sleeps)

    def datetime_now(self, tz: timezone | None = timezone.utc) -> datetime:
        """Return current time as :class:`datetime`."""
        return datetime.fromtimestamp(self._time, tz=tz)

    def reset(self, start: float = 0.0) -> None:
        """Reset clock to ``start`` and clear sleeps."""
        self._time = float(start)
        self._sleeps.clear()

    def install(self) -> None:
        """Monkeypatch ``time.time`` and ``time.monotonic`` to this clock (best-effort).

        Call :meth:`uninstall` or use ``with clock:`` to restore.
        """
        if self._installed:
            return
        import time as _time

        self._prev_time = _time.time
        self._prev_monotonic = _time.monotonic
        _time.time = self.time  # type: ignore[method-assign]
        _time.monotonic = self.monotonic  # type: ignore[method-assign]
        self._installed = True

    def uninstall(self) -> None:
        """Restore original ``time`` functions."""
        if not self._installed:
            return
        import time as _time

        with contextlib.suppress(Exception):
            _time.time = self._prev_time  # type: ignore[method-assign]
            _time.monotonic = self._prev_monotonic  # type: ignore[method-assign]
        self._installed = False
        self._prev_time = None  # type: ignore[assignment]
        self._prev_monotonic = None  # type: ignore[assignment]

    def __enter__(self) -> FakeClock:
        self.install()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:  # type: ignore[no-untyped-def]
        self.uninstall()

    def __repr__(self) -> str:
        return f"FakeClock(time={self._time!r})"

    # For compatibility with fixtures that expect a callable
    def __call__(self) -> float:
        return self._time
