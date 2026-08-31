"""Tests for lingualdub.core.pipeline."""

import pytest
from typing import Union
from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


class MockASR(Component):
    name: str = "mock_asr"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.ASR
    supported_languages = ["lug"]
    requires = []
    provides = ["transcription", "word_timestamps"]
    on_failure = FailureMode.ABORT

    def run(self, input: Union[Result, Resource]) -> Result:
        return Result()


class MockTranslation(Component):
    name: str = "mock_translation"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.TRANSLATION
    supported_languages = ["lug"]
    requires = ["transcription"]
    provides = ["translation"]
    on_failure = FailureMode.ABORT

    def run(self, input: Union[Result, Resource]) -> Result:
        return Result()


def test_pipeline_creation():
    p = Pipeline(stages=[MockASR()], source_language="lug")
    assert len(p.stages) == 1


def test_pipeline_requires_stages():
    with pytest.raises(ValueError):
        Pipeline(stages=[], source_language="lug")


def test_pipeline_requires_source_language():
    with pytest.raises(ValueError):
        Pipeline(stages=[MockASR()], source_language="")


def test_pipeline_stage_names():
    p = Pipeline(stages=[MockASR(), MockTranslation()], source_language="lug")
    assert p.stage_names == ["mock_asr", "mock_translation"]


def test_pipeline_single_stage_no_requires():
    p = Pipeline(stages=[MockASR()], source_language="lug")
    assert p.stages[0].name == "mock_asr"


def test_pipeline_compatibility_check_passes():
    p = Pipeline(stages=[MockASR(), MockTranslation()], source_language="lug")
    assert len(p.stages) == 2


def test_pipeline_compatibility_check_fails():
    # MockTranslation requires 'transcription' but nothing is upstream
    with pytest.raises(ValueError, match="compatibility error"):
        Pipeline(stages=[MockTranslation()], source_language="lug")


def test_pipeline_target_language_optional():
    p = Pipeline(stages=[MockASR()], source_language="lug")
    assert p.target_language is None


def test_pipeline_per_segment_language_default():
    p = Pipeline(stages=[MockASR()], source_language="lug")
    assert p.per_segment_language is False


def test_pipeline_repr():
    p = Pipeline(stages=[MockASR()], source_language="lug")
    r = repr(p)
    assert "lug" in r
    assert "mock_asr" in r
