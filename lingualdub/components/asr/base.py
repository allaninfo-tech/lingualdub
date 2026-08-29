"""
Base interface for ASR components.

All ASR implementations must subclass ASRComponent and implement run().
The contract enforces that ASR components emit the capabilities declared
in their `provides` list so that downstream components (e.g. alignment,
code-switch detection) can perform compatibility checks at pipeline assembly.
"""

from __future__ import annotations
from abc import abstractmethod
from typing import Union

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


class ASRComponent(Component):
    """
    Base class for automatic speech recognition components.

    Implementations must:
    - Accept a Resource (audio file or stream reference) as input.
    - Return a Result with populated Segment objects carrying transcribed text,
      timing, and per-segment language.
    - Declare any capabilities they provide (e.g. "word_timestamps",
      "language_detection") in their `provides` list.
    """

    task: ComponentTask = ComponentTask.ASR
    on_failure: FailureMode = FailureMode.ABORT

    @abstractmethod
    def run(self, input: Union[Result, Resource]) -> Result:
        """Transcribe audio and return a Result with Segment objects."""
        ...
