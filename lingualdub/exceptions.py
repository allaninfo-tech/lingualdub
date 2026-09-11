# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Centralized exception hierarchy for the LingualDub framework.

All framework exceptions are subclasses of ``LingualDubError``.  Callers can
catch at any level of the hierarchy:

    except LingualDubError:        # any framework error
    except ConfigurationError:     # any config / validation problem
    except PipelineError:          # any pipeline execution problem
    ...

Every exception carries three attributes:

* ``message`` – human-readable description (also the ``str()`` of the
  exception).
* ``code`` – optional machine-readable identifier, e.g.
  ``"STAGE_COMPAT_001"``.  ``None`` when not specified.
* ``context`` – optional ``dict`` of structured details for logging /
  monitoring.  Empty dict when not specified.

Hierarchy
---------
::

    LingualDubError
    ├── ConfigurationError
    │   └── ConfigurationValidationError
    ├── LifecycleError
    │   ├── InitializationError
    │   └── ShutdownError
    ├── PipelineError
    │   ├── StageCompatibilityError
    │   └── StageExecutionError
    ├── RegistryError
    │   ├── RegistrationConflictError
    │   └── ResolutionError
    ├── ComponentError
    │   └── ComponentContractError
    ├── ResourceError
    │   ├── ResourceNotFoundError
    │   ├── ResourceLoadError
    │   └── ConsentViolationError
    └── InternalError
"""

from __future__ import annotations

__all__: list[str] = [
    # Base
    "LingualDubError",
    # Configuration
    "ConfigurationError",
    "ConfigurationValidationError",
    # Lifecycle
    "LifecycleError",
    "InitializationError",
    "ShutdownError",
    # Pipeline
    "PipelineError",
    "StageCompatibilityError",
    "StageExecutionError",
    # Registry
    "RegistryError",
    "RegistrationConflictError",
    "ResolutionError",
    # Component
    "ComponentError",
    "ComponentContractError",
    # Resource
    "ResourceError",
    "ResourceNotFoundError",
    "ResourceLoadError",
    "ConsentViolationError",
    # Internal
    "InternalError",
]


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class LingualDubError(Exception):
    """Base class for all LingualDub framework exceptions.

    Args:
        message: Human-readable description of the error.
        code: Optional machine-readable identifier (e.g. ``"STAGE_COMPAT_001"``).
        context: Optional dict of structured details for logging / monitoring.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.code: str | None = code
        self.context: dict[str, object] = context or {}

    def __repr__(self) -> str:
        parts = [f"{type(self).__name__}({self.message!r}"]
        if self.code:
            parts.append(f", code={self.code!r}")
        if self.context:
            parts.append(f", context={self.context!r}")
        return "".join(parts) + ")"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class ConfigurationError(LingualDubError):
    """Raised for any configuration-related problem.

    Use the more-specific ``ConfigurationValidationError`` when a field value
    fails validation.
    """


class ConfigurationValidationError(ConfigurationError):
    """Raised when a configuration field value fails validation.

    Args:
        message: Human-readable description, ideally naming the field and
            the constraint violated.
        field: Optional field name that failed validation.
        code: Optional machine-readable code.
        context: Optional structured details.
    """

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        code: str | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        ctx: dict[str, object] = dict(context or {})
        if field is not None:
            ctx["field"] = field
        super().__init__(message, code=code, context=ctx)
        self.field: str | None = field


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class LifecycleError(LingualDubError):
    """Raised for illegal lifecycle state transitions or lifecycle violations."""


class InitializationError(LifecycleError):
    """Raised when the framework or a component fails to initialize.

    Args:
        message: Human-readable description.
        component: Optional name of the component that failed.
        code: Optional machine-readable code.
        context: Optional structured details.
    """

    def __init__(
        self,
        message: str,
        *,
        component: str | None = None,
        code: str | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        ctx: dict[str, object] = dict(context or {})
        if component is not None:
            ctx["component"] = component
        super().__init__(message, code=code, context=ctx)
        self.component: str | None = component


class ShutdownError(LifecycleError):
    """Raised when a shutdown hook fails.

    Unlike ``InitializationError``, shutdown errors are typically logged
    and non-fatal — teardown continues past a failing hook.
    """


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class PipelineError(LingualDubError):
    """Raised for any pipeline-level error."""


class StageCompatibilityError(PipelineError):
    """Raised when two consecutive pipeline stages are incompatible.

    For example, when a stage that provides ``\"text\"`` is followed by one
    that requires ``\"audio\"``.

    Args:
        message: Human-readable description.
        upstream: Name of the upstream (providing) stage.
        downstream: Name of the downstream (requiring) stage.
        code: Optional machine-readable code.
        context: Optional structured details.
    """

    def __init__(
        self,
        message: str,
        *,
        upstream: str | None = None,
        downstream: str | None = None,
        code: str | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        ctx: dict[str, object] = dict(context or {})
        if upstream is not None:
            ctx["upstream"] = upstream
        if downstream is not None:
            ctx["downstream"] = downstream
        super().__init__(message, code=code, context=ctx)
        self.upstream: str | None = upstream
        self.downstream: str | None = downstream


class StageExecutionError(PipelineError):
    """Raised when a pipeline stage raises under ``ABORT`` failure mode.

    Args:
        message: Human-readable description.
        stage: Name of the failing stage.
        code: Optional machine-readable code.
        context: Optional structured details.
    """

    def __init__(
        self,
        message: str,
        *,
        stage: str | None = None,
        code: str | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        ctx: dict[str, object] = dict(context or {})
        if stage is not None:
            ctx["stage"] = stage
        super().__init__(message, code=code, context=ctx)
        self.stage: str | None = stage


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class RegistryError(LingualDubError):
    """Raised for any registry-level error."""


class RegistrationConflictError(RegistryError):
    """Raised when a duplicate (kind, key) registration is attempted and
    the conflict policy does not allow it.

    Args:
        message: Human-readable description.
        kind: The registration kind (e.g. ``\"component\"``).
        key: The registration key (e.g. ``\"my_asr\"``).
        code: Optional machine-readable code.
        context: Optional structured details.
    """

    def __init__(
        self,
        message: str,
        *,
        kind: str | None = None,
        key: str | None = None,
        code: str | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        ctx: dict[str, object] = dict(context or {})
        if kind is not None:
            ctx["kind"] = kind
        if key is not None:
            ctx["key"] = key
        super().__init__(message, code=code, context=ctx)
        self.kind: str | None = kind
        self.key: str | None = key


class ResolutionError(RegistryError):
    """Raised when a registry lookup fails to find a matching entry.

    Args:
        message: Human-readable description.
        kind: The registration kind queried.
        key: The registration key queried.
        code: Optional machine-readable code.
        context: Optional structured details.
    """

    def __init__(
        self,
        message: str,
        *,
        kind: str | None = None,
        key: str | None = None,
        code: str | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        ctx: dict[str, object] = dict(context or {})
        if kind is not None:
            ctx["kind"] = kind
        if key is not None:
            ctx["key"] = key
        super().__init__(message, code=code, context=ctx)
        self.kind: str | None = kind
        self.key: str | None = key


# ---------------------------------------------------------------------------
# Component
# ---------------------------------------------------------------------------


class ComponentError(LingualDubError):
    """Raised for component-level failures."""


class ComponentContractError(ComponentError):
    """Raised when a component violates the framework component contract.

    For example, when a component returns an object that is not a ``Result``,
    or when provenance metadata is inconsistent.

    Args:
        message: Human-readable description.
        component: Name of the offending component.
        code: Optional machine-readable code.
        context: Optional structured details.
    """

    def __init__(
        self,
        message: str,
        *,
        component: str | None = None,
        code: str | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        ctx: dict[str, object] = dict(context or {})
        if component is not None:
            ctx["component"] = component
        super().__init__(message, code=code, context=ctx)
        self.component: str | None = component


# ---------------------------------------------------------------------------
# Resource
# ---------------------------------------------------------------------------


class ResourceError(LingualDubError):
    """Raised for resource-level failures."""


class ResourceNotFoundError(ResourceError):
    """Raised when a required resource cannot be found on disk or in the
    registry.

    Args:
        message: Human-readable description.
        resource_id: Optional identifier of the missing resource.
        code: Optional machine-readable code.
        context: Optional structured details.
    """

    def __init__(
        self,
        message: str,
        *,
        resource_id: str | None = None,
        code: str | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        ctx: dict[str, object] = dict(context or {})
        if resource_id is not None:
            ctx["resource_id"] = resource_id
        super().__init__(message, code=code, context=ctx)
        self.resource_id: str | None = resource_id


class ResourceLoadError(ResourceError):
    """Raised when a resource exists but cannot be loaded or verified.

    Typical causes: checksum mismatch, corrupt file, unsupported format.

    Args:
        message: Human-readable description.
        resource_id: Optional identifier of the resource that failed to load.
        code: Optional machine-readable code.
        context: Optional structured details.
    """

    def __init__(
        self,
        message: str,
        *,
        resource_id: str | None = None,
        code: str | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        ctx: dict[str, object] = dict(context or {})
        if resource_id is not None:
            ctx["resource_id"] = resource_id
        super().__init__(message, code=code, context=ctx)
        self.resource_id: str | None = resource_id


class ConsentViolationError(ResourceError):
    """Raised when an operation on a resource violates the user's consent
    settings.

    Args:
        message: Human-readable description.
        resource_id: Optional identifier of the resource.
        code: Optional machine-readable code.
        context: Optional structured details.
    """

    def __init__(
        self,
        message: str,
        *,
        resource_id: str | None = None,
        code: str | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        ctx: dict[str, object] = dict(context or {})
        if resource_id is not None:
            ctx["resource_id"] = resource_id
        super().__init__(message, code=code, context=ctx)
        self.resource_id: str | None = resource_id


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


class InternalError(LingualDubError):
    """Raised when the framework reaches an internally inconsistent state.

    This should never be raised in normal operation.  If it is, it indicates
    a bug in the framework itself, not in the caller's code.
    """
