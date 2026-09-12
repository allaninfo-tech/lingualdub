# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Extension point contracts — stable protocols for third-party extensions.

This module defines the formal extension points the framework provides.
It intentionally imports **nothing** from internal framework modules
(``lingualdub.core``, ``lingualdub.pipeline``, etc.) so third-party
packages can implement these protocols without importing framework internals.

Each protocol declares its required fields/methods and a stability level:

* ``stable`` — guaranteed not to break within a major version.
* ``experimental`` — may change; use with caution.

Third-party usage::

    from lingualdub.extensions.contracts import ComponentExtension

    class MyComponent:
        name = "my_asr"
        version = "1.0.0"
        task = "asr"
        supported_languages = ["lug"]
        requires = []
        provides = ["transcription"]
        on_failure = "abort"
        __stability__ = "stable"

        def run(self, inp): ...
        def degrade(self, inp): ...
        def can_handle(self, language: str) -> bool: ...

    assert isinstance(MyComponent(), ComponentExtension)
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

__all__ = [
    "ComponentExtension",
    "LanguageExtension",
    "ResourceExtension",
    "EvaluatorExtension",
    "MiddlewareExtension",
]


@runtime_checkable
class ComponentExtension(Protocol):
    """Protocol for pipeline stage components — ``stable``.

    Mirrors the public :class:`lingualdub.core.protocols.ComponentProtocol`
    but is defined here without internal imports so external packages remain
    decoupled.
    """

    name: str
    version: str
    task: str
    supported_languages: list[str]
    requires: list[str]
    provides: list[str]
    on_failure: str | None

    def run(self, inp: Any) -> Any:
        """Execute primary logic; must return a Result-like object."""
        ...

    def degrade(self, inp: Any) -> Any:
        """Reduced-quality fallback; may raise ``NotImplementedError``."""
        ...

    def can_handle(self, language: str) -> bool:
        """Return ``True`` if this component handles ``language``."""
        ...


ComponentExtension.__stability__ = "stable"  # type: ignore[attr-defined]


@runtime_checkable
class LanguageExtension(Protocol):
    """Protocol for language profile extensions — ``stable``.

    Language extensions register new ``Language`` profiles.  The minimal
    contract matches :class:`lingualdub.core.language.Language` fields.
    """

    code: str
    name: str
    family: str
    resource_profile: str
    supported_tasks: list[str]
    related_languages: list[str]
    resources: list[str]
    compatible_components: list[str]
    metadata: dict[str, Any]


LanguageExtension.__stability__ = "stable"  # type: ignore[attr-defined]


@runtime_checkable
class ResourceExtension(Protocol):
    """Protocol for resource type extensions — ``stable``.

    Resources are data assets (speech, text, checkpoints, etc.).  This
    protocol mirrors :class:`lingualdub.core.resource.Resource` without
    importing it.
    """

    id: str
    kind: str
    language: str
    version: str
    provenance: dict[str, Any]
    quality_flags: list[str]
    compatible_components: list[str]
    path: Any
    metadata: dict[str, Any]


ResourceExtension.__stability__ = "stable"  # type: ignore[attr-defined]


@runtime_checkable
class EvaluatorExtension(Protocol):
    """Protocol for custom evaluation strategies — ``experimental``.

    Evaluators are ``ComponentExtension`` of task ``eval`` plus an
    ``evaluate_pair`` method for hypothesis/reference comparison.
    """

    name: str
    version: str
    task: str
    supported_languages: list[str]
    requires: list[str]
    provides: list[str]
    on_failure: str | None

    def run(self, inp: Any) -> Any: ...

    def degrade(self, inp: Any) -> Any: ...

    def can_handle(self, language: str) -> bool: ...

    def evaluate_pair(self, hypothesis: Any, reference: Any) -> Any:
        """Evaluate hypothesis against reference; return Result-like with metrics."""
        ...


EvaluatorExtension.__stability__ = "experimental"  # type: ignore[attr-defined]


@runtime_checkable
class MiddlewareExtension(Protocol):
    """Protocol for cross-cutting middleware — ``experimental``.

    Middleware wraps pipeline execution with ``before``/``after``/``on_error``
    hooks and is ordered by ``priority`` (lower = outermost).
    """

    name: str
    priority: int

    def before(self, context: Any) -> Any:
        """Pre-execution hook; may short-circuit by returning a Result."""
        ...

    def after(self, context: Any, result: Any) -> Any:
        """Post-execution hook; may transform the result."""
        ...

    def on_error(self, context: Any, error: Exception) -> Any | None:
        """Error hook; return a Result to recover or ``None`` to propagate."""
        ...


MiddlewareExtension.__stability__ = "experimental"  # type: ignore[attr-defined]
