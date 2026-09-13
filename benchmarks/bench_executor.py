# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""Benchmarks for PipelineExecutor overhead — PEV-003."""

from __future__ import annotations

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result
from lingualdub.pipeline.executor import PipelineExecutor
from lingualdub.testing.fakes import FakeASR, FakeTranslation, FakeTTS


class _QuickDummy(Component):
    name = "quick_dummy"
    version = "1.0.0"
    task = ComponentTask.ASR
    supported_languages = []
    requires = []
    provides = ["transcription"]
    on_failure = FailureMode.ABORT

    def run(self, inp: Result | Resource) -> Result:
        if isinstance(inp, Resource):
            return Result(source_language="lug", segments=[])
        return inp


def test_bench_executor_dummy_overhead(benchmark):
    pipeline = Pipeline(stages=[_QuickDummy()], source_language="lug")
    executor = PipelineExecutor(pipeline)
    res = Resource(id="t", kind=ResourceKind.SPEECH, language="lug", version="1.0.0")
    benchmark(lambda: executor.run(res))


def test_bench_executor_fake_pipeline(benchmark):
    pipeline = Pipeline(
        stages=[FakeASR(), FakeTranslation(), FakeTTS()],
        source_language="lug",
        target_language="eng",
    )
    executor = PipelineExecutor(pipeline)
    res = Resource(id="t", kind=ResourceKind.SPEECH, language="lug", version="1.0.0")
    benchmark(lambda: executor.run(res))


def test_bench_executor_empty(benchmark):
    # Single stage, no-op
    pipeline = Pipeline(stages=[_QuickDummy()], source_language="lug")
    executor = PipelineExecutor(pipeline)
    inp = Result(source_language="lug")
    benchmark(lambda: executor.run(inp))
