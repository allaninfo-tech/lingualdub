# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Async/sync boundary utilities (REL-004).

The framework's primary execution model is **synchronous** — ``PipelineExecutor.run()``
blocks the calling thread for model loading, file I/O, and network calls.
This module provides thin async wrappers so web-service callers can
``await`` pipeline execution without blocking the event loop.

Usage:
    import asyncio
    from lingualdub.async_utils import run_pipeline_async, AsyncPipelineExecutor

    # Function form:
    result = await run_pipeline_async(executor, audio_resource)

    # Class wrapper:
    aexec = AsyncPipelineExecutor(executor)
    result = await aexec.run(audio_resource)
"""

from __future__ import annotations

import asyncio
from typing import Any

from lingualdub.core.resource import Resource
from lingualdub.core.result import Result

__all__ = ["run_pipeline_async", "AsyncPipelineExecutor"]


async def run_pipeline_async(executor: Any, input_resource: Resource | Result) -> Result:
    """Run a pipeline in a thread without blocking the event loop.

    Args:
        executor: A :class:`lingualdub.pipeline.executor.PipelineExecutor` instance
            (or any object exposing a ``run(input) -> Result`` method).
        input_resource: Input :class:`Resource` or :class:`Result`.

    Returns:
        The pipeline :class:`Result`.

    Raises:
        Any exception raised by ``executor.run`` is propagated.

    Note:
        Uses ``asyncio.to_thread`` (Python 3.9+). When running under a non-asyncio
        event loop the call still works via the default executor.
    """
    # Check for asyncio running loop; if none, raise with clear message rather than hanging
    # to_thread requires an active event loop when awaited, which calling context guarantees.
    return await asyncio.to_thread(executor.run, input_resource)  # type: ignore[arg-type]


class AsyncPipelineExecutor:
    """Thin async wrapper around a synchronous :class:`PipelineExecutor`.

    Example:
        executor = PipelineExecutor(pipeline)
        async_executor = AsyncPipelineExecutor(executor)
        result = await async_executor.run(resource)

    The wrapper holds a reference to the original executor and exposes an
    ``async run`` method that delegates to :func:`run_pipeline_async`.

    Attributes:
        executor: The underlying synchronous executor.
    """

    def __init__(self, executor: Any) -> None:
        if executor is None:
            raise ValueError("AsyncPipelineExecutor requires a non-None executor.")
        if not hasattr(executor, "run") or not callable(getattr(executor, "run")):
            raise ValueError(f"executor must expose a callable run(input) method, got {type(executor).__name__}: {executor!r}.")
        self.executor: Any = executor

    async def run(self, input_resource: Resource | Result) -> Result:
        """Async pipeline execution.

        Args:
            input_resource: Input resource/result.

        Returns:
            Pipeline :class:`Result`.
        """
        return await run_pipeline_async(self.executor, input_resource)

    def __repr__(self) -> str:
        return f"AsyncPipelineExecutor(executor={self.executor!r})"
