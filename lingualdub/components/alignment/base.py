"""
Base interface for alignment components.

Alignment components handle duration modelling, speech-rate control,
segment fitting, and time-stretching for cross-lingual speech. They are
a near-term research module (temporal alignment) and a dependency for
audio-visual synchronisation.
"""

from __future__ import annotations
from abc import abstractmethod
from typing import Union

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


class AlignmentComponent(Component):
    """Base class for timing and duration alignment components."""

    task: ComponentTask = ComponentTask.ALIGNMENT
    on_failure: FailureMode = FailureMode.DEGRADE

    @abstractmethod
    def run(self, input: Union[Result, Resource]) -> Result:
        """Align segment timing and return a Result with updated Segment timing."""
        ...

    def degrade(self, input: Union[Result, Resource]) -> Result:
        """
        Default degrade path: return the input without alignment applied.
        Marks the result as degraded so consumers are aware timing is not adjusted.
        """
        result = input if isinstance(input, Result) else Result()
        result.mark_degraded("Alignment skipped; returning unaligned output.")
        return result
