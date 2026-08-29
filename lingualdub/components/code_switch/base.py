"""
Base interface for code-switching components.

Code-switching components detect language boundaries within a mixed-language
utterance and populate Segment.language on each Segment. This populates the
data hook that Pipeline.per_segment_language acts on, connecting detection
directly to per-segment routing behaviour.
"""

from __future__ import annotations
from abc import abstractmethod
from typing import Union

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


class CodeSwitchComponent(Component):
    """Base class for code-switch detection and routing components."""

    task: ComponentTask = ComponentTask.CODE_SWITCH
    on_failure: FailureMode = FailureMode.DEGRADE

    @abstractmethod
    def run(self, input: Union[Result, Resource]) -> Result:
        """
        Detect language boundaries and annotate each Segment with its language.
        Returns a Result with Segment.language populated per segment.
        """
        ...

    def degrade(self, input: Union[Result, Resource]) -> Result:
        """
        Default degrade path: return the input with source language applied
        uniformly to all segments (single-language-assumed processing).
        """
        result = input if isinstance(input, Result) else Result()
        result.mark_degraded(
            "Code-switch detection unavailable; treating all segments as source language."
        )
        return result
