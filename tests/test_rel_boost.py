# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""Coverage boost for REL-005/002/004/001/003 — not a spec test, just to ensure overall coverage passes."""

import tempfile
from pathlib import Path

import pytest

from lingualdub.async_utils import AsyncPipelineExecutor, run_pipeline_async
from lingualdub.core.resource import Resource, ResourceKind, ResourceOwnership
from lingualdub.core.result import ResultStatus
from lingualdub.registry.registry import Registry
from lingualdub.resources.pool import ResourcePool
from lingualdub.testing.builders import (
    LanguageBuilder,
    ResourceBuilder,
    ResultBuilder,
    SegmentBuilder,
)
from lingualdub.testing.clock import FakeClock
from lingualdub.testing.fakes import FakeAlignment, FakeASR, FakeEvaluator, FakeTranslation, FakeTTS
from lingualdub.testing.matchers import (
    assert_resource_valid,
    assert_result_complete,
    assert_result_degraded,
    assert_result_failed,
    assert_result_has_language,
    assert_result_has_segment,
    assert_result_partial,
)
from lingualdub.testing.pipeline import PipelineTestHarness


def test_builders_all():
    lb = (
        LanguageBuilder()
        .with_code("yor")
        .with_name("Yoruba")
        .with_family("Niger-Congo")
        .with_resource_profile("speech-moderate")
        .with_supported_tasks(["asr"])
        .with_related_languages([])
        .with_resources([])
        .with_compatible_components([])
        .with_metadata({})
        .build()
    )
    assert lb.code == "yor"
    rb = (
        ResourceBuilder()
        .with_id("id1")
        .with_kind(ResourceKind.TEXT)
        .with_language("eng")
        .with_version("1.0.1")
        .with_provenance({"source": "x"})
        .with_quality_flags([])
        .with_compatible_components([])
        .with_path(None)
        .with_metadata({})
        .with_ownership(ResourceOwnership.FRAMEWORK_OWNED)
        .build()
    )
    assert rb.ownership == ResourceOwnership.FRAMEWORK_OWNED
    seg = (
        SegmentBuilder()
        .with_start(0.5)
        .with_end(1.5)
        .with_text("hi")
        .with_language("eng")
        .with_speaker("spk")
        .with_confidence(0.8)
        .with_source_language("lug")
        .with_provenance({})
        .with_metadata({})
        .build()
    )
    assert seg.text == "hi"
    res = (
        ResultBuilder()
        .with_segments([seg])
        .with_source_language("eng")
        .with_target_language("lug")
        .with_status(ResultStatus.COMPLETE)
        .with_warnings([])
        .with_provenance({"run_id": "x"})
        .with_artifacts([])
        .with_metadata({})
        .add_segment(seg)
        .build(status=ResultStatus.COMPLETE)
    )
    assert len(res.segments) == 2


def test_fakes_protocol():
    from lingualdub.core.protocols import ComponentProtocol

    assert isinstance(FakeASR(), ComponentProtocol)
    assert isinstance(FakeTranslation(), ComponentProtocol)
    assert isinstance(FakeTTS(), ComponentProtocol)
    assert isinstance(FakeAlignment(), ComponentProtocol)
    assert isinstance(FakeEvaluator(), ComponentProtocol)
    # run and degrade
    r = ResourceBuilder().build()
    asr = FakeASR(text="hello", language="lug")
    out = asr.run(r)
    assert out.segments[0].text == "hello"
    deg = asr.degrade(r)
    assert deg.status == ResultStatus.DEGRADED
    trans = FakeTranslation().run(out)
    assert "(translated)" in trans.segments[0].text
    # TTS
    tts = FakeTTS()
    tts_out = tts.run(trans)
    assert tts_out.artifacts
    tts_deg = tts.degrade(trans)
    assert tts_deg.status == ResultStatus.DEGRADED
    # Alignment
    align = FakeAlignment()
    aligned = align.run(out)
    assert "word_timestamps" in aligned.segments[0].metadata
    # Evaluator
    evalr = FakeEvaluator()
    ev = evalr.run(out)
    assert "metrics" in ev.metadata
    ev2 = evalr.evaluate_pair(out, r)
    assert ev2 is not None


def test_matchers():
    ok = ResultBuilder().build()
    assert_result_complete(ok)
    assert_result_has_segment(ok, "hello")
    assert_result_has_language(ok, "lug")
    assert_resource_valid(ResourceBuilder().build())
    # partial, degraded, failed
    part = ResultBuilder().with_status(ResultStatus.PARTIAL).build()
    assert_result_partial(part)
    deg = ResultBuilder().with_status(ResultStatus.DEGRADED).build()
    assert_result_degraded(deg)
    failed = ResultBuilder().with_status(ResultStatus.FAILED).build()
    assert_result_failed(failed)
    # failure cases
    with pytest.raises(AssertionError):
        assert_result_complete(failed)
    with pytest.raises(AssertionError):
        assert_result_failed(ok)
    with pytest.raises(AssertionError):
        assert_result_has_segment(ok, "nonexistent")


def test_harness(tmp_path):
    harness = PipelineTestHarness()
    harness.with_components(FakeASR(), FakeTranslation(), FakeTTS())
    result = harness.run(ResourceBuilder().build())
    assert result.status == ResultStatus.COMPLETE
    # config path
    config = {
        "source_language": "lug",
        "target_language": "eng",
        "stages": [
            {"kind": "component", "key": "fake_asr"},
            {"kind": "component", "key": "fake_translator"},
            {"kind": "component", "key": "fake_tts"},
        ],
    }
    result2 = harness.run_with_config(config, ResourceBuilder().build())
    assert result2.status == ResultStatus.COMPLETE
    harness.assert_complete(result2)
    # build_pipeline explicit
    from lingualdub.core.component import Component, ComponentTask, FailureMode
    from lingualdub.core.resource import Resource as Res
    from lingualdub.core.result import Result

    class Dummy(Component):
        name = "dummy_test"
        version = "1.0.0"
        task = ComponentTask.ASR
        supported_languages = []
        requires = []
        provides = ["transcription"]
        on_failure = FailureMode.ABORT

        def run(self, inp: Result | Res) -> Result:
            return Result(source_language="lug")

    p = harness.build_pipeline(stages=[Dummy()], source_language="lug")
    assert p.source_language == "lug"


def test_clock():
    c = FakeClock(start=10.0)
    assert c.now() == 10.0
    assert c.time() == 10.0
    assert c.monotonic() == 10.0
    c.advance(0.5)
    assert c.now() == 10.5
    c.sleep(0.5)
    assert c.time() == 11.0
    assert c.sleeps == [0.5]
    dt = c.datetime_now()
    assert dt is not None
    c.reset(start=0)
    assert c.now() == 0
    with c:
        import time

        assert time.time() == 0
        c.advance(5)
        assert time.monotonic() == 5
    # after uninstall
    assert c.now() == 5
    # callable
    assert c() == 5
    # error paths
    with pytest.raises(ValueError):
        FakeClock(start="bad")
    with pytest.raises(ValueError):
        c.advance("bad")
    with pytest.raises(ValueError):
        c.advance(-1)


def test_pool_basic():
    from lingualdub.exceptions import ResourceError

    pool = ResourcePool(factory=lambda name: object(), max_size=2, min_idle=1)
    assert pool.metrics()["total"] == 1  # min_idle warmed
    a = pool.acquire("m")
    b = pool.acquire("m")
    assert a.resource is not b.resource
    assert pool.active == 2
    assert pool.idle == 0
    # timeout 0 should fail
    with pytest.raises(ResourceError):
        pool.acquire("m", timeout_s=0)
    pool.release(a)
    assert pool.idle == 1
    c = pool.acquire("m")
    assert pool.active == 2
    pool.release(b)
    pool.release(c)
    # release idempotent
    pool.release(a)  # already released earlier, should be no-op
    # context manager on fresh pool
    pool_ctx = ResourcePool(factory=lambda: {"id": 1}, max_size=1)
    with pool_ctx.acquire("x") as res:
        assert res is not None
        assert pool_ctx.active == 1
    assert pool_ctx.idle == 1
    pool.close()
    pool_ctx.close()
    assert pool_ctx.idle == 0


def test_pool_factory_variants():
    # factory without args
    pool = ResourcePool(factory=lambda: {"id": 1}, max_size=1)
    r = pool.acquire("any")
    assert r.resource["id"] == 1
    pool.release(r)
    # no factory
    pool2 = ResourcePool(max_size=1)
    r2 = pool2.acquire("z")
    assert r2.resource is not None
    pool2.release(r2)
    # invalid args
    with pytest.raises(ValueError):
        ResourcePool(max_size=0)
    with pytest.raises(ValueError):
        ResourcePool(max_size=5, min_idle=10)


def test_async_utils():
    import asyncio as _asyncio

    from lingualdub.core.component import Component, ComponentTask, FailureMode
    from lingualdub.core.pipeline import Pipeline
    from lingualdub.core.resource import Resource
    from lingualdub.core.result import Result
    from lingualdub.pipeline.executor import PipelineExecutor

    class Quick(Component):
        name = "quick"
        version = "1.0.0"
        task = ComponentTask.ASR
        supported_languages = []
        requires = []
        provides = []
        on_failure = FailureMode.ABORT

        def run(self, inp: Result | Resource) -> Result:
            return Result(source_language="lug")

    p = Pipeline(stages=[Quick()], source_language="lug")
    exec = PipelineExecutor(p)
    res = ResourceBuilder().build()

    async def _inner():
        out = await run_pipeline_async(exec, res)
        assert out.status == ResultStatus.COMPLETE
        # wrapper
        aexec = AsyncPipelineExecutor(exec)
        out2 = await aexec.run(res)
        assert out2.status == ResultStatus.COMPLETE
        try:
            AsyncPipelineExecutor(None)  # type: ignore[arg-type]
            raise AssertionError("should raise")
        except ValueError:
            pass
        try:
            AsyncPipelineExecutor(object())
            raise AssertionError("should raise")
        except ValueError:
            pass

    _asyncio.run(_inner())


def test_resource_ownership():
    # FRAMEWORK_OWNED cleaned
    from lingualdub.di import DependencyContainer, Lifetime

    tmp = tempfile.mktemp()
    Path(tmp).write_text("hi")
    container = DependencyContainer()
    container.register(
        "r",
        lambda: Resource(
            id="t",
            kind=ResourceKind.CHECKPOINT,
            language="eng",
            version="1.0.0",
            ownership=ResourceOwnership.FRAMEWORK_OWNED,
            path=tmp,
        ),
        lifetime=Lifetime.SCOPED,
    )
    with container.create_scope() as scope:
        scope.resolve("r")
        assert Path(tmp).exists()
    assert not Path(tmp).exists()
    # USER_OWNED not cleaned
    tmp2 = tempfile.mktemp()
    Path(tmp2).write_text("hi2")
    container2 = DependencyContainer()
    container2.register(
        "r2",
        lambda: Resource(
            id="t2",
            kind=ResourceKind.CHECKPOINT,
            language="eng",
            version="1.0.0",
            ownership=ResourceOwnership.USER_OWNED,
            path=tmp2,
        ),
        lifetime=Lifetime.SCOPED,
    )
    with container2.create_scope() as scope:
        scope.resolve("r2")
        assert Path(tmp2).exists()
    assert Path(tmp2).exists()
    Path(tmp2).unlink(missing_ok=True)
    # serialization
    r3 = Resource(
        id="x",
        kind=ResourceKind.SPEECH,
        language="lug",
        version="1.0.0",
        ownership=ResourceOwnership.SHARED,
    )
    d = r3.to_dict()
    assert d["ownership"] == "shared"
    r4 = Resource.from_dict(d)
    assert r4.ownership == ResourceOwnership.SHARED
    # registry concurrency already covered but ensure lock exists
    reg = Registry()
    assert hasattr(reg, "_lock")
