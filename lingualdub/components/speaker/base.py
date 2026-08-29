"""
Base interface for speaker modelling components.

Speaker components handle speaker representation, identification, and
embedding extraction. They are a dependency for cross-lingual voice transfer.
Consent verification for voice resources is enforced at the Resource level
before data reaches this component.
"""

from __future__ import annotations
from abc import abstractmethod
from typing import Union

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


class SpeakerComponent(Component):
    """Base class for speaker modelling and representation components."""

    task: ComponentTask = ComponentTask.SPEAKER
    on_failure: FailureMode = FailureMode.DEGRADE

    @abstractmethod
    def run(self, input: Union[Result, Resource]) -> Result:
        """Extract or apply speaker representations and return an updated Result."""
        ...
