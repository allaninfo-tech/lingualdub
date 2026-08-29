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
from typing import List, Optional

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


@dataclass
class Result:
    """
    The structured output of a pipeline or component run.

    Attributes:
        segments: Ordered list of Segment objects produced by this run.
        source_language: Source language code for this result.
        target_language: Target language code, if a translation stage was involved.
        status: Processing status of this result.
        warnings: Human-readable warnings recorded during processing.
        provenance: Structured record linking this result to the pipeline config,
            component versions, dataset version, and run identifier that produced it.
            Used as a comparison key when evaluating across runs.
        artifacts: Paths or URIs of generated assets (audio, video, datasets)
            associated with this result.
        metadata: Extensible key-value store for component-specific output data.
    """

    segments: List[Segment] = field(default_factory=list)
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    status: ResultStatus = ResultStatus.COMPLETE
    warnings: List[str] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add_warning(self, message: str) -> None:
        """Record a warning without changing the result's status."""
        self.warnings.append(message)

    def mark_partial(self, reason: str) -> None:
        """Mark this result as partial and record the reason."""
        self.status = ResultStatus.PARTIAL
        self.add_warning(f"Partial: {reason}")

    def mark_degraded(self, reason: str) -> None:
        """Mark this result as degraded and record the reason."""
        self.status = ResultStatus.DEGRADED
        self.add_warning(f"Degraded: {reason}")

    def mark_failed(self, reason: str) -> None:
        """Mark this result as failed and record the reason."""
        self.status = ResultStatus.FAILED
        self.add_warning(f"Failed: {reason}")

    @property
    def is_usable(self) -> bool:
        """Returns True if the result can be passed to downstream consumers."""
        return self.status != ResultStatus.FAILED

    def __repr__(self) -> str:
        return (
            f"Result(status={self.status.value!r}, "
            f"segments={len(self.segments)}, "
            f"warnings={len(self.warnings)})"
        )
