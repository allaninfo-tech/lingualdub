# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Middleware pipeline — EXT-005.

Defines :class:`MiddlewareProtocol`, :class:`ExecutionContext`, and
:class:`MiddlewareChain` that wraps pipeline execution with before/after
hooks, short-circuiting, and error handling.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from lingualdub.core.resource import Resource
from lingualdub.core.result import Result

logger = logging.getLogger(__name__)

__all__ = ["MiddlewareProtocol", "ExecutionContext", "MiddlewareChain"]


@dataclass
class ExecutionContext:
    """Context passed through middleware and to the pipeline executor.

    Attributes:
        pipeline_name: Name of the pipeline being executed (or ``repr(pipeline)``).
        pipeline: Optional pipeline instance (for advanced middleware).
        input: Original input ``Resource`` or ``Result``.
        run_id: Unique run identifier (from ``make_run_id``).
        metadata: Free-form metadata dict for middleware communication.
        _short_circuit_result: If set by a ``before`` hook, pipeline execution
            is skipped and this result is returned directly.
    """

    pipeline_name: str
    input: Resource | Result
    run_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    pipeline: Any | None = None
    _short_circuit_result: Result | None = field(default=None, repr=False, compare=False)

    def short_circuit(self, result: Result) -> None:
        """Signal that pipeline execution should be skipped and ``result`` returned."""
        self._short_circuit_result = result


@runtime_checkable
class MiddlewareProtocol(Protocol):
    """Structural contract for pipeline middleware — ``experimental``.

    Attributes:
        name: Unique middleware name.
        priority: Ordering key — lower values are outermost (run first in ``before``,
            last in ``after``). Recommended: 0-100 for built-ins, 100+ for user.

    Methods:
        before: Pre-execution hook. May mutate ``context`` or short-circuit
            by returning a ``Result`` or calling ``context.short_circuit(result)``.
        after: Post-execution hook. May transform the result.
        on_error: Error hook. If pipeline raises, each middleware's ``on_error``
            is called in reverse order; the first non-``None`` Result is returned.
    """

    name: str
    priority: int

    def before(self, context: ExecutionContext) -> ExecutionContext | Result | None:
        """Called before pipeline execution.

        Args:
            context: Execution context.

        Returns:
            * ``ExecutionContext`` — updated context (or same object).
            * ``Result`` — short-circuit value; pipeline is skipped.
            * ``None`` — no change.
        """
        ...

    def after(self, context: ExecutionContext, result: Result) -> Result:
        """Called after successful pipeline execution; may transform ``result``."""
        ...

    def on_error(self, context: ExecutionContext, error: Exception) -> Result | None:
        """Called when pipeline raises; return ``Result`` to recover or ``None`` to propagate."""
        ...


class MiddlewareChain:
    """Composes a list of middleware in priority order.

    Example:
        chain = MiddlewareChain([LoggingMiddleware(), TimingMiddleware()])
        result = chain.run(context, lambda ctx: executor.run(ctx.input))

    Ordering:
        * ``before`` — ascending ``priority`` (lower outermost)
        * ``after`` / ``on_error`` — descending ``priority`` (reverse)

    Attributes:
        middlewares: Sorted list of middleware (ascending priority).
    """

    def __init__(self, middlewares: list[MiddlewareProtocol] | None = None) -> None:
        mws = list(middlewares or [])
        # Stable sort by priority, then by name for determinism when priorities tie
        mws.sort(key=lambda m: (getattr(m, "priority", 100), getattr(m, "name", "")))
        self.middlewares: list[MiddlewareProtocol] = mws

    def add(self, middleware: MiddlewareProtocol) -> None:
        """Add a middleware and keep sorted."""
        self.middlewares.append(middleware)
        self.middlewares.sort(key=lambda m: (getattr(m, "priority", 100), getattr(m, "name", "")))

    def __len__(self) -> int:
        return len(self.middlewares)

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.middlewares)

    def run(
        self,
        context: ExecutionContext,
        pipeline_fn: Any,  # Callable[[ExecutionContext], Result]
    ) -> Result:
        """Execute ``pipeline_fn`` through middleware.

        Steps:
        1. Call ``before`` for each middleware in priority order.  If any
           returns a ``Result``, short-circuit and skip pipeline.
        2. If not short-circuited, call ``pipeline_fn(context)``.
        3. On success, call ``after`` for each middleware in reverse order.
        4. On exception, call ``on_error`` in reverse order; first non-``None``
           Result is returned, otherwise the exception is re-raised.

        Args:
            context: Execution context.
            pipeline_fn: Callable that executes the pipeline and returns a Result.

        Returns:
            Result from pipeline (or middleware).

        Raises:
            Exception: Original pipeline exception if no middleware recovers.
        """
        # 1. before
        for mw in self.middlewares:
            before = getattr(mw, "before", None)
            if not callable(before):
                continue
            try:
                ret = before(context)
            except Exception as exc:
                # before failure is treated as pipeline error — try on_error
                logger.warning(
                    "Middleware %r before() failed: %s",
                    getattr(mw, "name", str(mw)),
                    exc,
                    exc_info=True,
                )
                ret_on_error = self._handle_error(context, exc)
                if ret_on_error is not None:
                    return ret_on_error
                raise
            # Interpret return value
            if isinstance(ret, Result):
                # Short-circuit
                context.short_circuit(ret)
                short_result = ret
                # Still call after for already-processed before middleware? For now return short_result via after chain
                # So we short-circuit pipeline and go directly to after
                return self._run_after(context, short_result)
            elif isinstance(ret, ExecutionContext):
                context = ret
            # Check short_circuit flag set by middleware via context.short_circuit()
            if context._short_circuit_result is not None:
                return self._run_after(context, context._short_circuit_result)

            # None means no change

        # 2. pipeline
        try:
            result = pipeline_fn(context)
        except Exception as exc:
            # 4. on_error
            recovered = self._handle_error(context, exc)
            if recovered is not None:
                return recovered
            raise

        # 3. after in reverse
        return self._run_after(context, result)

    def _run_after(self, context: ExecutionContext, result: Result) -> Result:
        for mw in reversed(self.middlewares):
            after = getattr(mw, "after", None)
            if not callable(after):
                continue
            try:
                ret = after(context, result)
                if isinstance(ret, Result):
                    result = ret
            except Exception as exc:
                logger.warning(
                    "Middleware %r after() failed: %s",
                    getattr(mw, "name", str(mw)),
                    exc,
                    exc_info=True,
                )
                # after failure tries on_error
                recovered = self._handle_error(context, exc)
                if recovered is not None:
                    return recovered
                raise
        return result

    def _handle_error(self, context: ExecutionContext, error: Exception) -> Result | None:
        for mw in reversed(self.middlewares):
            on_error = getattr(mw, "on_error", None)
            if not callable(on_error):
                continue
            try:
                ret = on_error(context, error)
                if isinstance(ret, Result):
                    return ret
                if ret is not None:
                    # Allow middleware to return something truthy that is not Result? Spec says Result | None
                    # If they return non-None non-Result, log and continue
                    logger.debug(
                        "Middleware %r on_error returned non-Result %r; ignoring.",
                        getattr(mw, "name", str(mw)),
                        ret,
                    )
            except Exception as exc:
                logger.warning(
                    "Middleware %r on_error() failed: %s",
                    getattr(mw, "name", str(mw)),
                    exc,
                    exc_info=True,
                )
        return None

    @classmethod
    def build(cls, pipeline_name: str, registry: Any | None = None) -> MiddlewareChain:  # type: ignore[no-untyped-def]
        """Build a chain for ``pipeline_name`` using a ``MiddlewareRegistry``.

        This is a convenience for EXT-007 integration: if a registry is
        provided, global + pipeline-scoped middleware are combined in priority
        order.  Otherwise returns an empty chain.

        Args:
            pipeline_name: Name of the pipeline to build chain for.
            registry: Optional ``MiddlewareRegistry``.

        Returns:
            New ``MiddlewareChain``.
        """
        if registry is None:
            return cls([])
        try:
            mws = registry.list_middleware(pipeline_name)  # type: ignore[operator]
            if mws is None:
                mws = []
        except Exception:
            mws = registry.list_middleware()  # type: ignore[operator]
        return cls(list(mws))

    def __repr__(self) -> str:
        return (
            f"MiddlewareChain(middlewares={[getattr(m, 'name', str(m)) for m in self.middlewares]})"
        )
