"""
Unit tests for abstract base components (Adaptation, Alignment, Speaker).
"""

from typing import Union
from lingualdub.components.adaptation.base import AdaptationComponent
from lingualdub.components.alignment.base import AlignmentComponent
from lingualdub.components.speaker.base import SpeakerComponent
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result, ResultStatus


class DummyAdaptation(AdaptationComponent):
    name = "dummy_adaptation"
    version = "1.0.0"

    def run(self, input: Union[Result, Resource]) -> Result:
        res = input if isinstance(input, Result) else Result()
        res.artifacts.append("checkpoint.pt")
        return res


class DummyAlignment(AlignmentComponent):
    name = "dummy_alignment"
    version = "1.0.0"

    def run(self, input: Union[Result, Resource]) -> Result:
        res = input if isinstance(input, Result) else Result()
        return res


class DummySpeaker(SpeakerComponent):
    name = "dummy_speaker"
    version = "1.0.0"

    def run(self, input: Union[Result, Resource]) -> Result:
        res = input if isinstance(input, Result) else Result()
        res.metadata["speaker_id"] = "spk_01"
        return res


def test_adaptation_component():
    adapt = DummyAdaptation()
    assert adapt.task == ComponentTask.ADAPTATION
    assert adapt.on_failure == FailureMode.ABORT
    res = adapt.run(Resource(id="r1", kind=ResourceKind.TEXT, language="lug", version="1.0"))
    assert "checkpoint.pt" in res.artifacts


def test_alignment_component():
    align = DummyAlignment()
    assert align.task == ComponentTask.ALIGNMENT
    assert align.on_failure == FailureMode.DEGRADE

    out = align.run(Result())
    assert isinstance(out, Result)

    degraded = align.degrade(Result())
    assert degraded.status == ResultStatus.DEGRADED


def test_speaker_component():
    speaker = DummySpeaker()
    assert speaker.task == ComponentTask.SPEAKER
    assert speaker.on_failure == FailureMode.DEGRADE

    out = speaker.run(Result())
    assert out.metadata["speaker_id"] == "spk_01"
