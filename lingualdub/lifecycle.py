# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Framework lifecycle — deterministic state machine for startup/shutdown.

States:
    UNINITIALIZED → CONFIGURING → CONFIGURED → INITIALIZING → READY → RUNNING → SHUTTING_DOWN → STOPPED

Responsibilities per stage:
    CONFIGURING: validate FrameworkConfig
    CONFIGURED:  config frozen, registry not yet populated
    INITIALIZING: component registration, manifest scan, resource acquisition
    READY:       pipeline assembly allowed
    RUNNING:     pipeline execution allowed
    SHUTTING_DOWN/STOPPED: teardown, no new work
"""

from __future__ import annotations

from enum import Enum

from lingualdub.exceptions import LifecycleError


class LifecycleState(str, Enum):
    """Ordered lifecycle stages."""

    UNINITIALIZED = "uninitialized"
    CONFIGURING = "configuring"
    CONFIGURED = "configured"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"


# Allowed transitions: from -> set(to)
_ALLOWED: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.UNINITIALIZED: {LifecycleState.CONFIGURING},
    LifecycleState.CONFIGURING: {LifecycleState.CONFIGURED},
    LifecycleState.CONFIGURED: {LifecycleState.INITIALIZING},
    LifecycleState.INITIALIZING: {LifecycleState.READY},
    LifecycleState.READY: {LifecycleState.RUNNING, LifecycleState.SHUTTING_DOWN},
    LifecycleState.RUNNING: {LifecycleState.READY, LifecycleState.SHUTTING_DOWN},
    LifecycleState.SHUTTING_DOWN: {LifecycleState.STOPPED},
    LifecycleState.STOPPED: set(),
}


class FrameworkLifecycle:
    """State-transition validator with queryable current state."""

    def __init__(self) -> None:
        self._state: LifecycleState = LifecycleState.UNINITIALIZED
        self._history: list[LifecycleState] = [self._state]

    @property
    def state(self) -> LifecycleState:
        return self._state

    @property
    def history(self) -> list[LifecycleState]:
        return list(self._history)

    def can_transition(self, target: LifecycleState) -> bool:
        return target in _ALLOWED.get(self._state, set())

    def transition(self, target: LifecycleState) -> None:
        if not self.can_transition(target):
            raise LifecycleError(
                f"Illegal lifecycle transition {self._state.value!r} → {target.value!r}",
                code="LIFECYCLE_001",
                context={"from": self._state.value, "to": target.value, "history": [s.value for s in self._history]},
            )
        self._state = target
        self._history.append(target)

    def ensure(self, *allowed: LifecycleState) -> None:
        """Raise LifecycleError if current state not in allowed."""
        if self._state not in allowed:
            raise LifecycleError(
                f"Operation not allowed in state {self._state.value!r}; allowed: {[s.value for s in allowed]}",
                code="LIFECYCLE_002",
                context={"state": self._state.value, "allowed": [s.value for s in allowed]},
            )

    def __repr__(self) -> str:
        return f"FrameworkLifecycle(state={self._state.value!r})"
