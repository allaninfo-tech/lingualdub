"""
Base interface for evaluation components.

Evaluators are Components of task type EVAL. They take one or more Results
as input and produce a Result carrying metrics rather than content. This
means evaluators register, version, and compose through the same Registry
as every other component, rather than living as separate external scripts.
"""

from __future__ import annotations
from abc import abstractmethod
from typing import List, Union

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


class EvaluatorComponent(Component):
    """
    Base class for evaluation components.

    Evaluators accept one or more Results and return a Result carrying
    metrics in its metadata field. They may also accept a reference Result
    to compare against (e.g. a reference transcription or gold translation).
    """

    task: ComponentTask = ComponentTask.EVAL
    on_failure: FailureMode = FailureMode.SKIP

    @abstractmethod
    def run(self, input: Union[Result, Resource]) -> Result:
        """
        Evaluate input and return a Result with metrics in result.metadata.
        """
        ...

    def evaluate_pair(self, hypothesis: Result, reference: Result) -> Result:
        """
        Evaluate a hypothesis Result against a reference Result.
        Override for evaluators that require paired comparison.
        """
        raise NotImplementedError(
            f"Evaluator {self.name!r} does not implement evaluate_pair()."
        )
