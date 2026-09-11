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

from lingualdub.utils.validation import (
    require_non_empty_string,
    validate_language_code,
)


@dataclass
class Segment:
    """
    An atomic unit of speech or text data.

    Attributes:
        start: Start time in seconds.
        end: End time in seconds.
        text: Transcribed, translated, or synthesised text for this segment.
        language: Language code for this specific segment. Authoritative per-segment,
            not inherited from the containing Result. Code-switch detection populates
            this field; pipeline routing acts on it.
        speaker: Speaker identifier or reference for this segment.
        confidence: Model confidence for this segment, in [0.0, 1.0].
        source_language: Original language before translation, if applicable.
        provenance: Model or component identifiers that produced this segment.
    """

    start: float
    end: float
    text: str
    language: str
    speaker: str | None = None
    confidence: float | None = None
    source_language: str | None = None
    provenance: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Use centralized validators; keep original semantics but raise
        # ConfigurationValidationError (which also is ValueError for compat).
        from lingualdub.exceptions import ConfigurationValidationError

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
