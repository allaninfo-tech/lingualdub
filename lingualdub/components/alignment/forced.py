"""
Forced alignment component for temporal alignment (Milestone 4).

DummyForcedAlignmentComponent assigns word-level timestamps to each Segment
proportionally by character count, strictly within the parent Segment boundaries.

It satisfies M4.1:
  - requires: ["transcription"]
  - provides: ["aligned_timestamps"]
  - acquires a timing resource via ResourceManager (offline fallback if absent)
  - registered via manifest
"""

from __future__ import annotations
import logging
from typing import Dict, List, Optional, Union

from lingualdub.components.alignment.base import AlignmentComponent
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment

logger = logging.getLogger(__name__)


def _distribute_word_timestamps(
    words: List[str], seg_start: float, seg_end: float
) -> List[Dict]:
    """
    Distribute word timestamps across [seg_start, seg_end] proportionally
    by character length, ensuring all boundaries are strictly within the parent segment.
    """
    if not words:
        return []

    total_chars = sum(len(w) for w in words) or 1
    duration = seg_end - seg_start
    timestamps = []
    cursor = seg_start

    for i, word in enumerate(words):
        frac = len(word) / total_chars
        word_dur = duration * frac
        word_start = round(cursor, 6)
        # Last word always clamps to seg_end to avoid floating-point drift
        if i == len(words) - 1:
            word_end = round(seg_end, 6)
        else:
            word_end = round(min(cursor + word_dur, seg_end), 6)

        timestamps.append({
            "word": word,
            "start": word_start,
            "end": word_end,
        })
        cursor = word_end

    return timestamps


class DummyForcedAlignmentComponent(AlignmentComponent):
    """
    Offline deterministic forced aligner that distributes word-level timestamps
    proportionally within each Segment boundary.

    In production, replace with a real aligner (e.g. Montreal Forced Aligner,
    WhisperX word timestamps, or CTC-based aligner) registered via the manifest.
    """

    name: str = "dummy_forced_aligner"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.ALIGNMENT
    supported_languages: List[str] = ["lug", "nyn", "eng", "swa"]
    requires: List[str] = ["transcription"]
    provides: List[str] = ["aligned_timestamps"]
    on_failure: FailureMode = FailureMode.DEGRADE

    def __init__(
        self,
        resource_manager: Optional[object] = None,
        registry: Optional[object] = None,
        version: str = "1.0.0",
    ) -> None:
        self.version = version
        self._resource_manager = resource_manager
        self._registry = registry
        self._timing_resource: Optional[Resource] = None
        self._timing_resource_path: Optional[str] = None

    def _load_timing_resource(self) -> None:
        """Acquire timing/pronunciation resource via Registry/ResourceManager."""
        if self._timing_resource is not None:
            return
        from lingualdub.utils.resource_helpers import acquire_resource

        res, path = acquire_resource(
            self._registry, self._resource_manager, "dummy_timing_resource"
        )
        if res is not None:
            self._timing_resource = res
            self._timing_resource_path = path


    def run(self, input: Union[Result, Resource]) -> Result:
        if not isinstance(input, Result):
            raise ValueError(
                f"DummyForcedAlignmentComponent expects a Result, got {type(input).__name__}"
            )

        self._load_timing_resource()

        aligned_segments: List[Segment] = []
        for seg in input.segments:
            words = (seg.text or "").split()
            word_timestamps = _distribute_word_timestamps(words, seg.start, seg.end)
            new_meta = dict(seg.metadata)
            new_meta["word_timestamps"] = word_timestamps
            new_meta["aligned"] = True
            aligned_seg = Segment(
                start=seg.start,
                end=seg.end,
                text=seg.text,
                language=seg.language,
                speaker=seg.speaker,
                confidence=seg.confidence,
                source_language=seg.source_language,
                provenance={**seg.provenance, "aligner": f"{self.name}@{self.version}"},
                metadata=new_meta,
            )
            aligned_segments.append(aligned_seg)

        return Result(
            segments=aligned_segments,
            source_language=input.source_language,
            target_language=input.target_language,
            warnings=list(input.warnings),
            provenance={**input.provenance, "forced_aligner": f"{self.name}@{self.version}"},
            artifacts=list(input.artifacts),
            metadata={**input.metadata, "aligned_timestamps": True},
        )
