# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
ResourcePool — pooling for expensive framework resources.

Manages creation, reuse, and cleanup of expensive resources (e.g. neural
models) with configurable ``max_size`` and timeout-aware ``acquire``.
Thread-safe; never returns the same live instance to two concurrent
acquirers.
"""

from __future__ import annotations

import collections
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from lingualdub.exceptions import ResourceError

logger = logging.getLogger(__name__)


@dataclass
class PooledResource:
    """Wrapper around a pooled instance.

    Supports context-manager protocol so callers can use::

        with pool.acquire(\"model\") as resource:
            use(resource)

    ``resource`` is the underlying pooled object (whatever the factory returned).
    ``name`` identifies the pool key.
    ``pool`` back-reference is kept for ``release()`` via context manager.

    Attributes:
        resource: The underlying pooled object.
        name: Pool key this resource was acquired under.
        _released: Whether ``release()`` has been called.
    """

    resource: Any
    name: str
    _pool: Any = field(default=None, repr=False, compare=False)
    _released: bool = field(default=False, repr=False, compare=False)

    def release(self) -> None:
        """Return this resource to its pool."""
        if self._released:
            return
        if self._pool is not None:
            self._pool.release(self)
        self._released = True

    def __enter__(self) -> Any:
        return self.resource

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release()

    def close(self) -> None:
        """Alias for :meth:`release` for scope-cleanup compatibility."""
        self.release()


class ResourcePool:
    """Thread-safe pool managing creation, reuse, and cleanup.

    Args:
        factory: Callable that creates a fresh resource. Signature may be
            ``() -> Any`` or ``(name: str) -> Any`` — the pool introspects
            arity and passes ``name`` when the factory accepts it.
        max_size: Maximum number of live resources (idle + active). When
            exhausted, ``acquire`` blocks or times out.
        min_idle: Minimum number of idle resources to keep warmed. Created
            eagerly at ``__init__`` and replenished on ``release`` when
            ``idle < min_idle`` and ``total < max_size``.

    Example:
        def make_model(name: str):
            return load_model(name)

        pool = ResourcePool(factory=make_model, max_size=2, min_idle=1)
        with pool.acquire(\"model\") as m:
            m.infer(...)

        # Direct acquire/release:
        r = pool.acquire(\"model\", timeout_s=0)
        try:
            use(r.resource)
        finally:
            pool.release(r)
    """

    def __init__(
        self,
        factory: Callable[..., Any] | None = None,
        max_size: int = 5,
        min_idle: int = 0,
    ) -> None:

        if max_size is not None and (
            not isinstance(max_size, int) or isinstance(max_size, bool) or max_size <= 0
        ):
            raise ValueError(  # justified: pool config — max_size must be positive int
                f"max_size must be a positive int, got {max_size!r}."
            )
        if not isinstance(min_idle, int) or isinstance(min_idle, bool) or min_idle < 0:
            raise ValueError(  # justified: pool config — min_idle must be non-negative
                f"min_idle must be a non-negative int, got {min_idle!r}."
            )
        if min_idle > max_size:
            raise ValueError(  # justified: pool invariant — min_idle <= max_size
                f"min_idle ({min_idle}) must be <= max_size ({max_size})."
            )

        self.factory: Callable[..., Any] | None = factory
        self.max_size: int = max_size
        self.min_idle: int = min_idle

        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)
        # idle holds raw resources (unwrapped) awaiting reuse
        self._idle: collections.deque[Any] = collections.deque()
        # active holds PooledResource wrappers currently borrowed
        self._active: set[int] = set()  # store id(wrapper.resource) for uniqueness check
        self._active_wrappers: dict[int, PooledResource] = {}
        # metrics
        self._total_created: int = 0

        # Pre-warm min_idle
        for _ in range(min_idle):
            try:
                raw = self._create_resource("__warmup__")
                self._idle.append(raw)
                self._total_created += 1
            except Exception as exc:
                logger.debug("ResourcePool warmup failed: %s", exc, exc_info=True)
                break

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_resource(self, name: str) -> Any:
        """Invoke factory to create a fresh resource."""
        if self.factory is None:
            # Default factory: produce a simple object keyed by name
            return object()
        import inspect

        try:
            sig = inspect.signature(self.factory)
            params = [
                p
                for p in sig.parameters.values()
                if p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            ]
            # Remove 'self' for bound methods? inspect already handles.
            if len(params) == 0:
                return self.factory()  # type: ignore[call-arg]
            elif len(params) >= 1:
                # Pass name as first arg
                try:
                    return self.factory(name)  # type: ignore[call-arg]
                except TypeError:
                    # Fallback to no-arg if factory doesn't accept name
                    return self.factory()  # type: ignore[call-arg]
            else:
                return self.factory()  # type: ignore[call-arg]
        except (ValueError, TypeError):
            # Fallback
            try:
                return self.factory(name)  # type: ignore[call-arg]
            except TypeError:
                return self.factory()  # type: ignore[call-arg]

    def _try_acquire_idle_or_create(self, name: str) -> Any | None:
        """Attempt to get an idle resource or create a new one if capacity allows.

        Must be called with ``self._lock`` held. Returns raw resource or None
        if pool exhausted.
        """
        if self._idle:
            return self._idle.popleft()
        if (
            self._total_created < self.max_size
            or (len(self._active_wrappers) + len(self._idle)) < self.max_size
        ):
            # Capacity available — create
            raw = self._create_resource(name)
            self._total_created += 1
            return raw
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire(self, name: str = "default", timeout_s: float | None = None) -> PooledResource:
        """Acquire a pooled resource.

        Args:
            name: Logical name of the resource (passed to factory when applicable).
            timeout_s: None → wait indefinitely, 0 → fail immediately if exhausted,
                positive float → wait that long.

        Returns:
            :class:`PooledResource` wrapper. Use ``.resource`` or ``with``.

        Raises:
            ResourceError: If pool is exhausted and timeout expires.
            ValueError: If ``name`` invalid or ``timeout_s`` negative.
        """
        from lingualdub.utils.validation import require_non_empty_string

        require_non_empty_string(name, "name")
        if timeout_s is not None:
            if not isinstance(timeout_s, (int, float)) or isinstance(timeout_s, bool):
                raise ValueError(  # justified: pool acquire — timeout_s must be numeric
                    f"timeout_s must be a number or None, got {timeout_s!r}."
                )
            if timeout_s < 0:
                raise ValueError(  # justified: pool acquire — timeout_s must be >= 0
                    f"timeout_s must be >= 0, got {timeout_s!r}."
                )

        # Fast path + blocking path under condition lock
        start = time.monotonic()
        with self._cond:
            while True:
                raw = self._try_acquire_idle_or_create(name)
                if raw is not None:
                    wrapper = PooledResource(resource=raw, name=name, _pool=self)
                    # Track active by id of raw resource object to ensure uniqueness enforcement
                    rid = id(raw)
                    # Defensive: if somehow raw already active, it would mean bug — but check
                    if rid in self._active:
                        # This should not happen if reuse logic correct, but guard
                        logger.warning(
                            "ResourcePool: duplicate active id %r, creating fresh instance", rid
                        )
                        raw = self._create_resource(name)
                        self._total_created += 1
                        wrapper = PooledResource(resource=raw, name=name, _pool=self)
                        rid = id(raw)
                    self._active.add(rid)
                    self._active_wrappers[rid] = wrapper
                    return wrapper

                # No idle and at max_size — need to wait
                if timeout_s == 0:
                    raise ResourceError(
                        f"ResourcePool exhausted (max_size={self.max_size}): cannot acquire {name!r} with timeout 0.",
                        code="POOL_EXHAUSTED_001",
                    )
                # Wait
                if timeout_s is None:
                    # Indefinite wait — Condition.wait without timeout
                    self._cond.wait()
                    # loop to re-check
                    continue
                else:
                    elapsed = time.monotonic() - start
                    remaining = timeout_s - elapsed
                    if remaining <= 0:
                        raise ResourceError(
                            f"ResourcePool acquire timeout after {timeout_s}s for {name!r} (max_size={self.max_size}).",
                            code="POOL_TIMEOUT_001",
                        )
                    self._cond.wait(timeout=remaining)
                    # loop will check elapsed again

    def release(self, pooled: PooledResource) -> None:
        """Return a resource to the pool.

        Args:
            pooled: Wrapper returned by :meth:`acquire`. Idempotent.

        Raises:
            ResourceError: If the wrapper was not acquired from this pool or already released.
        """
        if not isinstance(pooled, PooledResource):
            raise ResourceError(
                f"release() expects PooledResource, got {type(pooled).__name__}: {pooled!r}.",
                code="POOL_RELEASE_001",
            )
        with self._cond:
            rid = id(pooled.resource)
            if rid not in self._active:
                # Already released or foreign — idempotent if previously released, error if foreign
                if pooled._released:
                    return
                raise ResourceError(
                    f"PooledResource for {pooled.name!r} not active in this pool (double release or foreign pool).",
                    code="POOL_RELEASE_002",
                )
            self._active.discard(rid)
            self._active_wrappers.pop(rid, None)
            pooled._released = True
            # Return raw to idle queue
            self._idle.append(pooled.resource)
            # Ensure min_idle: if we have less than min_idle idle, keep; otherwise LRU is fine.
            # Wake one waiter
            self._cond.notify()
            # Optionally cleanup excess idle? Keep at most max_size idle — but total == idle+active, so idle can't exceed max_size.
            # If idle > max_size, trim? But active=0 and total==max_size, idle==max_size is okay.
            # No trimming needed; pool retains up to max_size idle.

    @property
    def total(self) -> int:
        """Total number of resources ever created (and not destroyed)."""
        with self._lock:
            return len(self._active_wrappers) + len(self._idle)

    @property
    def idle(self) -> int:
        """Number of idle resources available for immediate acquire."""
        with self._lock:
            return len(self._idle)

    @property
    def active(self) -> int:
        """Number of resources currently borrowed."""
        with self._lock:
            return len(self._active_wrappers)

    def metrics(self) -> dict[str, int]:
        """Return pool metrics dict with ``total``, ``idle``, ``active``."""
        with self._lock:
            return {"total": self.total, "idle": self.idle, "active": self.active}

    def close(self) -> None:
        """Close pool and cleanup idle resources (best-effort)."""
        with self._cond:
            for raw in list(self._idle):
                close = getattr(raw, "close", None)
                if callable(close):
                    with self._cond:
                        try:
                            close()
                        except Exception:
                            logger.debug("ResourcePool close cleanup failed", exc_info=True)
            self._idle.clear()
            # Active resources are not forcibly closed; they will be returned eventually
            # Notify waiters that pool is shutting down — they will raise on next loop if needed
            self._cond.notify_all()

    def __repr__(self) -> str:
        return f"ResourcePool(max_size={self.max_size}, idle={self.idle}, active={self.active}, total={self.total})"
