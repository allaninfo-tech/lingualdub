# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""Benchmarks for MiddlewareChain — PEV-003."""

from __future__ import annotations

import pytest

from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result
from lingualdub.middleware import MiddlewareChain
from lingualdub.middleware.base import ExecutionContext
from lingualdub.utils.provenance import make_run_id


class _NoOpMiddleware:
    name = "noop"
    priority = 50

    def before(self, ctx: ExecutionContext):
        return None

    def after(self, ctx: ExecutionContext, result: Result) -> Result:
        return result

    def on_error(self, ctx: ExecutionContext, error: Exception):
        return None


def _make_chain(n: int) -> MiddlewareChain:
    mws = []
    for i in range(n):
        m = _NoOpMiddleware()
        m.name = f"noop_{i}"
        m.priority = i * 10
        mws.append(m)  # type: ignore[arg-type]
    return MiddlewareChain(mws)  # type: ignore[arg-type]


def _make_context():
    return ExecutionContext(
        pipeline_name="bench",
        input=Resource(id="x", kind=ResourceKind.SPEECH, language="lug", version="1.0.0"),
        run_id=make_run_id(),
        metadata={},
    )


@pytest.mark.parametrize("n", [0, 3, 10])
def test_bench_middleware_chain(benchmark, n):
    chain = _make_chain(n)
    ctx = _make_context()

    def pipeline_fn(c: ExecutionContext) -> Result:
        return Result(source_language="lug")

    benchmark(lambda: chain.run(ctx, pipeline_fn))


def test_bench_middleware_0(benchmark):
    chain = _make_chain(0)
    ctx = _make_context()
    benchmark(lambda: chain.run(ctx, lambda c: Result(source_language="lug")))


def test_bench_middleware_3(benchmark):
    chain = _make_chain(3)
    ctx = _make_context()
    benchmark(lambda: chain.run(ctx, lambda c: Result(source_language="lug")))


def test_bench_middleware_10(benchmark):
    chain = _make_chain(10)
    ctx = _make_context()
    benchmark(lambda: chain.run(ctx, lambda c: Result(source_language="lug")))
