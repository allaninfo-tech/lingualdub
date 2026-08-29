"""
Base interface for translation components.

Translation components receive a Result carrying source-language Segments
and return a Result carrying translated Segments. Per-segment language
routing (Pipeline.per_segment_language) may cause a translation component
to be invoked once per distinct language span rather than once per utterance.
"""

from __future__ import annotations
from abc import abstractmethod
from typing import Union

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


class TranslationComponent(Component):
    """Base class for machine translation components."""

    task: ComponentTask = ComponentTask.TRANSLATION
    on_failure: FailureMode = FailureMode.ABORT

    @abstractmethod
    def run(self, input: Union[Result, Resource]) -> Result:
        """Translate segments and return a Result with translated text."""
        ...
