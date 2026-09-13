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

import atexit
import contextlib
import logging
from collections import deque
from collections.abc import Callable
from enum import Enum

from lingualdub.exceptions import InitializationError, LifecycleError

logger = logging.getLogger(__name__)

try:
    from lingualdub.observability.logging import get_logger as _obs_get_logger

    _struct_logger = _obs_get_logger(__name__)
except Exception:
    _struct_logger = logger  # type: ignore[assignment]


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
    """State-transition validator with queryable current state and startup hooks."""

    def __init__(self) -> None:
        self._state: LifecycleState = LifecycleState.UNINITIALIZED
        self._history: list[LifecycleState] = [self._state]
        # Startup hook registry: name -> (callable, depends_on list)
        self._startup_hooks: dict[str, tuple[Callable[[], None], list[str]]] = {}
        # Preserve registration order for deterministic tie-breaking
        self._startup_hook_order: list[str] = []
        # Shutdown hook registry: name -> callable (LIFO teardown)
        self._shutdown_hooks: dict[str, Callable[[], None]] = {}
        self._shutdown_hook_order: list[str] = []
        # Ensure atexit calls shutdown() for deterministic teardown
        # Register once per instance; suppress duplicate registration on re-init
        try:
            atexit.register(self._handle_atexit)  # type: ignore[arg-type]
        except Exception:
            # atexit registration should never fail framework init
            logger.debug("Failed to register atexit handler for FrameworkLifecycle", exc_info=True)

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
                context={
                    "from": self._state.value,
                    "to": target.value,
                    "history": [s.value for s in self._history],
                },
            )
        self._state = target
        self._history.append(target)
        # Structured log for lifecycle event (PRO-001) — suppress during interpreter shutdown
        try:
            import sys as _sys

            if not _sys.is_finalizing():
                _struct_logger.info(
                    "lifecycle.transition",
                    extra={
                        "run_id": "-",
                        "pipeline_name": "-",
                        "stage_name": target.value,
                        "language": "-",
                        "duration_ms": 0,
                    },
                )
        except Exception:
            pass

    def ensure(self, *allowed: LifecycleState) -> None:
        """Raise LifecycleError if current state not in allowed."""
        if self._state not in allowed:
            raise LifecycleError(
                f"Operation not allowed in state {self._state.value!r}; allowed: {[s.value for s in allowed]}",
                code="LIFECYCLE_002",
                context={"state": self._state.value, "allowed": [s.value for s in allowed]},
            )

    # ------------------------------------------------------------------
    # Startup hooks — LCY-002
    # ------------------------------------------------------------------

    def register_startup_hook(
        self,
        name: str,
        hook: Callable[[], None],
        depends_on: list[str] | None = None,
    ) -> None:
        """
        Register a startup hook invoked during ``INITIALIZING``.

        Hooks are ordered topologically by ``depends_on``. A hook with
        ``depends_on=["a", "b"]`` runs after both ``a`` and ``b``.

        Args:
            name: Unique hook name.
            hook: Callable with no required arguments.
            depends_on: Optional list of hook names that must run before this one.

        Raises:
            LifecycleError: If name is invalid, duplicate, or depends_on is malformed.
            ConfigurationValidationError: If name fails string validation.
        """
        from lingualdub.utils.validation import require_non_empty_string

        require_non_empty_string(name, "name")
        if not callable(hook):
            raise LifecycleError(
                f"Startup hook {name!r} must be callable, got {type(hook).__name__}: {hook!r}.",
                code="LIFECYCLE_003",
                context={"hook": name},
            )
        if name in self._startup_hooks:
            raise LifecycleError(
                f"Startup hook {name!r} is already registered.",
                code="LIFECYCLE_003",
                context={"hook": name},
            )
        # Validate depends_on
        if depends_on is None:
            deps: list[str] = []
        else:
            if not isinstance(depends_on, list):
                raise LifecycleError(
                    f"depends_on for hook {name!r} must be a list of strings or None, got {type(depends_on).__name__}: {depends_on!r}.",
                    code="LIFECYCLE_003",
                    context={"hook": name},
                )
            deps = []
            for i, dep in enumerate(depends_on):
                if not isinstance(dep, str) or not dep.strip():
                    raise LifecycleError(
                        f"depends_on[{i}] for hook {name!r} must be a non-empty string, got {dep!r}.",
                        code="LIFECYCLE_003",
                        context={"hook": name, "depends_on": depends_on},
                    )
                # Deduplicate while preserving order
                if dep not in deps:
                    deps.append(dep)
        self._startup_hooks[name] = (hook, deps)
        self._startup_hook_order.append(name)

    def startup_hook(
        self,
        name: str,
        depends_on: list[str] | None = None,
    ) -> Callable[[Callable[[], None]], Callable[[], None]]:
        """
        Decorator to register a startup hook.

        Example:
            lifecycle = FrameworkLifecycle()
            @lifecycle.startup_hook("init_registry", depends_on=["init_config"])
            def init_registry(): ...

        Args:
            name: Unique hook name.
            depends_on: Optional list of hook names that must run before this one.

        Returns:
            Decorator that registers the function and returns it unchanged.
        """

        def decorator(func: Callable[[], None]) -> Callable[[], None]:
            self.register_startup_hook(name, func, depends_on)
            return func

        return decorator

    def list_startup_hooks(self) -> list[str]:
        """Return hook names in registration order."""
        return list(self._startup_hook_order)

    def clear_startup_hooks(self) -> None:
        """Remove all registered startup hooks (useful for testing)."""
        self._startup_hooks.clear()
        self._startup_hook_order.clear()

    def _resolve_startup_order(self) -> list[str]:
        """
        Topologically sort hooks by dependencies.

        Returns:
            Ordered list of hook names.

        Raises:
            LifecycleError: If a dependency is missing or a cycle is detected.
        """
        if not self._startup_hooks:
            return []

        # Build graph: dependency -> dependents
        # Also compute in-degree
        in_degree: dict[str, int] = {name: 0 for name in self._startup_hooks}
        adjacency: dict[str, list[str]] = {name: [] for name in self._startup_hooks}

        for name, (_, deps) in self._startup_hooks.items():
            for dep in deps:
                if dep not in self._startup_hooks:
                    raise LifecycleError(
                        f"Startup hook {name!r} depends on unknown hook {dep!r}.",
                        code="LIFECYCLE_004",
                        context={"hook": name, "depends_on": deps, "unknown": dep},
                    )
                # dep -> name
                adjacency[dep].append(name)
                in_degree[name] += 1

        # Kahn's algorithm with deterministic tie-breaking by registration order
        # Hooks without dependencies are emitted before dependent hooks that
        # become ready later (FIFO), satisfying LCY-002 requirement:
        # "hooks without dependencies run before dependent hooks" even when
        # registration order is interleaved.
        order: list[str] = []
        # Map name -> registration index for tie-breaking
        reg_index = {name: i for i, name in enumerate(self._startup_hook_order)}

        available = [n for n, deg in in_degree.items() if deg == 0]
        # Sort initial available by registration order for determinism
        available.sort(key=lambda n: reg_index[n])
        queue: deque[str] = deque(available)

        while queue:
            current = queue.popleft()
            order.append(current)
            newly_available: list[str] = []
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    newly_available.append(neighbor)
            # Sort newly available batch by registration order, then FIFO append
            # (do not re-sort entire queue — preserves that independent hooks
            # registered later but initially available run before dependents
            # that just became ready)
            if newly_available:
                newly_available.sort(key=lambda n: reg_index[n])
                queue.extend(newly_available)

        if len(order) != len(self._startup_hooks):
            # Cycle detected — find cycle path via DFS for clear message
            cycle = self._find_cycle()
            cycle_str = " → ".join(repr(c) for c in cycle) if cycle else "unknown"
            raise LifecycleError(
                f"Circular dependency detected: {cycle_str}",
                code="LIFECYCLE_005",
                context={"cycle": cycle, "hooks": list(self._startup_hooks.keys())},
            )
        return order

    def _find_cycle(self) -> list[str]:
        """DFS to find a cycle path for error reporting."""
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> list[str] | None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            _, deps = self._startup_hooks[node]
            for dep in deps:
                # Traverse dependency edge: node depends on dep, so look at dep's dependencies
                # For cycle detection we follow depends_on direction: node -> dep
                if dep not in visited:
                    result = dfs(dep)
                    if result is not None:
                        return result
                elif dep in rec_stack:
                    # Found cycle: extract from dep to current
                    idx = path.index(dep)
                    return path[idx:] + [dep]
            path.pop()
            rec_stack.remove(node)
            return None

        for n in self._startup_hook_order:
            if n not in visited:
                result = dfs(n)
                if result is not None:
                    return result
        return []

    def run_startup_hooks(self) -> None:
        """
        Execute all registered startup hooks in dependency order.

        Hooks with no dependencies run before dependent hooks; otherwise
        topological order is respected. If a hook raises, no further hooks
        run and :class:`InitializationError` is raised wrapping the original.

        Raises:
            LifecycleError: If dependencies are missing or circular.
            InitializationError: If any hook raises.
        """
        with contextlib.suppress(Exception):
            _struct_logger.info(
                "lifecycle.startup",
                extra={
                    "run_id": "-",
                    "pipeline_name": "-",
                    "stage_name": "startup",
                    "language": "-",
                    "duration_ms": 0,
                },
            )
        order = self._resolve_startup_order()
        for name in order:
            hook, _ = self._startup_hooks[name]
            try:
                hook()
                with contextlib.suppress(Exception):
                    _struct_logger.info(
                        "lifecycle.startup.hook",
                        extra={
                            "run_id": "-",
                            "pipeline_name": "-",
                            "stage_name": name,
                            "language": "-",
                            "duration_ms": 0,
                        },
                    )
            except InitializationError:
                # Already correct type — re-raise without wrapping
                raise
            except Exception as exc:
                raise InitializationError(
                    f"Startup hook {name!r} failed: {exc}",
                    component=name,
                    code="INIT_HOOK_001",
                    context={"hook": name, "order": order},
                ) from exc

    # Alias for spec compatibility — roadmap refers to both names in prose
    def execute_startup_hooks(self) -> None:
        """Alias for :meth:`run_startup_hooks`."""
        return self.run_startup_hooks()

    # ------------------------------------------------------------------
    # Shutdown hooks — LCY-003
    # ------------------------------------------------------------------

    def register_shutdown_hook(
        self,
        name: str,
        hook: Callable[[], None],
    ) -> None:
        """
        Register a shutdown hook invoked during ``shutdown()``.

        Shutdown hooks run in reverse registration order (LIFO), which
        corresponds to reverse startup order when shutdown hooks are
        registered alongside their startup counterparts.

        Args:
            name: Unique hook name.
            hook: Callable with no required arguments.

        Raises:
            LifecycleError: If name is invalid, duplicate, or hook not callable.
        """
        from lingualdub.utils.validation import require_non_empty_string

        require_non_empty_string(name, "name")
        if not callable(hook):
            raise LifecycleError(
                f"Shutdown hook {name!r} must be callable, got {type(hook).__name__}: {hook!r}.",
                code="LIFECYCLE_006",
                context={"hook": name},
            )
        if name in self._shutdown_hooks:
            raise LifecycleError(
                f"Shutdown hook {name!r} is already registered.",
                code="LIFECYCLE_006",
                context={"hook": name},
            )
        self._shutdown_hooks[name] = hook
        self._shutdown_hook_order.append(name)

    def shutdown_hook(
        self,
        name: str,
    ) -> Callable[[Callable[[], None]], Callable[[], None]]:
        """
        Decorator to register a shutdown hook.

        Example:
            lifecycle = FrameworkLifecycle()
            @lifecycle.shutdown_hook("cleanup_tmp")
            def cleanup_tmp(): ...

        Args:
            name: Hook name.

        Returns:
            Decorator that registers the function and returns it unchanged.
        """

        def decorator(func: Callable[[], None]) -> Callable[[], None]:
            self.register_shutdown_hook(name, func)
            return func

        return decorator

    def list_shutdown_hooks(self) -> list[str]:
        """Return shutdown hook names in registration order."""
        return list(self._shutdown_hook_order)

    def clear_shutdown_hooks(self) -> None:
        """Remove all registered shutdown hooks (useful for testing)."""
        self._shutdown_hooks.clear()
        self._shutdown_hook_order.clear()

    def run_shutdown_hooks(self) -> None:
        """
        Execute all registered shutdown hooks in reverse registration order.

        Best-effort teardown: if a hook raises, the error is logged at
        WARNING level and remaining hooks continue.

        No exception is raised for hook failures; all hooks are attempted.
        """
        # Reverse registration order = reverse startup order when paired
        for name in reversed(self._shutdown_hook_order):
            hook = self._shutdown_hooks[name]
            try:
                hook()
            except Exception as exc:  # noqa: BLE001 — best-effort teardown must not abort
                logger.warning(
                    "Shutdown hook %r failed: %s",
                    name,
                    exc,
                    exc_info=True,
                )

    def shutdown(self) -> None:
        """
        Deterministically teardown the framework.

        Transitions state through ``SHUTTING_DOWN → STOPPED`` and runs
        shutdown hooks in reverse order. Safe to call from any state
        (including before startup completes) and idempotent — subsequent
        calls after ``STOPPED`` are no-ops.

        Best-effort: shutdown hook failures are logged but do not abort
        teardown; state still proceeds to ``STOPPED``.

        Handles partial initialization: if ``shutdown()`` is called before
        ``INITIALIZING`` completes, any registered shutdown hooks are still
        executed and state moves to ``STOPPED``.
        """
        if self._state == LifecycleState.STOPPED:
            return
        if self._state == LifecycleState.SHUTTING_DOWN:
            # Already shutting down — avoid re-entrance
            return

        # Transition to SHUTTING_DOWN — allow from any non-terminal state
        # for partial-init cleanup. Use can_transition when possible,
        # otherwise force transition.
        if self.can_transition(LifecycleState.SHUTTING_DOWN):
            try:
                self.transition(LifecycleState.SHUTTING_DOWN)
            except LifecycleError:
                # Fallback force
                self._state = LifecycleState.SHUTTING_DOWN
                self._history.append(LifecycleState.SHUTTING_DOWN)
        else:
            # Partial init: e.g., UNINITIALIZED/CONFIGURING/CONFIGURED/INITIALIZING
            # -> force SHUTTING_DOWN for deterministic cleanup
            self._state = LifecycleState.SHUTTING_DOWN
            self._history.append(LifecycleState.SHUTTING_DOWN)

        # Run shutdown hooks best-effort
        try:
            self.run_shutdown_hooks()
        except Exception:
            # run_shutdown_hooks itself should not raise, but be defensive
            logger.warning("Unexpected error during shutdown hooks", exc_info=True)

        # Transition to STOPPED
        if self.can_transition(LifecycleState.STOPPED):
            try:
                self.transition(LifecycleState.STOPPED)
            except LifecycleError:
                self._state = LifecycleState.STOPPED
                self._history.append(LifecycleState.STOPPED)
        else:
            if self._state != LifecycleState.STOPPED:
                self._state = LifecycleState.STOPPED
                self._history.append(LifecycleState.STOPPED)

    def _handle_atexit(self) -> None:
        """atexit handler — ensure shutdown() on interpreter exit."""
        try:
            if self._state != LifecycleState.STOPPED:
                self.shutdown()
        except Exception:
            # atexit must never raise
            logger.debug("Exception in atexit shutdown handler", exc_info=True)

    def __repr__(self) -> str:
        return f"FrameworkLifecycle(state={self._state.value!r})"


# ------------------------------------------------------------------
# Module-level decorator convenience — LCY-002
# ------------------------------------------------------------------


def startup_hook(
    name: str,
    depends_on: list[str] | None = None,
) -> Callable[[Callable[[], None]], Callable[[], None]]:
    """
    Module-level decorator to mark a function as a startup hook.

    This is a convenience for cases where a ``FrameworkLifecycle`` instance
    is not yet available at decoration time. The decorator validates arguments
    and attaches metadata ``_lingualdub_startup_hook`` to the function so it
    can be registered later via ``lifecycle.register_startup_hook``.

    Example:
        from lingualdub.lifecycle import startup_hook

        @startup_hook("my_hook", depends_on=["other"])
        def my_hook(): ...

        # Later:
        lifecycle.register_startup_hook("my_hook", my_hook, depends_on=["other"])
        # Or inspect: my_hook._lingualdub_startup_hook == ("my_hook", ["other"])

    Args:
        name: Hook name.
        depends_on: Optional dependencies.

    Returns:
        Decorator.
    """
    from lingualdub.utils.validation import require_non_empty_string

    require_non_empty_string(name, "name")
    if depends_on is not None:
        if not isinstance(depends_on, list):
            raise LifecycleError(
                f"depends_on for hook {name!r} must be a list of strings or None, got {type(depends_on).__name__}: {depends_on!r}.",
                code="LIFECYCLE_003",
                context={"hook": name},
            )
        for i, dep in enumerate(depends_on):
            if not isinstance(dep, str) or not dep.strip():
                raise LifecycleError(
                    f"depends_on[{i}] for hook {name!r} must be a non-empty string, got {dep!r}.",
                    code="LIFECYCLE_003",
                    context={"hook": name},
                )

    def decorator(func: Callable[[], None]) -> Callable[[], None]:
        # Validate callable
        if not callable(func):
            raise LifecycleError(
                f"Startup hook {name!r} must be callable.",
                code="LIFECYCLE_003",
                context={"hook": name},
            )
        # Attach metadata for later introspection / test verification
        import contextlib

        with contextlib.suppress(Exception):
            object.__setattr__(
                func, "_lingualdub_startup_hook", (name, list(depends_on) if depends_on else [])
            )  # type: ignore[attr-defined]
        return func

    return decorator


def shutdown_hook(
    name: str,
) -> Callable[[Callable[[], None]], Callable[[], None]]:
    """
    Module-level decorator to mark a function as a shutdown hook.

    Mirrors :func:`startup_hook` but for shutdown. Validates arguments and
    attaches metadata ``_lingualdub_shutdown_hook`` so it can be registered
    later via ``lifecycle.register_shutdown_hook``.

    Example:
        from lingualdub.lifecycle import shutdown_hook

        @shutdown_hook("cleanup_tmp")
        def cleanup_tmp(): ...

        # Later:
        lifecycle.register_shutdown_hook("cleanup_tmp", cleanup_tmp)
        # Or inspect: cleanup_tmp._lingualdub_shutdown_hook == "cleanup_tmp"

    Args:
        name: Hook name.

    Returns:
        Decorator.
    """
    from lingualdub.utils.validation import require_non_empty_string

    require_non_empty_string(name, "name")

    def decorator(func: Callable[[], None]) -> Callable[[], None]:
        if not callable(func):
            raise LifecycleError(
                f"Shutdown hook {name!r} must be callable.",
                code="LIFECYCLE_006",
                context={"hook": name},
            )
        import contextlib

        with contextlib.suppress(Exception):
            object.__setattr__(func, "_lingualdub_shutdown_hook", name)  # type: ignore[attr-defined]
        return func

    return decorator
