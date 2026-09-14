# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Dependency injection contracts — formal dependency descriptors and lifetimes.

This module is purely declarative: it defines **what** a dependency is, not
how it is resolved.  No resolution or registration logic lives here.

Lifetime semantics
------------------
* ``SINGLETON`` — constructed once per :class:`DependencyContainer`, cached,
  and reused for every ``resolve()``. Created lazily on first resolve.
* ``SCOPED`` — singleton within a :class:`DependencyScope` (per-pipeline-run,
  per-request, etc.). Each ``create_scope()`` yields a new instance; within
  the same scope ``resolve()`` returns the identical object. On scope exit
  ``close()`` is called if present.
* ``TRANSIENT`` — a fresh instance is constructed on every ``resolve()``,
  never cached.

Dependency declaration
----------------------
A dependency is declared either via annotation or as a field descriptor::

    from lingualdub.di import Dependency

    # annotation form
    class MyService:
        registry: Dependency[Registry]

    # descriptor form
    class MyService:
        registry = Dependency[Registry]  # marker

    # explicit descriptor with lifetime/default
    class MyService:
        cache = Dependency(lifetime=Lifetime.SCOPED)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Any, Generic, TypeVar

__all__ = [
    "Lifetime",
    "DependencyDescriptor",
    "Dependency",
    "_MISSING",
]


# Sentinel for "no default supplied" — distinct from ``None``.
_MISSING: Any = object()


class Lifetime(str, Enum):
    """Lifecycle of a resolved dependency.

    Attributes:
        SINGLETON: One shared instance per container.
        SCOPED: One instance per scope, new per ``create_scope()``.
        TRANSIENT: New instance on every resolve.
    """

    SINGLETON = "singleton"
    SCOPED = "scoped"
    TRANSIENT = "transient"


@dataclass
class DependencyDescriptor:
    """Declarative description of a single dependency.

    Attributes:
        name: Registered name in the container (e.g. ``"registry"``).
        type_hint: Optional type hint for the dependency (e.g. ``Registry``).
        lifetime: Lifetime of the constructed instance.
        default: Fallback value if the dependency is not registered. ``_MISSING``
            means no default — resolution must succeed or raise.

    Example:
        DependencyDescriptor(
            name="registry",
            type_hint=Registry,
            lifetime=Lifetime.SINGLETON,
        )
    """

    name: str
    type_hint: Any = None
    lifetime: Lifetime = Lifetime.SINGLETON
    default: Any = field(default=_MISSING)

    def __post_init__(self) -> None:
        # Use local import to avoid circular dependency with validation utils
        # but keep error hierarchy consistent (ConfigurationValidationError for
        # bad names is reserved for validation layer; here we raise ValueError
        # for descriptor misuse and let container raise LingualDubError).
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError(  # justified: descriptor misuse — invalid descriptor field, not a config/lifecycle domain error
                f"DependencyDescriptor name must be a non-empty string, got {self.name!r}."
            )
        if not isinstance(self.lifetime, Lifetime):
            raise ValueError(  # justified: descriptor misuse — invalid enum, not a framework config error
                f"DependencyDescriptor lifetime must be a Lifetime, got {type(self.lifetime).__name__}: {self.lifetime!r}."
            )


_T = TypeVar("_T")


class Dependency(Generic[_T]):
    """Descriptor / annotation marker for injectable fields.

    Supports three equivalent forms::

        class S:
            # 1. Annotation with generic — inspected via ``get_type_hints``:
            reg: Dependency[Registry]

        # 2. Direct assignment of marker:
            reg = Dependency[Registry]

        # 3. Explicit descriptor with lifetime/default:
            reg = Dependency(lifetime=Lifetime.SCOPED)
            cache = Dependency(default=None)

    The descriptor itself does not perform injection; that is the
    responsibility of :class:`DependencyContainer` which inspects either
    ``__annotations__`` or descriptor instances on the class.

    The ``__class_getitem__`` implementation enables ``Dependency[X]`` syntax
    by returning an :class:`typing.Annotated` alias carrying the marker as
    metadata.  This allows type checkers to preserve ``X`` while the runtime
    can detect ``Dependency`` usage via ``include_extras=True``.

    Attributes:
        type_hint: The declared type for this dependency.
        lifetime: Lifetime override for this field.
        default: Default value if unset.
        name: Attribute name set via ``__set_name__``.
    """

    # Allow ``isinstance(obj, Dependency)`` checks if ever needed
    # (not runtime_checkable via Protocol, but simple class is fine).

    def __init__(
        self,
        type_hint: Any | None = None,
        *,
        lifetime: Lifetime = Lifetime.SINGLETON,
        default: Any = _MISSING,
    ) -> None:
        self.type_hint: Any | None = type_hint
        self.lifetime: Lifetime = lifetime
        self.default: Any = default
        self.name: str = ""
        self._is_marker: bool = True

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __get__(self, instance: object | None, owner: type | None = None) -> Any:
        # When accessed via class, return the descriptor itself for introspection.
        if instance is None:
            return self
        # Instance access would normally be intercepted by the container's
        # field-injection logic; if no injection has occurred, expose the
        # descriptor or default.
        if self.default is not _MISSING:
            return self.default
        return None

    def __set__(self, instance: object, value: Any) -> None:
        # Allow direct assignment to override the descriptor value on the instance
        # (e.g. test overrides).
        instance.__dict__[self.name] = value

    def __repr__(self) -> str:
        return f"Dependency(name={self.name!r}, type_hint={self.type_hint!r}, lifetime={self.lifetime.value!r})"

    # Generic alias support — ``Dependency[SomeService]`` → ``Annotated[SomeService, Dependency(...)]``
    @classmethod
    def __class_getitem__(cls, item: Any) -> Any:
        # Preserve ``item`` as the type hint inside an Annotated marker.
        # The marker carries the type for later inspection.
        marker = cls(type_hint=item)
        # ``Annotated[Target, metadata]`` — metadata is the Dependency marker.
        # Type checkers will see ``Annotated[item, marker]``; runtime can
        # introspect via ``get_type_hints(..., include_extras=True)``.
        return Annotated[item, marker]  # type: ignore[return-value]

    # For backwards compatibility, allow calling as function-like
    # ``Dependency(SomeService)`` — though ``Dependency[SomeService]`` is preferred.
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # If used as ``dep = Dependency(SomeService)()`` — not intended,
        # but allow calling to construct an instance if type_hint is a class.
        if self.type_hint is not None and callable(self.type_hint):
            try:
                return self.type_hint(*args, **kwargs)
            except Exception:
                pass
        return None
