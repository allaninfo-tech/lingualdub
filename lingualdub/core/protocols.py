# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Component contract protocols (PEP 544).

Structural (duck-typed) definitions of what it means to be a component,
evaluator, or registrable object in the framework. Using ``Protocol`` with
``runtime_checkable=True`` allows ``isinstance(obj, ComponentProtocol)`` to
succeed for third-party classes without inheriting from :class:`Component`.

These protocols are the stable extension point: external packages should type
against ``ComponentProtocol`` rather than importing :class:`Component` directly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result

__all__ = ["ComponentProtocol", "EvaluatorProtocol", "RegistrableProtocol"]


@runtime_checkable
class ComponentProtocol(Protocol):
    """
    Structural contract for a pipeline component.

    Any object with these attributes and methods satisfies the framework's
    component requirements without needing to inherit from
    :class:`lingualdub.core.component.Component`.

    Attributes:
        name: Unique name for this component implementation.
        version: Version string for this component.
        task: Processing task categorisation.
        supported_languages: Language codes this component handles; empty
            or ``["*"]`` means universal.
        requires: Capability tokens required from upstream.
        provides: Capability tokens emitted downstream.
        on_failure: Failure handling policy for this stage.
    """

    name: str
    version: str
    task: ComponentTask
    supported_languages: list[str]
    requires: list[str]
    provides: list[str]
    on_failure: FailureMode | None

    def run(self, input: Resource | Result) -> Result:
        """Execute the component's primary logic."""
        ...

    def degrade(self, input: Resource | Result) -> Result:
        """Execute a reduced-quality fallback. May raise NotImplementedError."""
        ...

    def can_handle(self, language: str) -> bool:
        """Return True if this component can handle the given language code."""
        ...


@runtime_checkable
class EvaluatorProtocol(ComponentProtocol, Protocol):
    """
    Structural contract for an evaluator component.

    Evaluators are components of task ``EVAL`` that accept hypothesis and
    reference results and return metrics in ``Result.metadata``. They satisfy
    :class:`ComponentProtocol` and additionally provide ``evaluate_pair``.
    """

    def evaluate_pair(self, hypothesis: Result, reference: Result) -> Result:
        """
        Evaluate a hypothesis Result against a reference Result.

        Args:
            hypothesis: Result produced by the system under test.
            reference: Gold-standard reference Result or Resource.

        Returns:
            Result carrying metrics in ``metadata`` (e.g. ``wer``, ``bleu``).
        """
        ...

    # Many evaluators also expose ``evaluate`` as alias; not required but allowed.
    # def evaluate(self, hypothesis: Result, reference: Result | None = None) -> Result: ...


@runtime_checkable
class RegistrableProtocol(Protocol):
    """
    Structural contract for any object that can be stored in the Registry.

    The Registry is heterogeneous (languages, resources, components, evaluators),
    so this protocol captures the minimal common surface: a versioned entity.
    Concrete registrable kinds may have additional fields (e.g. ``name`` for
    components, ``id`` for resources, ``code`` for languages) but all share
    ``version`` for provenance.

    Attributes:
        version: Version string for this registration (e.g. ``"1.0.0"``).
    """

    version: str
