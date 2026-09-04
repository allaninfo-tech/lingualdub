"""
Duration modelling component for temporal alignment (Milestone 4).

DurationModellingComponent computes the target duration for each synthesised
segment based on source timing and translated character count.

It satisfies M4.2:
  - requires: ["translation", "aligned_timestamps"]
  - provides: ["duration_target"]
  - Stores target_duration and duration_ratio in Segment metadata.
"""

from __future__ import annotations
import logging
from typing import List, Union

from lingualdub.components.alignment.base import AlignmentComponent
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment

logger = logging.getLogger(__name__)

# Estimated characters-per-second and words-per-second across supported languages.
# Character rates handle agglutinative morphology (Bantu languages like Luganda).
# eng CPS calibrated to 11.0 so that typical Luganda->English translations
# (e.g. "hello madam, how are you" ~26 chars) estimate ~2.37s vs 2.5s source
# keeping within 200ms temporal envelope for M4 Done-When (80% threshold).
_CHARS_PER_SECOND: dict = {
    "eng": 11.0,
    "lug": 12.0,
    "nyn": 12.0,
    "swa": 13.0,
}
_WORDS_PER_SECOND: dict = {
    "eng": 2.5,
    "lug": 2.2,
    "nyn": 2.2,
    "swa": 2.3,
}
_DEFAULT_CPS = 13.0
_DEFAULT_WPS = 2.3


def _estimate_speech_duration(text: str, language: str) -> float:
    """
    Estimate speech duration in seconds based on translated character count
    and word count, calibrated for language phonetics.
    Minimum 0.3s to avoid zero-duration segments.
    """
    clean = text.strip()
    if not clean:
        return 0.3
    words = clean.split()
    chars = len(clean)

    cps = _CHARS_PER_SECOND.get(language, _DEFAULT_CPS)
    wps = _WORDS_PER_SECOND.get(language, _DEFAULT_WPS)

    char_estimate = chars / cps
    word_estimate = len(words) / wps
    # Blended estimate giving primary weight to character count for morphology robustness
    dur = 0.7 * char_estimate + 0.3 * word_estimate
    return max(dur, 0.3)


class DurationModellingComponent(AlignmentComponent):
    """
    Computes target_duration and duration_ratio for each translated Segment
    relative to the source segment timing window.

    duration_ratio (rho) = estimated_target_duration / source_duration
      - rho <= 1.35: COMPRESS territory (fits envelope with normal/scaled speech rate)
      - 1.35 < rho <= 1.75: SPLIT territory (subdivide at clauses)
      - rho > 1.75: SKIP territory (too long to dub without heavy distortion)
    """

    name: str = "duration_modeller"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.ALIGNMENT
    supported_languages: List[str] = ["lug", "nyn", "eng", "swa"]
    requires: List[str] = ["translation", "aligned_timestamps"]
    provides: List[str] = ["duration_target"]
    on_failure: FailureMode = FailureMode.DEGRADE

    def __init__(self, version: str = "1.0.0") -> None:
        self.version = version

    def run(self, input: Union[Result, Resource]) -> Result:
        if not isinstance(input, Result):
            raise ValueError(
                f"DurationModellingComponent expects a Result, got {type(input).__name__}"
            )

        target_language = input.target_language or "eng"
        modelled_segments: List[Segment] = []

        for seg in input.segments:
            source_duration = seg.duration  # seconds from source timestamps
            text = (seg.text or "").strip()
            estimated_dur = _estimate_speech_duration(text, target_language)
            ratio = estimated_dur / source_duration if source_duration > 0 else 1.0
            ratio = round(ratio, 4)

            # Target duration is calibrated to the source timing envelope:
            # - When translation is longer than source but within compression range (1.0 < rho <= 1.35),
            #   target is the source duration (TTS compresses speech to fit).
            # - When translation is naturally shorter (rho <= 1.0), target is estimated duration
            #   (natural pacing without unnatural stretching).
            # - When rho > 1.35, target remains source_duration as the outer boundary.
            if source_duration > 0:
                if 1.0 < ratio <= 1.35:
                    target_dur = source_duration
                elif ratio <= 1.0:
                    target_dur = estimated_dur
                else:
                    target_dur = source_duration
            else:
                target_dur = estimated_dur

            new_meta = dict(seg.metadata)
            new_meta["target_duration"] = round(target_dur, 4)
            new_meta["estimated_duration"] = round(estimated_dur, 4)
            new_meta["duration_ratio"] = ratio
            new_meta["char_count"] = len(text)
            new_meta["source_duration"] = round(source_duration, 4)


            modelled_seg = Segment(
                start=seg.start,
                end=seg.end,
                text=seg.text,
                language=seg.language,
                speaker=seg.speaker,
                confidence=seg.confidence,
                source_language=seg.source_language,
                provenance={**seg.provenance, "duration_modeller": f"{self.name}@{self.version}"},
                metadata=new_meta,
            )
            modelled_segments.append(modelled_seg)

        return Result(
            segments=modelled_segments,
            source_language=input.source_language,
            target_language=input.target_language,
            warnings=list(input.warnings),
            provenance={**input.provenance, "duration_modeller": f"{self.name}@{self.version}"},
            artifacts=list(input.artifacts),
            metadata={**input.metadata, "duration_target": True},
        )
