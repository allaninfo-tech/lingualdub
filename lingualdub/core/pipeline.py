# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Pipeline abstraction.

A Pipeline composes an ordered sequence of Components into a reproducible
workflow. It manages inter-stage compatibility checking, per-segment language
routing for code-switch-aware execution, and stage failure handling.

Pipeline does not execute stages directly — that is delegated to the executor
in lingualdub.pipeline. This module defines the pipeline's structure and contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from lingualdub.core.component import FailureMode
from lingualdub.types import LanguageCode
from lingualdub.utils.validation import (
    require_non_empty_string,
    require_not_none,
    validate_language_code,
)

if TYPE_CHECKING:
    from lingualdub.core.protocols import ComponentProtocol


@dataclass
class Pipeline:
    """
    A composition of components forming a speech-processing workflow.

    Attributes:
        stages: Ordered list of Component instances forming the pipeline.
        source_language: Source language code for this pipeline.
        target_language: Target language code, if translation is involved.
        per_segment_language: When True, each Segment's language field is used
            to route that segment to the appropriate component independently,
            enabling code-switch-aware processing within a single run.
        on_stage_failure: Default failure mode applied to any stage that does
            not override it. Stages may declare their own on_failure value.
        name: Optional human-readable name for this pipeline.
        description: Optional description of this pipeline's purpose.
    """

    stages: list[ComponentProtocol]
    source_language: LanguageCode
    target_language: LanguageCode | None = None
    per_segment_language: bool = False
    on_stage_failure: FailureMode = FailureMode.ABORT
    name: str | None = None
    description: str | None = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_not_none(self.stages, "stages")
        if not self.stages:
            from lingualdub.exceptions import ConfigurationValidationError

            raise ConfigurationValidationError(
                "Pipeline must have at least one stage.", field="stages"
            )
        require_non_empty_string(self.source_language, "source_language")
        validate_language_code(self.source_language)
        if self.target_language is not None:
            require_non_empty_string(self.target_language, "target_language")
            validate_language_code(self.target_language)
        self._validate_stage_compatibility()

    def _validate_stage_compatibility(self) -> None:
        """
        Walk the stage list and verify that each stage's required capabilities
        are provided by any upstream stage in the pipeline. Raises ValueError
        on mismatch.

        Capabilities accumulate across stages: if Stage 1 provides "transcription"
        and Stage 2 provides "translation", Stage 3 can require either or both.
        This check runs at pipeline assembly time, not at execution time.
        """
        accumulated_provides: list[str] = []
        for stage in self.stages:
            # Support both classic Component (check_compatibility method) and
            # minimal Protocol duck types that only expose ``requires``.
            checker = getattr(stage, "check_compatibility", None)
            if callable(checker):
                missing = checker(accumulated_provides)  # type: ignore[operator]
            else:
                requires = getattr(stage, "requires", [])
                missing = [cap for cap in requires if cap not in accumulated_provides]
            if missing:
                raise ValueError(
                    f"Pipeline compatibility error: stage {stage.name!r} "
                    f"requires {missing!r} but upstream provides {accumulated_provides!r}."
                )
            # Accumulate this stage's capabilities for downstream stages.
            for cap in getattr(stage, "provides", []):
                if cap not in accumulated_provides:
                    accumulated_provides.append(cap)

        # Language compatibility check (assembly-time) — only for non-routing pipelines.
        # Per-segment pipelines deliberately allow stages that support a subset of languages.
        if not self.per_segment_language:
            for stage in self.stages:
                langs = getattr(stage, "supported_languages", [])
                if not langs or "*" in langs:
                    continue
                # Stage supports a specific set — pipeline languages should intersect
                pipeline_langs = {self.source_language}
                if self.target_language:
                    pipeline_langs.add(self.target_language)
                # Also include any metadata-declared pipeline languages?
                if not pipeline_langs.intersection(set(langs)):
                    raise ValueError(
                        f"Pipeline language error: stage {stage.name!r} supports {langs!r} "
                        f"but pipeline languages are {sorted(pipeline_langs)!r}. "
                        f"Use per_segment_language=True for code-switch routing or adjust stage languages."
                    )

    @property
    def stage_names(self) -> list[str]:
        """Returns the names of all stages in order."""
        return [s.name for s in self.stages]

    def to_dict(self) -> dict:
        """
        Serialize this Pipeline to a JSON-compatible dictionary.

        Note: stages are serialized as (name, version) pairs only. Full
        round-trip deserialization requires resolving component names through
        a Registry (see Pipeline.from_dict). No component logic is serialized.
        """
        return {
            "source_language": self.source_language,
            "target_language": self.target_language,
            "per_segment_language": self.per_segment_language,
            "on_stage_failure": self.on_stage_failure.value,
            "name": self.name,
            "description": self.description,
            "metadata": dict(self.metadata),
            "stages": [{"name": s.name, "version": s.version} for s in self.stages],
        }

    @classmethod
    def from_dict(cls, data: dict, resolved_stages: list[ComponentProtocol]) -> Pipeline:
        """
        Deserialize a Pipeline from a dictionary produced by to_dict().

        Args:
            data: Dictionary from to_dict().
            resolved_stages: Pre-resolved Component instances corresponding
                to the stage entries in data["stages"], in order. The caller
                is responsible for resolving stage names through the Registry.

        Returns:
            A live Pipeline object.
        """
        return cls(
            stages=resolved_stages,
            source_language=data["source_language"],
            target_language=data.get("target_language"),
            per_segment_language=data.get("per_segment_language", False),
            on_stage_failure=FailureMode(data.get("on_stage_failure", FailureMode.ABORT.value)),
            name=data.get("name"),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return (
            f"Pipeline(source={self.source_language!r}, "
            f"target={self.target_language!r}, "
            f"stages={self.stage_names})"
        )
