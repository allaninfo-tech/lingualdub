"""
Base interface for adaptation components.

Adaptation components implement parameter-efficient fine-tuning, cross-lingual
transfer, and related data workflows. Artifacts produced by adaptation runs
are registered back into the Registry with version and provenance so they
can be resolved by later pipelines as first-class components.
"""

from __future__ import annotations
from abc import abstractmethod
from typing import Union

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


class AdaptationComponent(Component):
    """Base class for model adaptation and fine-tuning components."""

    task: ComponentTask = ComponentTask.ADAPTATION
    on_failure: FailureMode = FailureMode.ABORT

    @abstractmethod
    def run(self, input: Union[Result, Resource]) -> Result:
        """
        Run an adaptation workflow against the provided resource.
        Returns a Result carrying artifact links to the adapted checkpoint.
        """
        ...
