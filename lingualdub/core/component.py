# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Component abstraction.

A Component is the primary extension point of the framework. Each component
declares what capabilities it requires from upstream stages and what it
provides to downstream stages. This allows the framework to catch incompatible
pipeline compositions at assembly time rather than at runtime.

Components also declare an optional degraded execution path, enabling
pipelines to produce partial results instead of failing completely when
a stage cannot run to full completion.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from lingualdub.core.resource import Resource
from lingualdub.core.result import Result
from lingualdub.types import LanguageCode


class ComponentTask(str, Enum):
    """The processing task a component performs."""

    ASR = "asr"
    TRANSLATION = "translation"
    TTS = "tts"
    ALIGNMENT = "alignment"
    SPEAKER = "speaker"
    CODE_SWITCH = "code_switch"
    ADAPTATION = "adaptation"
    EVAL = "eval"
    PREPROCESSING = "preprocessing"
    VIDEO = "video"
    OTHER = "other"


class FailureMode(str, Enum):
    """
    How a pipeline should respond when this component fails.

    ABORT   — stop the pipeline and surface the error.
    SKIP    — omit this stage's contribution and mark the result as partial.
    DEGRADE — call the component's degrade() path if defined; mark as degraded.
    """

    ABORT = "abort"
    SKIP = "skip"
    DEGRADE = "degrade"


class Component(ABC):
    """
    Abstract base class for all LingualDub processing components.

    Subclasses must implement `run()` and may optionally implement `degrade()`
    to define a graceful fallback path.

    Attributes:
        name: Unique name for this component implementation.
        version: Version string for this component.
        task: The processing task this component performs.
        supported_languages: Language codes this component supports.
        requires: Capability tokens this component expects from upstream output.
        provides: Capability tokens this component emits in its output.
        on_failure: Default failure mode when this component cannot run.
    """

    name: str
    version: str
    task: ComponentTask
    supported_languages: list[LanguageCode] = []  # type: ignore[assignment]
    requires: list[str] = []  # type: ignore[assignment]
    provides: list[str] = []  # type: ignore[assignment]
    on_failure: FailureMode | None = None

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        orig_init = cls.__init__

        # Avoid double-wrapping
        if getattr(orig_init, "_lingualdub_wrapped", False):
            return

        def _wrapped_init(self, *args, **kw):  # type: ignore[no-untyped-def]
            # Ensure per-instance copies of mutable class-level lists to avoid
            # shared-state bugs (appending on one instance polluting another).
            for attr in ("supported_languages", "requires", "provides"):
                val = getattr(self.__class__, attr, None)
                if isinstance(val, list):
                    # Only copy if instance hasn't already shadowed it
                    if attr not in self.__dict__:
                        object.__setattr__(self, attr, list(val))
            # Call original __init__ (which will eventually hit Component.__init__)
            orig_init(self, *args, **kw)
            # If subclass didn't call super().__init__, enforce contract validation here.
            # Component.__init__ validates name/version; we ensure it ran.
            if not getattr(self, "_lingualdub_validated", False):
                from lingualdub.utils.validation import (
                    require_non_empty_string,
                    validate_version_string,
                )

                if self.__class__ is not Component:
                    require_non_empty_string(getattr(self, "name", None), "name")
                    require_non_empty_string(getattr(self, "version", None), "version")
                    validate_version_string(getattr(self, "version", None))
                    # Validate task type
                    if not isinstance(getattr(self, "task", None), ComponentTask):
                        from lingualdub.exceptions import ConfigurationValidationError

                        raise ConfigurationValidationError(
                            f"Field 'task' must be a ComponentTask, got {type(getattr(self, 'task', None)).__name__}: {getattr(self, 'task', None)!r}.",
                            field="task",
                        )
                    # Validate list fields are actually lists of strings
                    for list_field in ("supported_languages", "requires", "provides"):
                        v = getattr(self, list_field, None)
                        if not isinstance(v, list):
                            from lingualdub.exceptions import ConfigurationValidationError

                            raise ConfigurationValidationError(
                                f"Field {list_field!r} must be a list, got {type(v).__name__}: {v!r}.",
                                field=list_field,
                            )
                        for i, item in enumerate(v):
                            if not isinstance(item, str):
                                from lingualdub.exceptions import ConfigurationValidationError

                                raise ConfigurationValidationError(
                                    f"Field {list_field!r}[{i}] must be a string, got {type(item).__name__}: {item!r}.",
                                    field=f"{list_field}[{i}]",
                                )
                    # Validate on_failure
                    of = getattr(self, "on_failure", None)
                    if of is not None and not isinstance(of, FailureMode):
                        from lingualdub.exceptions import ConfigurationValidationError

                        raise ConfigurationValidationError(
                            f"Field 'on_failure' must be a FailureMode or None, got {type(of).__name__}: {of!r}.",
                            field="on_failure",
                        )
                object.__setattr__(self, "_lingualdub_validated", True)

        _wrapped_init._lingualdub_wrapped = True  # type: ignore[attr-defined]
        cls.__init__ = _wrapped_init  # type: ignore[method-assign]

    def __init__(self, *args, **kwargs) -> None:
        # Centralised contract validation for every component instance.
        from lingualdub.utils.validation import require_non_empty_string, validate_version_string

        # Ensure per-instance copies even when Component.__init__ is called directly
        for attr in ("supported_languages", "requires", "provides"):
            if attr not in self.__dict__:
                class_val = getattr(self.__class__, attr, None)
                if isinstance(class_val, list):
                    object.__setattr__(self, attr, list(class_val))

        # Only validate concrete subclasses, not the abstract base itself
        if self.__class__ is not Component:
            # name / version are required contract fields
            require_non_empty_string(getattr(self, "name", None), "name")
            require_non_empty_string(getattr(self, "version", None), "version")
            validate_version_string(getattr(self, "version", None))
            object.__setattr__(self, "_lingualdub_validated", True)

    @abstractmethod
    def run(self, input: Result | Resource) -> Result:
        """
        Execute the component's primary processing logic.

        Args:
            input: A Result from an upstream stage or a Resource to process.

        Returns:
            A Result carrying this component's output.
        """
        ...

    def degrade(self, input: Result | Resource) -> Result:
        """
        Execute a reduced-quality fallback when full processing cannot complete.

        Override this method to define a graceful degradation path.
        The default implementation raises NotImplementedError, which causes
        the pipeline to treat DEGRADE mode the same as ABORT for this component.

        Args:
            input: The same input passed to run().

        Returns:
            A Result with status DEGRADED.
        """
        raise NotImplementedError(f"Component {self.name!r} does not define a degrade() path.")

    def supports_language(self, language_code: LanguageCode) -> bool:
        """Returns True if this component supports the given language code."""
        langs = getattr(self, "supported_languages", [])
        if not langs:
            return True
        if "*" in langs:
            return True
        return language_code in langs

    def can_handle(self, language: LanguageCode) -> bool:
        """Return True if this component can handle the given language code.

        Structural alias for :meth:`supports_language` to satisfy
        :class:`lingualdub.core.protocols.ComponentProtocol` without breaking
        existing callers that use ``supports_language``.
        """
        return self.supports_language(language)

    def check_compatibility(self, upstream_provides: list[str]) -> list[str]:
        """
        Returns a list of missing capability tokens that this component requires
        but the upstream stage does not provide. An empty list means compatible.
        """
        return [cap for cap in self.requires if cap not in upstream_provides]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, version={self.version!r}, task={self.task.value!r})"
