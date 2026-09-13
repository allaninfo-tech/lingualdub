# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Middleware registry — EXT-007.

Provides :class:`MiddlewareRegistry` for global and per-pipeline middleware
registration, removal and ordered listing, and integration with
:class:`MiddlewareChain`.
"""

from __future__ import annotations

import logging

from lingualdub.exceptions import RegistrationConflictError
from lingualdub.middleware.base import MiddlewareChain, MiddlewareProtocol

logger = logging.getLogger(__name__)

__all__ = ["MiddlewareRegistry"]


def _is_cache_enabled() -> bool:
    try:
        from lingualdub.config import is_cache_enabled

        return bool(is_cache_enabled())
    except Exception:
        return True


class MiddlewareRegistry:
    """Registry for :class:`MiddlewareProtocol` with global and scoped support.

    Example:
        registry = MiddlewareRegistry()
        registry.register(LoggingMiddleware())  # global
        registry.register(MyMiddleware(), scope="dubbing_pipeline")
        chain = registry.build_chain("dubbing_pipeline")
        # chain includes logging + MyMiddleware sorted by priority

    Attributes:
        _global: Dict of global middleware by name.
        _scoped: Dict of pipeline_name -> dict[name -> middleware].
    """

    def __init__(self) -> None:
        self._global: dict[str, MiddlewareProtocol] = {}
        self._scoped: dict[str, dict[str, MiddlewareProtocol]] = {}
        self._build_cache: dict[str | None, MiddlewareChain] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        middleware: MiddlewareProtocol,
        scope: str = "global",
        *,
        override: bool = False,
    ) -> None:
        """Register a middleware.

        Args:
            middleware: Middleware instance (must have ``name`` and ``priority``).
            scope: ``"global"`` for all pipelines, or a pipeline name for
                scoped registration.
            override: If ``True``, replaces an existing middleware with the
                same name in the same scope.

        Raises:
            ValueError: If ``middleware`` lacks ``name`` or ``priority``.
            RegistrationConflictError: If a middleware with same name already
                exists in the same scope and ``override`` is ``False``.
        """
        name = getattr(middleware, "name", None)
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Middleware must have a non-empty string name, got {name!r}.")
        priority = getattr(middleware, "priority", None)
        if not isinstance(priority, int):
            raise ValueError(f"Middleware {name!r} must have integer priority, got {priority!r}.")

        if scope == "global":
            if name in self._global and not override:
                raise RegistrationConflictError(
                    f"Middleware {name!r} already registered globally.",
                    kind="middleware",
                    key=name,
                    code="MIDDLEWARE_CONFLICT_001",
                )
            self._global[name] = middleware
        else:
            # Scoped
            if not isinstance(scope, str) or not scope.strip():
                raise ValueError(f"scope must be a non-empty string, got {scope!r}.")
            bucket = self._scoped.setdefault(scope, {})
            if name in bucket and not override:
                raise RegistrationConflictError(
                    f"Middleware {name!r} already registered for scope {scope!r}.",
                    kind="middleware",
                    key=name,
                    code="MIDDLEWARE_CONFLICT_001",
                )
            bucket[name] = middleware
        # Invalidate build cache (PEV-005)
        self._build_cache.clear()

    def remove(self, middleware_name: str, scope: str | None = None) -> bool:
        """Remove a middleware by name.

        Args:
            middleware_name: Name of middleware to remove.
            scope: If ``None``, removes from global and all scoped buckets;
                   if ``"global"``, removes only from global;
                   if a pipeline name, removes only from that scope.

        Returns:
            ``True`` if any middleware was removed, ``False`` otherwise.
        """
        removed = False
        if scope is None:
            if middleware_name in self._global:
                del self._global[middleware_name]
                removed = True
            for bucket in self._scoped.values():
                if middleware_name in bucket:
                    del bucket[middleware_name]
                    removed = True
        elif scope == "global":
            if middleware_name in self._global:
                del self._global[middleware_name]
                removed = True
        else:
            bucket = self._scoped.get(scope)  # type: ignore[assignment]
            if bucket and middleware_name in bucket:
                del bucket[middleware_name]
                removed = True
                if not bucket:
                    self._scoped.pop(scope, None)
        if removed:
            self._build_cache.clear()
        return removed

    def list_middleware(self, scope: str | None = None) -> list[MiddlewareProtocol]:
        """List middleware in priority order.

        Args:
            scope: ``None`` returns global middleware only (sorted);
                   ``"global"`` same as ``None``;
                   pipeline name returns global + scoped for that pipeline
                   combined and sorted.

        Returns:
            Sorted list of middleware.
        """
        if scope is None or scope == "global":
            mws = list(self._global.values())
            mws.sort(key=lambda m: (getattr(m, "priority", 100), getattr(m, "name", "")))
            return mws

        # Scoped + global combined
        global_mws = list(self._global.values())
        scoped_mws = list(self._scoped.get(scope, {}).values())
        combined = global_mws + scoped_mws
        combined.sort(key=lambda m: (getattr(m, "priority", 100), getattr(m, "name", "")))
        return combined

    def build_chain(self, pipeline_name: str | None = None) -> MiddlewareChain:
        """Build a :class:`MiddlewareChain` for a pipeline.

        Combines global + pipeline-scoped middleware in priority order.
        Cached when ``FrameworkConfig.cache_enabled`` is True (PEV-005).

        Args:
            pipeline_name: Pipeline name or ``None`` for global only.

        Returns:
            New ``MiddlewareChain``.
        """
        if _is_cache_enabled() and pipeline_name in self._build_cache:
            return self._build_cache[pipeline_name]
        if pipeline_name is None:
            mws = self.list_middleware(scope=None)
        else:
            mws = self.list_middleware(scope=pipeline_name)
        chain = MiddlewareChain(mws)
        if _is_cache_enabled():
            self._build_cache[pipeline_name] = chain
        return chain

    # Alias for spec compatibility: spec says MiddlewareChain.build(pipeline_name)
    # but we also provide registry.build_chain. For convenience, alias.
    build = build_chain

    def clear(self) -> None:
        """Remove all middleware (testing utility)."""
        self._global.clear()
        self._scoped.clear()
        self._build_cache.clear()

    def __len__(self) -> int:
        return len(self._global) + sum(len(b) for b in self._scoped.values())

    def __repr__(self) -> str:
        return f"MiddlewareRegistry(global={list(self._global.keys())}, scoped={ {k: list(v.keys()) for k, v in self._scoped.items()} })"
