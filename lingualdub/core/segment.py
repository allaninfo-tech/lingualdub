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
from typing import Optional


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
    speaker: Optional[str] = None
    confidence: Optional[float] = None
    source_language: Optional[str] = None
    provenance: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("Segment.start must be >= 0.")
        if self.end < self.start:
            raise ValueError("Segment.end must be >= Segment.start.")

    @property
    def duration(self) -> float:
        """Duration of this segment in seconds."""
        return self.end - self.start

    def __repr__(self) -> str:
        return (
            f"Segment(start={self.start}, end={self.end}, "
            f"language={self.language!r}, speaker={self.speaker!r})"
        )
