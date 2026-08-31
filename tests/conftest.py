"""
Shared test fixtures for the LingualDub test suite.
"""
from __future__ import annotations
from typing import Union

import pytest

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.language import Language
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment


class MockComponent(Component):
    """A minimal concrete Component for use in tests. Does no real processing."""

    name: str = "mock"
    version: str = "0.0.1"
    task: ComponentTask = ComponentTask.ASR
    supported_languages = ["lug", "nyn"]
    requires = []
    provides = ["transcription"]
    on_failure = FailureMode.ABORT

    def run(self, input: Union[Result, Resource]) -> Result:
        return Result(source_language="lug")


@pytest.fixture
def mock_component() -> MockComponent:
    """A concrete Component instance usable in tests."""
    return MockComponent()


@pytest.fixture
def sample_segment() -> Segment:
    return Segment(start=0.0, end=2.0, text="Oli otya", language="lug")


@pytest.fixture
def sample_result(sample_segment: Segment) -> Result:
    return Result(
        segments=[sample_segment],
        source_language="lug",
        provenance={"run_id": "test-run-001"},
    )


@pytest.fixture
def sample_language() -> Language:
    return Language(
        code="lug",
        name="Luganda",
        family="Bantu (Great Lakes)",
        resource_profile="speech-moderate / text-moderate",
        supported_tasks=["asr", "translation"],
        related_languages=["nyn"],
    )


@pytest.fixture
def sample_resource() -> Resource:
    return Resource(
        id="lug_speech_v1",
        kind=ResourceKind.SPEECH,
        language="lug",
        version="1.0.0",
        provenance={"source": "CommonVoice", "license": "CC0"},
    )
