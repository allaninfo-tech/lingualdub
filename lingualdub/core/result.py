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
from lingualdub.types import LanguageCode, MetadataDict, ProvenanceDict


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
    source_language: LanguageCode | None = None
    target_language: LanguageCode | None = None
    status: ResultStatus = ResultStatus.COMPLETE
    warnings: list[str] = field(default_factory=list)
    provenance: ProvenanceDict = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    metadata: MetadataDict = field(default_factory=dict)

    _SEVERITY = {
        ResultStatus.COMPLETE: 0,
        ResultStatus.PARTIAL: 1,
        ResultStatus.DEGRADED: 2,
        ResultStatus.FAILED: 3,
    }

    def __post_init__(self) -> None:
        # Validate language fields when present
        if self.source_language is not None:
            from lingualdub.utils.validation import require_non_empty_string, validate_language_code

            require_non_empty_string(self.source_language, "source_language")
            validate_language_code(self.source_language, "source_language")
        if self.target_language is not None:
            from lingualdub.utils.validation import require_non_empty_string, validate_language_code

            require_non_empty_string(self.target_language, "target_language")
            validate_language_code(self.target_language, "target_language")
        # Validate status is a valid enum
        if not isinstance(self.status, ResultStatus):  # type: ignore
            from lingualdub.exceptions import ConfigurationValidationError

            raise ConfigurationValidationError(
                f"Field 'status' must be a ResultStatus, got {type(self.status).__name__}: {self.status!r}.",
                field="status",
            )
        # Validate list/tuple fields and break external references (tuple after hardening)
        for key in ("segments", "warnings", "artifacts"):
            val = getattr(self, key)
            if not isinstance(val, (list, tuple)):
                from lingualdub.exceptions import ConfigurationValidationError

                raise ConfigurationValidationError(
                    f"Field {key!r} must be a list, got {type(val).__name__}: {val!r}.", field=key
                )
        if not isinstance(self.provenance, dict):
            from lingualdub.exceptions import ConfigurationValidationError

            raise ConfigurationValidationError(
                f"Field 'provenance' must be a dict, got {type(self.provenance).__name__}: {self.provenance!r}.",
                field="provenance",
            )
        if not isinstance(self.metadata, dict):
            from lingualdub.exceptions import ConfigurationValidationError

            raise ConfigurationValidationError(
                f"Field 'metadata' must be a dict, got {type(self.metadata).__name__}: {self.metadata!r}.",
                field="metadata",
            )
        # Security limits (PRO-004)
        from lingualdub.utils.validation import validate_metadata_depth

        validate_metadata_depth(self.provenance, field_name="provenance")
        validate_metadata_depth(self.metadata, field_name="metadata")
        # Break external mutable references and harden segments as tuple
        # (``result.segments.append`` now raises). Warnings/artifacts kept as
        # list for backward compat with component ``res.artifacts.append`` patterns;
        # full tuple hardening deferred to avoid breaking existing adapters.
        object.__setattr__(self, "segments", tuple(self.segments))
        object.__setattr__(self, "warnings", list(self.warnings))
        object.__setattr__(self, "artifacts", list(self.artifacts))
        object.__setattr__(self, "provenance", dict(self.provenance))
        object.__setattr__(self, "metadata", dict(self.metadata))
        # Validate segments are Segment instances
        for i, s in enumerate(self.segments):
            if not isinstance(s, Segment):
                from lingualdub.exceptions import ConfigurationValidationError

                raise ConfigurationValidationError(
                    f"Field segments[{i}] must be a Segment, got {type(s).__name__}: {s!r}.",
                    field=f"segments[{i}]",
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
                raise TypeError(  # justified: Python type contract for unexpected replace field
                    f"Result.replace() got unexpected field {k!r}"
                )

        # dataclasses.replace bypasses frozen __setattr__ via object.__setattr__
        new_obj = dc_replace(self, **changes)
        # Enforce monotonic severity: COMPLETE(0) < PARTIAL(1) < DEGRADED(2) < FAILED(3)
        # Status may only stay or increase in severity; regression is a contract violation.
        if "status" in changes:
            old_sev = self._SEVERITY[self.status]
            new_sev = self._SEVERITY[new_obj.status]  # type: ignore[attr-defined]
            if new_sev < old_sev:
                from lingualdub.exceptions import ConfigurationValidationError

                raise ConfigurationValidationError(
                    f"Result status cannot regress from {self.status.value!r} to {new_obj.status.value!r} (severity {old_sev} -> {new_sev}).",
                    field="status",
                )
        try:
            new_obj.__post_init__()  # type: ignore[attr-defined]
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
        """Serialize this Result to a JSON-compatible dictionary.

        The returned dictionary is a deep copy suitable for JSON serialization
        and round-trip via :meth:`from_dict`.
        """
        import copy

        return {
            "segments": [s.to_dict() for s in self.segments],
            "source_language": self.source_language,
            "target_language": self.target_language,
            "status": self.status.value,
            "warnings": list(self.warnings),
            "provenance": copy.deepcopy(self.provenance),
            "artifacts": list(self.artifacts),
            "metadata": copy.deepcopy(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Result:
        """Deserialize a Result from a dictionary produced by :meth:`to_dict`.

        Validation mirrors :meth:`Segment.from_dict` — explicit type checks,
        descriptive ``SerializationError`` for schema violations, and
        forward-compatible preservation of unknown keys in ``metadata``.

        All fields are optional except ``segments`` (defaults to ``[]``) and
        ``status`` (defaults to ``COMPLETE`` when missing).

        Raises:
            SerializationError: If ``data`` is not a dict, a field has the wrong
                type, or ``status`` is not a valid :class:`ResultStatus` value,
                or any contained segment fails to deserialize.
            ConfigurationValidationError: If a language code is malformed.
        """
        from lingualdub.core.segment import Segment  # avoid circular at module level
        from lingualdub.exceptions import SerializationError

        if not isinstance(data, dict):
            raise SerializationError(
                f"Result.from_dict expects a dict, got {type(data).__name__}: {data!r}.",
                field="data",
                code="RESU_DESER_001",
            )

        known_keys = {
            "segments",
            "source_language",
            "target_language",
            "status",
            "warnings",
            "provenance",
            "artifacts",
            "metadata",
        }

        # --- segments --------------------------------------------------------
        if "segments" in data and data["segments"] is None:
            raise SerializationError(
                "Field 'segments' must be a list, got None.",
                field="segments",
                code="RESU_DESER_003",
            )
        raw_segments = data.get("segments", [])
        if not isinstance(raw_segments, list):
            raise SerializationError(
                f"Field 'segments' must be a list, got {type(raw_segments).__name__}: {raw_segments!r}.",
                field="segments",
                code="RESU_DESER_003",
            )
        segments: list[Segment] = []
        for idx, seg_data in enumerate(raw_segments):
            if not isinstance(seg_data, dict):
                raise SerializationError(
                    f"Segment at index {idx} must be a dict, got {type(seg_data).__name__}: {seg_data!r}.",
                    field=f"segments[{idx}]",
                    code="RESU_DESER_003",
                )
            try:
                segments.append(Segment.from_dict(seg_data))
            except SerializationError as e:
                # Re-wrap with index context for clearer diagnostics
                raise SerializationError(
                    f"Invalid segment at index {idx}: {e.message}",
                    field=f"segments[{idx}].{e.field}" if e.field else f"segments[{idx}]",
                    code=e.code,
                    context={**e.context, "segment_index": idx},
                ) from e
            except Exception as e:
                # ConfigurationValidationError from language-code validation etc.
                # is a LingualDubError subclass — preserve its type if possible,
                # otherwise wrap as SerializationError with field info.
                from lingualdub.exceptions import LingualDubError

                if isinstance(e, LingualDubError):
                    raise
                raise SerializationError(
                    f"Invalid segment at index {idx}: {e}",
                    field=f"segments[{idx}]",
                    code="RESU_DESER_003",
                    context={"segment_index": idx},
                ) from e

        # --- source_language / target_language --------------------------------
        for key in ("source_language", "target_language"):
            if key in data and data[key] is not None and not isinstance(data[key], str):
                raise SerializationError(
                    f"Field '{key}' must be a string or None, got {type(data[key]).__name__}: {data[key]!r}.",
                    field=key,
                    code="RESU_DESER_003",
                )

        # --- status ---------------------------------------------------------
        if "status" in data and data["status"] is None:
            raise SerializationError(
                "Field 'status' must be a string, got None.", field="status", code="RESU_DESER_003"
            )
        raw_status = data.get("status", ResultStatus.COMPLETE.value)
        if not isinstance(raw_status, str):
            raise SerializationError(
                f"Field 'status' must be a string, got {type(raw_status).__name__}: {raw_status!r}.",
                field="status",
                code="RESU_DESER_003",
            )
        valid_statuses = [s.value for s in ResultStatus]
        if raw_status not in valid_statuses:
            raise SerializationError(
                f"Field 'status' must be one of {valid_statuses!r}, got {raw_status!r}.",
                field="status",
                code="RESU_DESER_003",
            )
        status = ResultStatus(raw_status)

        # --- warnings / artifacts / provenance / metadata -------------------
        for key in ("warnings", "artifacts"):
            if key in data and data[key] is None:
                raise SerializationError(
                    f"Field '{key}' must be a list, got None.", field=key, code="RESU_DESER_003"
                )
            if key in data and not isinstance(data[key], list):
                raise SerializationError(
                    f"Field '{key}' must be a list, got {type(data[key]).__name__}: {data[key]!r}.",
                    field=key,
                    code="RESU_DESER_003",
                )
            if key in data and isinstance(data[key], list):
                for i, item in enumerate(data[key]):  # type: ignore[union-attr]
                    if not isinstance(item, str):
                        raise SerializationError(
                            f"Field '{key}[{i}]' must be a string, got {type(item).__name__}: {item!r}.",
                            field=f"{key}[{i}]",
                            code="RESU_DESER_003",
                        )

        for key in ("provenance", "metadata"):
            if key in data and data[key] is None:
                raise SerializationError(
                    f"Field '{key}' must be a dict, got None.", field=key, code="RESU_DESER_003"
                )
            if key in data and not isinstance(data[key], dict):
                raise SerializationError(
                    f"Field '{key}' must be a dict, got {type(data[key]).__name__}: {data[key]!r}.",
                    field=key,
                    code="RESU_DESER_003",
                )

        # Preserve unknown keys in metadata for schema evolution (base wins on collision)
        base_metadata = dict(data.get("metadata") or {})
        unknown = {k: v for k, v in data.items() if k not in known_keys}
        merged_metadata = {**unknown, **base_metadata} if unknown else base_metadata

        # Validate warnings/artifacts/provenance/metadata None was already rejected
        warnings_val = data.get("warnings", [])
        artifacts_val = data.get("artifacts", [])
        provenance_val = data.get("provenance", {})
        metadata_val = merged_metadata
        # Construction delegates language-code validation to __post_init__
        return cls(
            segments=segments,
            source_language=data.get("source_language"),
            target_language=data.get("target_language"),
            status=status,
            warnings=list(warnings_val),  # type: ignore[arg-type]
            provenance=dict(provenance_val),  # type: ignore[arg-type]
            artifacts=list(artifacts_val),  # type: ignore[arg-type]
            metadata=metadata_val,
        )

    def __repr__(self) -> str:
        return (
            f"Result(status={self.status.value!r}, "
            f"segments={len(self.segments)}, "
            f"warnings={len(self.warnings)})"
        )
