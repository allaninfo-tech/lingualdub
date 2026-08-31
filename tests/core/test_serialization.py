"""Round-trip serialization tests for all core objects."""

from lingualdub.core.language import Language
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.segment import Segment
from lingualdub.core.result import Result, ResultStatus


def test_language_round_trip():
    original = Language(
        code="lug", name="Luganda", family="Bantu (Great Lakes)",
        resource_profile="speech-moderate / text-moderate",
        supported_tasks=["asr", "translation"],
        related_languages=["nyn"],
        metadata={"region": "Uganda"},
    )
    restored = Language.from_dict(original.to_dict())
    assert restored.code == original.code
    assert restored.name == original.name
    assert restored.family == original.family
    assert restored.resource_profile == original.resource_profile
    assert restored.supported_tasks == original.supported_tasks
    assert restored.related_languages == original.related_languages
    assert restored.metadata == original.metadata


def test_resource_round_trip():
    original = Resource(
        id="lug_speech_v1", kind=ResourceKind.SPEECH, language="lug", version="1.0.0",
        provenance={"source": "CommonVoice", "license": "CC0"},
        quality_flags=["weak_transcripts"],
        path="/data/lug.wav",
    )
    restored = Resource.from_dict(original.to_dict())
    assert restored.id == original.id
    assert restored.kind == original.kind
    assert restored.language == original.language
    assert restored.version == original.version
    assert restored.provenance == original.provenance
    assert restored.quality_flags == original.quality_flags
    assert restored.path == original.path


def test_resource_kind_preserved():
    for kind in ResourceKind:
        r = Resource(id="x", kind=kind, language="lug", version="1.0.0")
        restored = Resource.from_dict(r.to_dict())
        assert restored.kind == kind


def test_segment_round_trip():
    original = Segment(
        start=1.0, end=3.5, text="Oli otya", language="lug",
        speaker="SPK_001", confidence=0.92, source_language="lug",
        provenance={"model": "whisper"}, metadata={"word_count": 2},
    )
    restored = Segment.from_dict(original.to_dict())
    assert restored.start == original.start
    assert restored.end == original.end
    assert restored.text == original.text
    assert restored.language == original.language
    assert restored.speaker == original.speaker
    assert restored.confidence == original.confidence
    assert restored.source_language == original.source_language
    assert restored.provenance == original.provenance
    assert restored.metadata == original.metadata


def test_result_round_trip():
    seg = Segment(start=0.0, end=2.0, text="hello", language="lug")
    original = Result(
        segments=[seg],
        source_language="lug",
        target_language="eng",
        status=ResultStatus.PARTIAL,
        warnings=["something skipped"],
        provenance={"run_id": "abc123"},
        artifacts=["/out/audio.wav"],
        metadata={"wer": 0.15},
    )
    restored = Result.from_dict(original.to_dict())
    assert len(restored.segments) == 1
    assert restored.segments[0].text == "hello"
    assert restored.source_language == original.source_language
    assert restored.target_language == original.target_language
    assert restored.status == original.status
    assert restored.warnings == original.warnings
    assert restored.provenance == original.provenance
    assert restored.artifacts == original.artifacts
    assert restored.metadata == original.metadata


def test_result_status_preserved():
    for status in ResultStatus:
        r = Result(status=status)
        restored = Result.from_dict(r.to_dict())
        assert restored.status == status


def test_pipeline_to_dict():
    from lingualdub.core.component import Component, ComponentTask, FailureMode
    from lingualdub.core.pipeline import Pipeline
    from lingualdub.core.resource import Resource
    from lingualdub.core.result import Result
    from typing import Union

    class MockStage(Component):
        name: str = "mock_asr"
        version: str = "1.0.0"
        task: ComponentTask = ComponentTask.ASR
        supported_languages = []
        requires = []
        provides = ["transcription"]
        on_failure = FailureMode.ABORT
        def run(self, input: Union[Result, Resource]) -> Result:
            return Result()

    p = Pipeline(
        stages=[MockStage()],
        source_language="lug",
        target_language="eng",
        name="test_pipeline",
        description="A test pipeline",
        metadata={"env": "test"},
    )
    d = p.to_dict()
    assert d["source_language"] == "lug"
    assert d["target_language"] == "eng"
    assert d["name"] == "test_pipeline"
    assert d["stages"] == [{"name": "mock_asr", "version": "1.0.0"}]
    assert d["metadata"] == {"env": "test"}


def test_pipeline_from_dict():
    from lingualdub.core.component import Component, ComponentTask, FailureMode
    from lingualdub.core.pipeline import Pipeline
    from lingualdub.core.resource import Resource
    from lingualdub.core.result import Result
    from typing import Union

    class MockStage(Component):
        name: str = "mock_asr"
        version: str = "1.0.0"
        task: ComponentTask = ComponentTask.ASR
        supported_languages = []
        requires = []
        provides = ["transcription"]
        on_failure = FailureMode.ABORT
        def run(self, input: Union[Result, Resource]) -> Result:
            return Result()

    original = Pipeline(stages=[MockStage()], source_language="lug", target_language="eng")
    d = original.to_dict()
    restored = Pipeline.from_dict(d, resolved_stages=[MockStage()])
    assert restored.source_language == "lug"
    assert restored.target_language == "eng"
    assert restored.stage_names == ["mock_asr"]
