"""
Base interface for TTS components.

TTS components receive a Result carrying translated text Segments and
synthesise speech audio. They may optionally use a speaker reference
from the input Result or from an attached Resource.
"""

from __future__ import annotations
from abc import abstractmethod
from enum import Enum
from typing import Union

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


class FittingStrategy(str, Enum):
    """
    Speech-rate control strategy chosen per segment to fit the source timing envelope.

    COMPRESS: Speed up speech synthesis to fit the target duration (ratio 0.7–1.35).
    SPLIT:    Break the segment at clause/punctuation boundaries (ratio > 1.35, splittable).
    SKIP:     Mark the segment as unfit for dubbing (ratio > 1.75, unsplittable).
    """

    COMPRESS = "compress"
    SPLIT = "split"
    SKIP = "skip"


class TTSComponent(Component):
    """Base class for text-to-speech components."""

    task: ComponentTask = ComponentTask.TTS
    on_failure: FailureMode = FailureMode.DEGRADE

    @abstractmethod
    def run(self, input: Union[Result, Resource]) -> Result:
        """Synthesise speech and return a Result with audio artifact links."""
        ...
