"""
Tests for per-segment language routing in PipelineExecutor (M3.2).
"""

import pytest
from typing import List, Union

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.result import Result, ResultStatus
from lingualdub.core.segment import Segment
from lingualdub.pipeline.executor import PipelineExecutor, PipelineExecutionError


class LugandaOnlyStage(Component):
    """Component that only processes Luganda segments and appends '[LUG_PROCESSED]'."""
    name = "lug_processor"
    version = "1.0.0"
    task = ComponentTask.TRANSLATION
    supported_languages = ["lug"]
    requires = []
    provides = ["translation"]
    on_failure = FailureMode.SKIP

    def run(self, input: Union[Result, Component]) -> Result:
        res = input if isinstance(input, Result) else Result()
        out_segs = []
        for s in res.segments:
            out_segs.append(
                Segment(
                    start=s.start,
                    end=s.end,
                    text=f"{s.text} [LUG_PROCESSED]",
                    language="eng",
                    source_language="lug",
                    metadata=dict(s.metadata),
                )
            )
        return Result(
            segments=out_segs,
            source_language=res.source_language,
            target_language="eng",
            provenance=dict(res.provenance),
        )


class StrictLugandaStage(LugandaOnlyStage):
    """Component that aborts if an unsupported language is encountered."""
    name = "strict_lug_processor"
    on_failure = FailureMode.ABORT


def test_per_segment_routing_disabled_by_default():
    """When per_segment_language is False, stage receives all segments."""
    stage = LugandaOnlyStage()
    pipe = Pipeline(stages=[stage], source_language="lug", per_segment_language=False)
    executor = PipelineExecutor(pipe)

    mixed_input = Result(
        segments=[
            Segment(start=0.0, end=1.0, text="Oli otya", language="lug"),
            Segment(start=1.0, end=2.0, text="Good morning", language="eng"),
        ],
        source_language="lug",
    )
    out = executor.run(mixed_input)

    # Without per_segment_language, stage processed all segments blindly
    assert len(out.segments) == 2
    assert "[LUG_PROCESSED]" in out.segments[0].text
    assert "[LUG_PROCESSED]" in out.segments[1].text


def test_per_segment_routing_skips_unsupported_segments():
    """M3.2: When per_segment_language is True, stage only runs on supported segments."""
    stage = LugandaOnlyStage()
    pipe = Pipeline(
        stages=[stage],
        source_language="lug",
        target_language="eng",
        per_segment_language=True,
    )
    executor = PipelineExecutor(pipe)

    mixed_input = Result(
        segments=[
            Segment(start=0.0, end=1.0, text="Oli otya", language="lug"),
            Segment(start=1.0, end=2.5, text="my friend", language="eng"),
            Segment(start=2.5, end=4.0, text="Tusanyuse nnyo", language="lug"),
        ],
        source_language="lug",
        target_language="eng",
    )
    out = executor.run(mixed_input)

    assert len(out.segments) == 3

    # Segment 0: Luganda -> processed
    assert out.segments[0].text == "Oli otya [LUG_PROCESSED]"
    assert out.segments[0].language == "eng"

    # Segment 1: English -> skipped by LugandaOnlyStage and kept intact
    assert out.segments[1].text == "my friend"
    assert out.segments[1].language == "eng"
    assert out.segments[1].metadata.get("skipped_by") == "lug_processor"

    # Segment 2: Luganda -> processed
    assert out.segments[2].text == "Tusanyuse nnyo [LUG_PROCESSED]"
    assert out.segments[2].language == "eng"

    # Status should reflect partial/skipped routing
    assert out.status in (ResultStatus.PARTIAL, ResultStatus.COMPLETE)


def test_per_segment_routing_aborts_on_unsupported_when_configured():
    """M3.2: ABORT mode raises PipelineExecutionError naming unsupported language."""
    stage = StrictLugandaStage()
    pipe = Pipeline(
        stages=[stage],
        source_language="lug",
        per_segment_language=True,
        on_stage_failure=FailureMode.ABORT,
    )
    executor = PipelineExecutor(pipe)

    mixed_input = Result(
        segments=[
            Segment(start=0.0, end=1.0, text="Hello", language="eng"),
        ],
        source_language="lug",
    )

    with pytest.raises(PipelineExecutionError) as exc_info:
        executor.run(mixed_input)

    assert "does not support segment language" in str(exc_info.value).lower()
    assert "eng" in str(exc_info.value)


def test_per_segment_routing_all_segments_unsupported():
    """When all segments are unsupported and failure_mode is SKIP, all pass through."""
    stage = LugandaOnlyStage()
    pipe = Pipeline(
        stages=[stage],
        source_language="eng",
        per_segment_language=True,
    )
    executor = PipelineExecutor(pipe)

    all_eng_input = Result(
        segments=[
            Segment(start=0.0, end=1.0, text="This is pure English", language="eng"),
            Segment(start=1.0, end=2.0, text="No Luganda here", language="eng"),
        ],
        source_language="eng",
    )
    out = executor.run(all_eng_input)

    assert len(out.segments) == 2
    assert out.segments[0].text == "This is pure English"
    assert out.segments[1].text == "No Luganda here"
    assert out.status == ResultStatus.PARTIAL
