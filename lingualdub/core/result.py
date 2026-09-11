# mypy: disable-error-code="unreachable"
# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Result — the structured output of any pipeline stage.

Result carries content, segment-level data, processing status, warnings,
provenance, and artifact links. Status explicitly distinguishes complete,
partial, and degraded outputs so downstream consumers can act on result
quality rather than treating all outputs identically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from lingualdub.core.segment import Segment


class ResultStatus(str, Enum):
    """
    Processing status for a Result.

    COMPLETE  — all stages ran to full completion.
    PARTIAL   — one or more stages were skipped; output is incomplete.
    DEGRADED  — one or more stages ran their degraded path; output is reduced quality.
    FAILED    — a stage aborted and the result cannot be used.
    """

    COMPLETE = "complete"
    PARTIAL = "partial"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass(frozen=True)
class Result:
    """
    The structured output of a pipeline or component run.

    This is an **immutable value object** — all fields are validated at
    construction and the instance is frozen. To produce a modified copy use
    :meth:`replace`. Direct assignment (e.g. ``result.status = ...``) raises
    :class:`dataclasses.FrozenInstanceError`.

    Attributes:
        segments: Ordered list of :class:`Segment` objects produced by this run.
            Each segment carries timing, text, and per-segment language. The list
            itself is not deep-frozen (``list`` is mutable), but the Result
            contract is to treat it as immutable via :meth:`replace`.
        source_language: Source language code for this result (e.g. ``\"lug\"``).
            When set, validated as ISO 639-3. ``None`` is allowed for generic results.
        target_language: Target language code, if a translation stage was involved.
            When set, validated as ISO 639-3.
        status: Processing status of this result.

            * ``COMPLETE`` — all stages ran to full completion.
            * ``PARTIAL`` — one or more stages were skipped; output is incomplete
              (e.g. per-segment routing skipped unsupported languages).
            * ``DEGRADED`` — one or more stages ran their ``degrade()`` fallback;
              output is reduced quality.
            * ``FAILED`` — a stage aborted and the result cannot be used
              (``is_usable`` is ``False``).

            Transitions are **monotonic in severity**: ``COMPLETE`` may become
            ``PARTIAL``, ``DEGRADED``, or ``FAILED``; ``PARTIAL``/``DEGRADED``
            may become ``FAILED``; ``FAILED`` is terminal. Framework code moves
            ``COMPLETE→PARTIAL`` on ``SKIP``, ``COMPLETE/PARTIAL→DEGRADED`` on
            ``DEGRADE``, and any →``FAILED`` on ``ABORT``.

        warnings: Human-readable warnings recorded during processing.
            Each ``mark_*`` appends a prefixed warning (``\"Partial: ...\"``).
        provenance: Structured record linking this result to the pipeline config,
            component versions, dataset version, and run identifier that produced it.
            Used as a comparison key when evaluating across runs. Keys include
            ``run_id``, ``timestamp``, ``pipeline``, ``component_versions``,
            ``dataset_version``, and optional ``consent_basis``.
        artifacts: Paths or URIs of generated assets (audio, video, datasets)
            associated with this result.
        metadata: Extensible key-value store for component-specific output data
            (e.g. ``metrics``, ``asr_model``, ``timing_metrics``).
    """

    segments: list[Segment] = field(default_factory=list)
    source_language: str | None = None
    target_language: str | None = None
    status: ResultStatus = ResultStatus.COMPLETE
    warnings: list[str] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Validate language fields when present
        if self.source_language is not None:
            from lingualdub.utils.validation import require_non_empty_string, validate_language_code

            require_non_empty_string(self.source_language, "source_language")
            validate_language_code(self.source_language)
        if self.target_language is not None:
            from lingualdub.utils.validation import require_non_empty_string, validate_language_code

            require_non_empty_string(self.target_language, "target_language")
            validate_language_code(self.target_language)
        # Validate status is a valid enum
        if not isinstance(self.status, ResultStatus):  # type: ignore
            from lingualdub.exceptions import ConfigurationValidationError

            raise ConfigurationValidationError(
                f"Field 'status' must be a ResultStatus, got {type(self.status).__name__}: {self.status!r}.",
                field="status",
            )

    def replace(self, **changes) -> Result:
        """
        Return a new :class:`Result` with the given field changes.

        Args:
            **changes: Field names and new values. Unknown fields raise ``TypeError``.
                Invalid values (e.g. ``source_language=\"bad_code\"`` or
                ``status=\"invalid\"``) raise :class:`ConfigurationValidationError`.

        Returns:
            A new, validated :class:`Result` instance. The original is unchanged.

        Example:
            >>> r = Result(source_language=\"lug\")
            >>> r2 = r.replace(status=ResultStatus.FAILED, warnings=[*r.warnings, \"Failed: reason\"])
        """
        from dataclasses import replace as dc_replace

        valid_fields = set(self.__dataclass_fields__.keys())
        for k in changes:
            if k not in valid_fields:
                raise TypeError(f"Result.replace() got unexpected field {k!r}")

        # dataclasses.replace bypasses frozen __setattr__ via object.__setattr__
        new_obj = dc_replace(self, **changes)
        # Validate the new object (language codes, status etc.)
        # Use __post_init__ logic by calling it manually
        try:
            # Re-use same validation as __post_init__
            if new_obj.source_language is not None:
                from lingualdub.utils.validation import (
                    require_non_empty_string,
                    validate_language_code,
                )

                require_non_empty_string(new_obj.source_language, "source_language")
                validate_language_code(new_obj.source_language)
            if new_obj.target_language is not None:
                from lingualdub.utils.validation import (
                    require_non_empty_string,
                    validate_language_code,
                )

                require_non_empty_string(new_obj.target_language, "target_language")
                validate_language_code(new_obj.target_language)
            if not isinstance(new_obj.status, ResultStatus):  # type: ignore
                from lingualdub.exceptions import ConfigurationValidationError

                raise ConfigurationValidationError(
                    f"Field 'status' must be a ResultStatus, got {type(new_obj.status).__name__}: {new_obj.status!r}.",
                    field="status",
                )
        except Exception:
            raise

        return new_obj

    def add_warning(self, message: str) -> Result:
        """Return a new Result with an added warning (immutable)."""
        from lingualdub.utils.validation import require_non_empty_string

        require_non_empty_string(message, "message")
        return self.replace(warnings=[*self.warnings, message])

    def mark_partial(self, reason: str) -> Result:
        """Return a new Result marked as partial with a prefixed warning."""
        from lingualdub.utils.validation import require_non_empty_string

        require_non_empty_string(reason, "reason")
        return self.replace(
            status=ResultStatus.PARTIAL, warnings=[*self.warnings, f"Partial: {reason}"]
        )

    def mark_degraded(self, reason: str) -> Result:
        """Return a new Result marked as degraded with a prefixed warning."""
        from lingualdub.utils.validation import require_non_empty_string

        require_non_empty_string(reason, "reason")
        return self.replace(
            status=ResultStatus.DEGRADED, warnings=[*self.warnings, f"Degraded: {reason}"]
        )

    def mark_failed(self, reason: str) -> Result:
        """Return a new Result marked as failed with a prefixed warning."""
        from lingualdub.utils.validation import require_non_empty_string

        require_non_empty_string(reason, "reason")
        return self.replace(
            status=ResultStatus.FAILED, warnings=[*self.warnings, f"Failed: {reason}"]
        )

    @property
    def is_usable(self) -> bool:
        """Returns True if the result can be passed to downstream consumers."""
        return self.status != ResultStatus.FAILED

    def to_dict(self) -> dict:
        """Serialize this Result to a JSON-compatible dictionary."""
        return {
            "segments": [s.to_dict() for s in self.segments],
            "source_language": self.source_language,
            "target_language": self.target_language,
            "status": self.status.value,
            "warnings": list(self.warnings),
            "provenance": dict(self.provenance),
            "artifacts": list(self.artifacts),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Result:
        """Deserialize a Result from a dictionary produced by to_dict()."""
        from lingualdub.core.segment import Segment  # avoid circular at module level

        return cls(
            segments=[Segment.from_dict(s) for s in data.get("segments", [])],
            source_language=data.get("source_language"),
            target_language=data.get("target_language"),
            status=ResultStatus(data.get("status", ResultStatus.COMPLETE.value)),
            warnings=data.get("warnings", []),
            provenance=data.get("provenance", {}),
            artifacts=data.get("artifacts", []),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return (
            f"Result(status={self.status.value!r}, "
            f"segments={len(self.segments)}, "
            f"warnings={len(self.warnings)})"
        )
