"""
Base interface for TTS components.

TTS components receive a Result carrying translated text Segments and
synthesise speech audio. They may optionally use a speaker reference
from the input Result or from an attached Resource.
"""

from __future__ import annotations
from abc import abstractmethod
from typing import Union

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


class TTSComponent(Component):
    """Base class for text-to-speech components."""

    task: ComponentTask = ComponentTask.TTS
    on_failure: FailureMode = FailureMode.DEGRADE

    @abstractmethod
    def run(self, input: Union[Result, Resource]) -> Result:
        """Synthesise speech and return a Result with audio artifact links."""
        ...
