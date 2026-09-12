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

from collections import deque
from collections.abc import Callable
from enum import Enum

from lingualdub.exceptions import InitializationError, LifecycleError


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
        order = self._resolve_startup_order()
        for name in order:
            hook, _ = self._startup_hooks[name]
            try:
                hook()
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
