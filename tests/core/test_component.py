"""Tests for lingualdub.core.component (Component base class)."""

import pytest
from typing import Union
from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


class MockASR(Component):
    """Concrete mock ASR component for testing."""
    name: str = "mock_asr"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.ASR
    supported_languages = ["lug", "nyn"]
    requires = []
    provides = ["transcription", "word_timestamps"]
    on_failure = FailureMode.ABORT

    def run(self, input: Union[Result, Resource]) -> Result:
        return Result()


def test_component_check_compatibility_empty():
    comp = MockASR()
    assert comp.check_compatibility([]) == []


def test_component_check_compatibility_satisfied():
    comp = MockASR()
    comp.requires = ["transcription"]
    assert comp.check_compatibility(["transcription", "word_timestamps"]) == []


def test_component_check_compatibility_missing():
    comp = MockASR()
    comp.requires = ["translation"]
    missing = comp.check_compatibility(["transcription"])
    assert "translation" in missing


def test_component_check_compatibility_partial():
    comp = MockASR()
    comp.requires = ["transcription", "alignment"]
    missing = comp.check_compatibility(["transcription"])
    assert missing == ["alignment"]


def test_component_supports_language_empty_list():
    comp = MockASR()
    comp.supported_languages = []
    assert comp.supports_language("any_language") is True
    assert comp.supports_language("eng") is True


def test_component_supports_language_match():
    comp = MockASR()
    assert comp.supports_language("lug") is True


def test_component_supports_language_no_match():
    comp = MockASR()
    assert comp.supports_language("eng") is False


def test_component_degrade_raises():
    comp = MockASR()
    with pytest.raises(NotImplementedError):
        comp.degrade(Result())


def test_component_repr():
    comp = MockASR()
    r = repr(comp)
    assert "mock_asr" in r
    assert "1.0.0" in r
    assert "asr" in r
