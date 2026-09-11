# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Segment — the shared unit of data between components.

A Segment is the atomic unit exchanged between pipeline stages. It carries
timing, text, per-segment language, speaker identity, confidence, and
provenance. Per-segment language is authoritative at the segment level —
not just at the file level — which is what makes code-switching a structural
property of the data rather than an annotation added after the fact.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lingualdub.types import LanguageCode, MetadataDict, ProvenanceDict
from lingualdub.utils.validation import (
    require_non_empty_string,
    validate_language_code,
)


@dataclass(frozen=True)
class Segment:
    """
    An atomic unit of speech or text data.

    This is an **immutable value object** — all fields are validated at
    construction and the instance is frozen. To produce a modified copy use
    :meth:`replace`.

    Attributes:
        start: Start time in seconds. Must be ``>= 0``. Invariant: ``end >= start``.
        end: End time in seconds. Must be ``>= start``. Duration is ``end - start``.
        text: Transcribed, translated, or synthesised text for this segment.
            May be empty (``\"\"``) for pure timing segments, but if non-empty
            must be a non-whitespace string.
        language: Language code for this specific segment. Authoritative per-segment,
            not inherited from the containing :class:`Result`. Validated as
            ISO 639-3 (``^[a-z]{2,3}$``). Code-switch detection populates this
            field; pipeline routing acts on it.
        speaker: Speaker identifier or reference for this segment, if known.
        confidence: Model confidence for this segment, in ``[0.0, 1.0]`` when set.
        source_language: Original language before translation, if applicable.
            When present, validated as language code.
        provenance: Model or component identifiers that produced this segment.
            Free-form dict, not validated beyond type.
        metadata: Extensible key-value store for component-specific data
            (e.g. ``word_timestamps``, ``fitting_strategy``).
    """

    start: float
    end: float
    text: str
    language: LanguageCode
    speaker: str | None = None
    confidence: float | None = None
    source_language: LanguageCode | None = None
    provenance: ProvenanceDict = field(default_factory=dict)
    metadata: MetadataDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Use centralized validators; keep original semantics but raise
        # ConfigurationValidationError (which also is ValueError for compat).
        from lingualdub.exceptions import ConfigurationValidationError

        # start / end are numbers; validate via helper where possible
        if self.start < 0:
            raise ConfigurationValidationError(
                f"Field 'start' must be >= 0, got {self.start!r}.", field="start"
            )
        if self.end < self.start:
            raise ConfigurationValidationError(
                f"Field 'end' must be >= start ({self.start!r}), got {self.end!r}.",
                field="end",
            )
        # Validate core string fields via shared helper
        if self.text:
            require_non_empty_string(self.text, "text")
        require_non_empty_string(self.language, "language")
        validate_language_code(self.language)
        if self.source_language is not None:
            require_non_empty_string(self.source_language, "source_language")
            validate_language_code(self.source_language)
        # confidence if provided must be in [0,1]
        if self.confidence is not None:
            if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
                raise ConfigurationValidationError(
                    f"Field 'confidence' must be a number in [0, 1], got {type(self.confidence).__name__}: {self.confidence!r}.",
                    field="confidence",
                )
            if not (0.0 <= float(self.confidence) <= 1.0):
                raise ConfigurationValidationError(
                    f"Field 'confidence' must be in [0, 1], got {self.confidence!r}.",
                    field="confidence",
                )

    def replace(self, **changes) -> Segment:
        """
        Return a new :class:`Segment` with the given field changes.

        Args:
            **changes: Field names and new values. Unknown fields raise ``TypeError``.
                Invalid values (e.g. ``start=-1`` or ``language=\"bad_code\"``)
                raise :class:`ConfigurationValidationError`.

        Returns:
            A new, validated :class:`Segment` instance. The original is unchanged.

        Example:
            >>> seg = Segment(start=0, end=1, text=\"hi\", language=\"lug\")
            >>> seg2 = seg.replace(text=\"hello\", language=\"eng\")
        """
        from dataclasses import replace as dc_replace

        # Validate known field names early for clearer error
        valid_fields = set(self.__dataclass_fields__.keys())
        for k in changes:
            if k not in valid_fields:
                raise TypeError(f"Segment.replace() got unexpected field {k!r}")

        # Use dataclasses.replace which bypasses frozen __setattr__ via object.__setattr__
        new_obj = dc_replace(self, **changes)
        # Manually trigger validation (dataclasses.replace does not call __post_init__)
        # We call the validation logic directly by invoking __post_init__'s checks
        # via a helper to avoid duplicating code.
        # Since Segment is frozen, we need to validate the new object without mutating.
        # Call __post_init__ manually (it only validates, not mutates, so safe).
        # However __post_init__ is defined to validate self, so we call it on new_obj.
        # Use object.__getattribute__ to avoid recursion issues.
        try:
            # Re-use the same validation logic as __post_init__
            from lingualdub.exceptions import ConfigurationValidationError

            if new_obj.start < 0:
                raise ConfigurationValidationError(
                    f"Field 'start' must be >= 0, got {new_obj.start!r}.", field="start"
                )
            if new_obj.end < new_obj.start:
                raise ConfigurationValidationError(
                    f"Field 'end' must be >= start ({new_obj.start!r}), got {new_obj.end!r}.",
                    field="end",
                )
            if new_obj.text:
                require_non_empty_string(new_obj.text, "text")
            require_non_empty_string(new_obj.language, "language")
            validate_language_code(new_obj.language)
            if new_obj.source_language is not None:
                require_non_empty_string(new_obj.source_language, "source_language")
                validate_language_code(new_obj.source_language)
            if new_obj.confidence is not None:
                if not isinstance(new_obj.confidence, (int, float)) or isinstance(
                    new_obj.confidence, bool
                ):
                    raise ConfigurationValidationError(
                        f"Field 'confidence' must be a number in [0, 1], got {type(new_obj.confidence).__name__}: {new_obj.confidence!r}.",
                        field="confidence",
                    )
                if not (0.0 <= float(new_obj.confidence) <= 1.0):
                    raise ConfigurationValidationError(
                        f"Field 'confidence' must be in [0, 1], got {new_obj.confidence!r}.",
                        field="confidence",
                    )
        except Exception:
            # If validation fails, the new object is discarded; original unchanged
            raise

        return new_obj

    @property
    def duration(self) -> float:
        """Duration of this segment in seconds."""
        return self.end - self.start

    def to_dict(self) -> dict:
        """Serialize this Segment to a JSON-compatible dictionary."""
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "language": self.language,
            "speaker": self.speaker,
            "confidence": self.confidence,
            "source_language": self.source_language,
            "provenance": dict(self.provenance),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Segment:
        """Deserialize a Segment from a dictionary produced by to_dict()."""
        return cls(
            start=data["start"],
            end=data["end"],
            text=data["text"],
            language=data["language"],
            speaker=data.get("speaker"),
            confidence=data.get("confidence"),
            source_language=data.get("source_language"),
            provenance=data.get("provenance", {}),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return (
            f"Segment(start={self.start}, end={self.end}, "
            f"language={self.language!r}, speaker={self.speaker!r})"
        )
