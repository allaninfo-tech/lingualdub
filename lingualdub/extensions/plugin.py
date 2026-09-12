# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Plugin registration and lifecycle — EXT-002 .. EXT-004.

Provides :class:`Plugin` and :class:`PluginRegistry` with:
* explicit registration / discovery via ``entry_points``
* dependency-ordered startup / reverse shutdown
* ``fail_fast`` isolation and state machine
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lingualdub.exceptions import InitializationError, RegistrationConflictError
from lingualdub.lifecycle import FrameworkLifecycle, LifecycleState

logger = logging.getLogger(__name__)

__all__ = ["Plugin", "PluginRegistry", "PluginState"]


class PluginState(str, Enum):
    """Lifecycle state of a plugin instance."""

    REGISTERED = "registered"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class Plugin:
    """Base class for LingualDub plugins.

    Subclass and override :meth:`on_startup` / :meth:`on_shutdown` to
    participate in framework lifecycle.

    Attributes:
        name: Unique plugin name (e.g. ``"my_plugin"``).
        version: Version string (``MAJOR.MINOR.PATCH``).
        description: Human-readable description.
        author: Author name or org.
        dependencies: List of plugin names this plugin depends on (alias for
            ``depends_on`` — kept for backwards compatibility with EXT-002 spec).
        depends_on: List of plugin names that must initialize before this one.
        state: Current :class:`PluginState` (read-only via property, but
            dataclass field for persistence).
    """

    name: str
    version: str = "0.0.0"
    description: str = ""
    author: str = ""
    dependencies: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    state: PluginState = field(default=PluginState.REGISTERED, init=False)

    # Stability marker for extension contracts
    __stability__: str = "stable"

    def __post_init__(self) -> None:
        from lingualdub.utils.validation import require_non_empty_string, validate_version_string

        require_non_empty_string(self.name, "name")
        validate_version_string(self.version)
        # Normalise dependencies / depends_on: de-duplicate, keep order
        # depends_on is canonical; dependencies is alias
        # Merge both into depends_on
        merged: list[str] = []
        for dep in list(self.dependencies) + list(self.depends_on):
            if dep and dep not in merged:
                merged.append(dep)
        # Validate each is non-empty string
        for i, dep in enumerate(merged):
            require_non_empty_string(dep, f"depends_on[{i}]")
        object.__setattr__(self, "depends_on", merged)
        object.__setattr__(self, "dependencies", list(merged))
        # Ensure state is REGISTERED initially
        object.__setattr__(self, "state", PluginState.REGISTERED)

    # ------------------------------------------------------------------
    # Lifecycle hooks — EXT-003 (override in subclasses)
    # ------------------------------------------------------------------

    def on_startup(self, container: Any | None = None) -> None:  # type: ignore[no-untyped-def]
        """Called during :meth:`PluginRegistry.initialize_all`.

        Args:
            container: :class:`DependencyContainer` for registering services.
        """
        # Default no-op; subclasses override.

    def on_shutdown(self) -> None:
        """Called during :meth:`PluginRegistry.shutdown_all` (reverse order)."""
        # Default no-op.

    def __repr__(self) -> str:
        return f"Plugin(name={self.name!r}, version={self.version!r}, state={self.state.value!r})"


class PluginRegistry:
    """Registry for :class:`Plugin` instances.

    Args:
        lifecycle: Optional :class:`FrameworkLifecycle` for stage enforcement.
            If provided, :meth:`register_plugin` only succeeds when
            ``lifecycle.state == CONFIGURING``.
        fail_fast: When ``True`` (default), the first plugin startup failure
            raises :class:`InitializationError` immediately. When ``False``,
            failures are logged, the plugin is marked ``FAILED``, and
            initialization continues for non-dependent plugins.
    """

    def __init__(
        self,
        lifecycle: FrameworkLifecycle | None = None,
        *,
        fail_fast: bool = True,
    ) -> None:
        self._lifecycle: FrameworkLifecycle | None = lifecycle
        self.fail_fast: bool = fail_fast
        self._plugins: dict[str, Plugin] = {}
        self._startup_order: list[str] = []  # order of successful initializations

    # ------------------------------------------------------------------
    # Registration — EXT-002
    # ------------------------------------------------------------------

    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin.

        Args:
            plugin: Plugin instance to register.

        Raises:
            RegistrationConflictError: If a plugin with the same name already exists.
            LifecycleError: If ``lifecycle`` is provided and current state is not
                ``CONFIGURING``.
        """
        from lingualdub.exceptions import LifecycleError

        if not isinstance(plugin, Plugin):
            raise TypeError(
                f"plugin must be a Plugin instance, got {type(plugin).__name__}: {plugin!r}."
            )

        # Lifecycle stage enforcement
        if self._lifecycle is not None and self._lifecycle.state != LifecycleState.CONFIGURING:
            raise LifecycleError(
                f"Plugin registration is only allowed during CONFIGURING stage, current state is {self._lifecycle.state.value!r}.",
                code="PLUGIN_LIFECYCLE_001",
                context={"plugin": plugin.name, "state": self._lifecycle.state.value},
            )

        if plugin.name in self._plugins:
            raise RegistrationConflictError(
                f"Plugin {plugin.name!r} is already registered.",
                kind="plugin",
                key=plugin.name,
                code="PLUGIN_CONFLICT_001",
                context={"plugin": plugin.name},
            )
        # Mark as REGISTERED (in case it was previously FAILED elsewhere)
        plugin.state = PluginState.REGISTERED  # type: ignore[union-attr]
        self._plugins[plugin.name] = plugin

    def get_plugin(self, name: str) -> Plugin:
        """Return plugin by name.

        Raises:
            KeyError: If not found.
        """
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise KeyError(f"Plugin {name!r} not found.") from exc

    def list_plugins(self) -> list[Plugin]:
        """Return plugins in registration order."""
        return list(self._plugins.values())

    def list_failed_plugins(self) -> list[Plugin]:
        """Return plugins whose state is ``FAILED``."""
        return [p for p in self._plugins.values() if p.state == PluginState.FAILED]

    def is_registered(self, name: str) -> bool:
        """Return ``True`` if a plugin with ``name`` is registered."""
        return name in self._plugins

    def clear(self) -> None:
        """Remove all plugins (testing utility)."""
        self._plugins.clear()
        self._startup_order.clear()

    # ------------------------------------------------------------------
    # Auto-discovery via entry_points — EXT-002
    # ------------------------------------------------------------------

    def discover(self, group: str = "lingualdub.plugins") -> list[Plugin]:
        """Discover and register plugins via ``entry_points``.

        Scans ``importlib.metadata.entry_points(group=...)`` and attempts to
        load each entry point.  Each entry point must resolve to a :class:`Plugin`
        subclass or instance.  Already-registered names are skipped with a warning.

        Returns:
            List of newly registered plugins.

        The method respects lifecycle stage enforcement via :meth:`register_plugin`.
        """
        try:
            from importlib.metadata import entry_points
        except ImportError:  # pragma: no cover — Python <3.8 fallback
            from importlib_metadata import entry_points  # type: ignore[no-redef]

        discovered: list[Plugin] = []
        try:
            # Python 3.10+ has group param; older uses mapping
            try:
                eps = entry_points(group=group)  # type: ignore[call-arg]
            except TypeError:
                eps_map = entry_points()  # type: ignore[no-untyped-call]
                eps = eps_map.get(group, [])  # type: ignore[attr-defined,arg-type]
        except Exception as exc:
            logger.debug("Failed to query entry_points for group %r: %s", group, exc, exc_info=True)
            return discovered

        for ep in eps:
            try:
                obj = ep.load()
                # obj may be a class or instance
                if isinstance(obj, type) and issubclass(obj, Plugin):
                    plugin = obj()  # type: ignore[call-arg]
                elif isinstance(obj, Plugin):
                    plugin = obj
                else:
                    # Try to instantiate if it's a Plugin subclass without args
                    try:
                        plugin = obj() if isinstance(obj, type) else obj  # type: ignore[call-arg]
                    except Exception:
                        logger.warning(
                            "Entry point %r for group %r is not a Plugin: %r", ep.name, group, obj
                        )
                        continue
                    if not isinstance(plugin, Plugin):
                        logger.warning(
                            "Entry point %r did not resolve to Plugin: %r", ep.name, plugin
                        )
                        continue
                try:
                    self.register_plugin(plugin)
                except RegistrationConflictError:
                    logger.warning(
                        "Plugin %r from entry point %r already registered; skipping.",
                        plugin.name,
                        ep.name,
                    )
                    continue
                except Exception as exc:
                    logger.warning(
                        "Failed to register plugin from entry point %r: %s",
                        ep.name,
                        exc,
                        exc_info=True,
                    )
                    continue
                discovered.append(plugin)
            except Exception as exc:
                logger.warning(
                    "Failed to load entry point %r for group %r: %s",
                    getattr(ep, "name", str(ep)),
                    group,
                    exc,
                    exc_info=True,
                )
        return discovered

    # Alias for spec compatibility
    auto_discover = discover
    discover_plugins = discover

    # ------------------------------------------------------------------
    # Lifecycle — EXT-003 / EXT-004
    # ------------------------------------------------------------------

    def _resolve_startup_order(self) -> list[str]:
        """Topologically sort plugins by ``depends_on``.

        Returns:
            Ordered list of plugin names.

        Raises:
            InitializationError: If a dependency is missing.
            ValueError: If a cycle is detected (wrapped as InitializationError by caller).
        """
        if not self._plugins:
            return []

        # Build graph
        in_degree: dict[str, int] = {name: 0 for name in self._plugins}
        adjacency: dict[str, list[str]] = {name: [] for name in self._plugins}

        for name, plugin in self._plugins.items():
            for dep in plugin.depends_on:
                if dep not in self._plugins:
                    raise InitializationError(
                        f"Plugin {name!r} depends on unknown plugin {dep!r}.",
                        component=name,
                        code="PLUGIN_DEP_001",
                        context={"plugin": name, "depends_on": plugin.depends_on, "unknown": dep},
                    )
                adjacency[dep].append(name)
                in_degree[name] += 1

        # Kahn with deterministic registration order
        reg_order = list(self._plugins.keys())
        reg_index = {n: i for i, n in enumerate(reg_order)}
        available = [n for n, deg in in_degree.items() if deg == 0]
        available.sort(key=lambda n: reg_index[n])
        queue: deque[str] = deque(available)
        order: list[str] = []
        while queue:
            cur = queue.popleft()
            order.append(cur)
            newly: list[str] = []
            for nb in adjacency[cur]:
                in_degree[nb] -= 1
                if in_degree[nb] == 0:
                    newly.append(nb)
            if newly:
                newly.sort(key=lambda n: reg_index[n])
                queue.extend(newly)

        if len(order) != len(self._plugins):
            # Cycle — find via DFS for message
            cycle = self._find_plugin_cycle()
            cycle_str = " → ".join(repr(c) for c in cycle) if cycle else "unknown"
            raise InitializationError(
                f"Circular plugin dependency detected: {cycle_str}",
                component="plugin_registry",
                code="PLUGIN_CYCLE_001",
                context={"cycle": cycle},
            )
        return order

    def _find_plugin_cycle(self) -> list[str]:
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> list[str] | None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for dep in self._plugins[node].depends_on:
                if dep not in visited:
                    res = dfs(dep)
                    if res is not None:
                        return res
                elif dep in rec_stack:
                    idx = path.index(dep)
                    return path[idx:] + [dep]
            path.pop()
            rec_stack.remove(node)
            return None

        for n in self._plugins:
            if n not in visited:
                res = dfs(n)
                if res is not None:
                    return res
        return []

    def initialize_all(self, container: Any | None = None) -> None:
        """Initialize all registered plugins in dependency order.

        Calls :meth:`Plugin.on_startup` for each plugin.  On failure,
        behaviour depends on ``fail_fast``:

        * ``True``: raise :class:`InitializationError` immediately (plugin
          marked ``FAILED`` before raising).
        * ``False``: log the error, mark plugin ``FAILED``, and continue for
          non-dependent plugins.  Plugins that depend (directly or transitively)
          on a ``FAILED`` plugin are also marked ``FAILED`` without calling
          their ``on_startup``.

        Args:
            container: Optional :class:`DependencyContainer` passed to each
                plugin's ``on_startup``.

        Raises:
            InitializationError: If any plugin's ``on_startup`` fails and
                ``fail_fast`` is ``True``, or if a dependency is missing / cycle.
        """
        order = self._resolve_startup_order()
        # Track failed plugins for cascade
        failed: set[str] = {
            name for name, p in self._plugins.items() if p.state == PluginState.FAILED
        }

        for name in order:
            plugin = self._plugins[name]
            # Skip if already failed (from previous run)
            if plugin.state == PluginState.FAILED:
                failed.add(name)
                continue
            # If any dependency is failed, mark this as failed too (cascade)
            if any(dep in failed for dep in plugin.depends_on):
                plugin.state = PluginState.FAILED  # type: ignore[union-attr]
                failed.add(name)
                logger.warning(
                    "Skipping plugin %r: depends on failed plugin(s) %r.",
                    name,
                    [d for d in plugin.depends_on if d in failed],
                )
                continue

            plugin.state = PluginState.INITIALIZING  # type: ignore[union-attr]
            try:
                plugin.on_startup(container)
            except InitializationError:
                plugin.state = PluginState.FAILED  # type: ignore[union-attr]
                failed.add(name)
                if self.fail_fast:
                    raise
                logger.warning(
                    "Plugin %r on_startup failed (fail_fast=False); marked FAILED.",
                    name,
                    exc_info=True,
                )
                continue
            except Exception as exc:
                plugin.state = PluginState.FAILED  # type: ignore[union-attr]
                failed.add(name)
                wrapped = InitializationError(
                    f"Plugin {name!r} on_startup failed: {exc}",
                    component=name,
                    code="PLUGIN_INIT_001",
                    context={"plugin": name},
                )
                wrapped.__cause__ = exc
                if self.fail_fast:
                    raise wrapped from exc
                logger.warning(
                    "Plugin %r on_startup failed: %s (fail_fast=False)", name, exc, exc_info=True
                )
                continue
            plugin.state = PluginState.ACTIVE  # type: ignore[union-attr]
            self._startup_order.append(name)

    def shutdown_all(self) -> None:
        """Shutdown all plugins in reverse startup order.

        Calls :meth:`Plugin.on_shutdown` best-effort: failures are logged and
        remaining plugins continue.  Plugins in ``ACTIVE`` or ``FAILED`` state
        transition to ``STOPPED`` after their shutdown hook (or immediately if
        no hook).  Plugins still ``REGISTERED`` (never initialized) are left
        as-is or moved to ``STOPPED``? Here we move all to ``STOPPED`` for
        determinism.

        Startup order is the order in which plugins became ``ACTIVE``; if no
        startup has occurred, uses reverse registration order.
        """
        # Determine order: reverse of startup_order if available, else reverse registration
        order = (
            list(reversed(self._startup_order))
            if self._startup_order
            else list(reversed(list(self._plugins.keys())))
        )
        # Ensure any plugins not in startup_order but registered are also shut down
        # Append missing in reverse registration order
        seen = set(order)
        for name in reversed(list(self._plugins.keys())):
            if name not in seen:
                order.append(name)

        for name in order:
            plugin = self._plugins.get(name)
            if plugin is None:
                continue
            # Only attempt shutdown for plugins that were at least REGISTERED
            # (all are). But skip if already STOPPED
            if plugin.state == PluginState.STOPPED:
                continue
            try:
                plugin.on_shutdown()
            except Exception as exc:  # noqa: BLE001 — best-effort teardown
                logger.warning("Plugin %r on_shutdown failed: %s", name, exc, exc_info=True)
            # Transition to STOPPED regardless
            plugin.state = PluginState.STOPPED  # type: ignore[union-attr]
        # Clear startup order after shutdown
        self._startup_order.clear()

    def __repr__(self) -> str:
        return f"PluginRegistry(plugins={list(self._plugins.keys())}, fail_fast={self.fail_fast})"
