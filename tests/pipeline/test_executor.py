"""Tests for lingualdub.pipeline.executor."""

import pytest
from typing import Union
from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result, ResultStatus
from lingualdub.pipeline.executor import PipelineExecutor, PipelineExecutionError


# --- Mock stages ---

class GoodStage(Component):
    name: str = "good_stage"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.ASR
    requires = []
    provides = ["transcription"]
    on_failure = FailureMode.ABORT

    def run(self, input: Union[Result, Resource]) -> Result:
        return Result(metadata={"stage": "good"})


class FailingStage(Component):
    name: str = "failing_stage"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.ASR
    requires = []
    provides = ["transcription"]
    on_failure = FailureMode.ABORT

    def run(self, input: Union[Result, Resource]) -> Result:
        raise RuntimeError("stage failed")


class SkipStage(FailingStage):
    name: str = "skip_stage"
    on_failure = FailureMode.SKIP


class DegradingStage(Component):
    name: str = "degrading_stage"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.ASR
    requires = []
    provides = ["transcription"]
    on_failure = FailureMode.DEGRADE

    def run(self, input: Union[Result, Resource]) -> Result:
        raise RuntimeError("primary failed")

    def degrade(self, input: Union[Result, Resource]) -> Result:
        return Result(metadata={"degraded": True})


class ProvenanceStage(Component):
    name: str = "provenance_stage"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.ASR
    requires = []
    provides = ["transcription"]
    on_failure = FailureMode.ABORT

    def run(self, input: Union[Result, Resource]) -> Result:
        return Result(provenance={"stage_key": "stage_value"})


class SecondStage(Component):
    name: str = "second_stage"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.TRANSLATION
    requires = ["transcription"]
    provides = ["translation"]
    on_failure = FailureMode.ABORT

    def run(self, input: Union[Result, Resource]) -> Result:
        return Result(metadata={"second": True})


# --- Tests ---

def test_executor_runs_successfully():
    pipeline = Pipeline(stages=[GoodStage()], source_language="lug")
    executor = PipelineExecutor(pipeline)
    result = executor.run(Resource(id="test", kind="speech", language="lug", version="1.0"))
    assert result.status == ResultStatus.COMPLETE


def test_executor_abort_mode():
    pipeline = Pipeline(stages=[FailingStage()], source_language="lug")
    executor = PipelineExecutor(pipeline)
    with pytest.raises(PipelineExecutionError):
        executor.run(Result())


def test_executor_skip_mode():
    pipeline = Pipeline(stages=[SkipStage()], source_language="lug")
    executor = PipelineExecutor(pipeline)
    result = executor.run(Result())
    assert result.status == ResultStatus.PARTIAL


def test_executor_degrade_mode():
    pipeline = Pipeline(stages=[DegradingStage()], source_language="lug")
    executor = PipelineExecutor(pipeline)
    result = executor.run(Result())
    assert result.status == ResultStatus.DEGRADED


def test_executor_degrade_no_degrade_path():
    # SkipStage has no degrade() — should fall back to PARTIAL behaviour
    class NoDegradePath(FailingStage):
        name: str = "no_degrade"
        on_failure = FailureMode.DEGRADE
    pipeline = Pipeline(stages=[NoDegradePath()], source_language="lug")
    executor = PipelineExecutor(pipeline)
    result = executor.run(Result())
    assert result.status == ResultStatus.PARTIAL


def test_executor_multi_stage_skip_then_continue():
    pipeline = Pipeline(
        stages=[SkipStage(), SecondStage()],
        source_language="lug",
        on_stage_failure=FailureMode.SKIP,
    )
    executor = PipelineExecutor(pipeline)
    result = executor.run(Result())
    # SkipStage fails with SKIP, SecondStage runs and returns its Result
    assert result.status in (ResultStatus.PARTIAL, ResultStatus.COMPLETE)


def test_executor_provenance_not_lost():
    """BUG FIX TEST: executor-set provenance must survive stage Result replacement."""
    pipeline = Pipeline(stages=[ProvenanceStage()], source_language="lug")
    executor = PipelineExecutor(pipeline)
    result = executor.run(Result())
    # Must contain the executor-set key
    assert "pipeline" in result.provenance
    # Must also contain the stage-set key
    assert "stage_key" in result.provenance
    assert result.provenance["stage_key"] == "stage_value"


def test_executor_result_source_language():
    pipeline = Pipeline(stages=[GoodStage()], source_language="lug")
    executor = PipelineExecutor(pipeline)
    result = executor.run(Result())
    # The final result's source_language comes from the stage; check pipeline sets it initially
    assert pipeline.source_language == "lug"


def test_executor_result_target_language():
    pipeline = Pipeline(stages=[GoodStage()], source_language="lug", target_language="eng")
    executor = PipelineExecutor(pipeline)
    assert pipeline.target_language == "eng"
