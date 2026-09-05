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
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Union

from lingualdub.core.result import Result
from lingualdub.core.resource import Resource


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
    supported_languages: List[str] = []
    requires: List[str] = []
    provides: List[str] = []
    on_failure: Optional[FailureMode] = None

    @abstractmethod
    def run(self, input: Union[Result, Resource]) -> Result:
        """
        Execute the component's primary processing logic.

        Args:
            input: A Result from an upstream stage or a Resource to process.

        Returns:
            A Result carrying this component's output.
        """
        ...

    def degrade(self, input: Union[Result, Resource]) -> Result:
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
        raise NotImplementedError(
            f"Component {self.name!r} does not define a degrade() path."
        )

    def supports_language(self, language_code: str) -> bool:
        """Returns True if this component supports the given language code."""
        return not self.supported_languages or language_code in self.supported_languages

    def check_compatibility(self, upstream_provides: List[str]) -> List[str]:
        """
        Returns a list of missing capability tokens that this component requires
        but the upstream stage does not provide. An empty list means compatible.
        """
        return [cap for cap in self.requires if cap not in upstream_provides]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, version={self.version!r}, task={self.task.value!r})"
