# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""Benchmarks for Pipeline assembly — PEV-003."""

from __future__ import annotations

import pytest

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


class _DummyStage(Component):
    name = "bench_dummy"
    version = "1.0.0"
    task = ComponentTask.ASR
    supported_languages = []
    requires = []
    provides = []
    on_failure = FailureMode.ABORT

    def run(self, inp: Result | Resource) -> Result:
        return Result(source_language="lug")


def _make_pipeline(n: int) -> Pipeline:
    stages = []
    for i in range(n):
        # Create distinct stage instances with unique names to avoid capability conflicts
        comp = _DummyStage()
        comp.name = f"bench_dummy_{i}"
        stages.append(comp)
    return Pipeline(stages=stages, source_language="lug", target_language="eng")


@pytest.mark.parametrize("n", [3, 5, 10])
def test_bench_pipeline_assembly(benchmark, n):
    benchmark(lambda: _make_pipeline(n))


def test_bench_pipeline_assembly_3(benchmark):
    benchmark(lambda: _make_pipeline(3))


def test_bench_pipeline_assembly_5(benchmark):
    benchmark(lambda: _make_pipeline(5))


def test_bench_pipeline_assembly_10(benchmark):
    benchmark(lambda: _make_pipeline(10))
