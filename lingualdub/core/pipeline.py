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

from lingualdub.core.component import FailureMode
from lingualdub.core.protocols import ComponentProtocol
from lingualdub.types import LanguageCode, MetadataDict
from lingualdub.utils.validation import (
    require_non_empty_string,
    require_not_none,
    validate_language_code,
)


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
    metadata: MetadataDict = field(default_factory=dict)

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
        are provided by any upstream stage in the pipeline. Raises
        :class:`StageCompatibilityError` on mismatch.

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
                from lingualdub.exceptions import StageCompatibilityError

                raise StageCompatibilityError(
                    f"Pipeline compatibility error: stage {stage.name!r} "
                    f"requires {missing!r} but upstream provides {accumulated_provides!r}.",
                    upstream=str(accumulated_provides),
                    downstream=stage.name,
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
                    from lingualdub.exceptions import StageCompatibilityError

                    raise StageCompatibilityError(
                        f"Pipeline language error: stage {stage.name!r} supports {langs!r} "
                        f"but pipeline languages are {sorted(pipeline_langs)!r}. "
                        f"Use per_segment_language=True for code-switch routing or adjust stage languages.",
                        upstream=str(sorted(pipeline_langs)),
                        downstream=stage.name,
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
        The returned dict is a deep copy suitable for round-trip.
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
        Deserialize a Pipeline from a dictionary produced by :meth:`to_dict`.

        Validation mirrors core models — required keys are checked, types are
        validated, and unknown keys are preserved in ``metadata``.

        Args:
            data: Dictionary from to_dict().
            resolved_stages: Pre-resolved Component instances corresponding
                to the stage entries in data["stages"], in order. The caller
                is responsible for resolving stage names through the Registry.

        Returns:
            A live Pipeline object.

        Raises:
            SerializationError: If ``data`` is not a dict or required keys are
                missing / have wrong types.
        """
        from lingualdub.exceptions import SerializationError

        if not isinstance(data, dict):
            raise SerializationError(
                f"Pipeline.from_dict expects a dict, got {type(data).__name__}: {data!r}.",
                field="data",
                code="PIPE_DESER_001",
            )

        known_keys = {
            "source_language",
            "target_language",
            "per_segment_language",
            "on_stage_failure",
            "name",
            "description",
            "metadata",
            "stages",
        }

        # source_language is required; other fields have defaults for backward compat
        if "source_language" not in data:
            raise SerializationError(
                "Missing required field 'source_language' for Pipeline.",
                field="source_language",
                code="PIPE_DESER_002",
                context={"data_keys": list(data.keys())},
            )

        # Type checks for optional fields
        if (
            "target_language" in data
            and data["target_language"] is not None
            and not isinstance(data["target_language"], str)
        ):
            raise SerializationError(
                f"Field 'target_language' must be a string or None, got {type(data['target_language']).__name__}: {data['target_language']!r}.",
                field="target_language",
                code="PIPE_DESER_003",
            )
        if "per_segment_language" in data and not isinstance(data["per_segment_language"], bool):
            raise SerializationError(
                f"Field 'per_segment_language' must be a bool, got {type(data['per_segment_language']).__name__}: {data['per_segment_language']!r}.",
                field="per_segment_language",
                code="PIPE_DESER_003",
            )
        if "on_stage_failure" in data and data["on_stage_failure"] is not None:
            raw_fm = data["on_stage_failure"]
            if not isinstance(raw_fm, str):
                raise SerializationError(
                    f"Field 'on_stage_failure' must be a string, got {type(raw_fm).__name__}: {raw_fm!r}.",
                    field="on_stage_failure",
                    code="PIPE_DESER_003",
                )
            valid_fm = [e.value for e in FailureMode]
            if raw_fm not in valid_fm:
                raise SerializationError(
                    f"Field 'on_stage_failure' must be one of {valid_fm!r}, got {raw_fm!r}.",
                    field="on_stage_failure",
                    code="PIPE_DESER_003",
                )
        for key in ("name", "description"):
            if key in data and data[key] is not None and not isinstance(data[key], str):
                raise SerializationError(
                    f"Field '{key}' must be a string or None, got {type(data[key]).__name__}: {data[key]!r}.",
                    field=key,
                    code="PIPE_DESER_003",
                )
        if (
            "metadata" in data
            and data["metadata"] is not None
            and not isinstance(data["metadata"], dict)
        ):
            raise SerializationError(
                f"Field 'metadata' must be a dict, got {type(data['metadata']).__name__}: {data['metadata']!r}.",
                field="metadata",
                code="PIPE_DESER_003",
            )

        # Preserve unknown keys in metadata
        base_metadata = dict(data.get("metadata") or {})
        unknown = {k: v for k, v in data.items() if k not in known_keys}
        merged_metadata = {**base_metadata, **unknown} if unknown else base_metadata

        # Resolve on_stage_failure with default
        raw_fm_val = data.get("on_stage_failure", FailureMode.ABORT.value)
        failure_mode = FailureMode(raw_fm_val) if isinstance(raw_fm_val, str) else FailureMode.ABORT

        return cls(
            stages=resolved_stages,
            source_language=data["source_language"],
            target_language=data.get("target_language"),
            per_segment_language=bool(data.get("per_segment_language", False)),
            on_stage_failure=failure_mode,
            name=data.get("name"),
            description=data.get("description"),
            metadata=merged_metadata,
        )

    def __repr__(self) -> str:
        return (
            f"Pipeline(source={self.source_language!r}, "
            f"target={self.target_language!r}, "
            f"stages={self.stage_names})"
        )
