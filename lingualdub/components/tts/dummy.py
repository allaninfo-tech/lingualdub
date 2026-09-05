"""
Deterministic dummy TTS component for offline testing without ML dependencies.
"""

from __future__ import annotations
import tempfile
from pathlib import Path
from typing import List, Optional, Union

from lingualdub.components.tts.base import FittingStrategy, TTSComponent
from lingualdub.components.tts.shared import (
    _COMPRESS_MAX_RATIO,
    _SKIP_MIN_RATIO,
    _SPLIT_PATTERN,
    choose_strategy as _choose_strategy,
    write_dummy_wav as _write_dummy_wav,
)
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment
from lingualdub.utils.consent import ensure_consent


# Re-export shared constants for backward compatibility (tests import from dummy)
# New code should import from lingualdub.components.tts.shared directly.


class DummyTTSComponent(TTSComponent):
    """
    Fast offline TTS component generating synthetic WAV audio for pipeline testing.
    Supports temporal alignment fitting strategies: COMPRESS, SPLIT, SKIP.
    """

    name: str = "dummy_tts"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.TTS
    supported_languages: List[str] = ["lug", "nyn", "eng", "swa"]
    requires: List[str] = ["translation"]
    provides: List[str] = ["synthesised_audio"]
    on_failure: FailureMode = FailureMode.DEGRADE

    def __init__(
        self,
        output_dir: Optional[str] = None,
        sample_rate: int = 16000,
        version: str = "1.0.0",
        require_duration_target: bool = False,
    ) -> None:
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "lingualdub_dummy_tts"
        self.sample_rate = sample_rate
        self.version = version
        self.requires = ["translation", "duration_target"] if require_duration_target else ["translation"]

    def run(self, input: Union[Result, Resource]) -> Result:
        if not isinstance(input, Result):
            raise ValueError(f"DummyTTSComponent expects a Result input, got {type(input).__name__}")
        # Enforce consent for voice synthesis (M5/M6)
        ensure_consent(input, self.__class__.__name__)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        artifacts: List[str] = list(input.artifacts)
        out_segments: List[Segment] = []
        warnings: List[str] = list(input.warnings)

        if input.segments:
            for idx, seg in enumerate(input.segments):
                ratio = seg.metadata.get("duration_ratio", 1.0)
                target_dur = seg.metadata.get("target_duration", seg.duration)
                text = (seg.text or "").strip()

                strategy = _choose_strategy(ratio, text)

                new_meta = dict(seg.metadata)
                new_meta["fitting_strategy"] = strategy.value
                new_meta["source_segment_index"] = idx
                new_meta["source_start"] = seg.start
                new_meta["source_end"] = seg.end

                if strategy == FittingStrategy.COMPRESS:
                    # Synthesise at target_duration (compressed or normal rate)
                    audio_dur = max(target_dur, 0.1)
                    audio_path = self.output_dir / f"tts_segment_{idx}_{self.version}.wav"
                    _write_dummy_wav(audio_path, duration_sec=audio_dur, freq_hz=440.0 + idx * 50, sample_rate=self.sample_rate)
                    artifacts.append(str(audio_path))
                    out_segments.append(Segment(
                        start=seg.start,
                        end=seg.start + audio_dur,
                        text=seg.text,
                        language=seg.language,
                        speaker=seg.speaker,
                        confidence=seg.confidence,
                        source_language=seg.source_language,
                        provenance=dict(seg.provenance),
                        metadata=new_meta,
                    ))

                elif strategy == FittingStrategy.SPLIT:
                    # Split at clause boundary and synthesise sub-segments
                    parts = [p.strip() for p in _SPLIT_PATTERN.split(text) if p.strip()]
                    if not parts:
                        parts = [text]
                    sub_dur = seg.duration / len(parts)
                    for sub_idx, part in enumerate(parts):
                        sub_start = seg.start + sub_idx * sub_dur
                        sub_end = seg.start + (sub_idx + 1) * sub_dur
                        audio_path = self.output_dir / f"tts_segment_{idx}_split_{sub_idx}_{self.version}.wav"
                        _write_dummy_wav(audio_path, duration_sec=sub_dur, freq_hz=440.0 + idx * 50, sample_rate=self.sample_rate)
                        artifacts.append(str(audio_path))
                        sub_meta = dict(new_meta)
                        sub_meta["split_index"] = sub_idx
                        sub_meta["split_count"] = len(parts)
                        sub_meta["parent_end"] = seg.end
                        sub_meta["parent_start"] = seg.start
                        out_segments.append(Segment(
                            start=round(sub_start, 6),
                            end=round(sub_end, 6),
                            text=part,
                            language=seg.language,
                            speaker=seg.speaker,
                            confidence=seg.confidence,
                            source_language=seg.source_language,
                            provenance=dict(seg.provenance),
                            metadata=sub_meta,
                        ))

                else:  # SKIP
                    new_meta["unfit"] = True
                    warnings.append(f"Segment #{idx} skipped (duration_ratio={ratio:.2f} exceeds threshold)")
                    out_segments.append(Segment(
                        start=seg.start,
                        end=seg.end,
                        text=seg.text,
                        language=seg.language,
                        speaker=seg.speaker,
                        confidence=seg.confidence,
                        source_language=seg.source_language,
                        provenance=dict(seg.provenance),
                        metadata=new_meta,
                    ))

        else:
            # Utterance fallback (no segments)
            audio_path = self.output_dir / f"tts_output_{self.version}.wav"
            _write_dummy_wav(audio_path, duration_sec=2.0, sample_rate=self.sample_rate)
            artifacts.append(str(audio_path))

        return Result(
            segments=out_segments if input.segments else list(input.segments),
            source_language=input.source_language,
            target_language=input.target_language,
            warnings=warnings,
            provenance=dict(input.provenance),
            artifacts=artifacts,
            metadata={**input.metadata, "tts_engine": f"{self.name}@{self.version}"},
        )

    def degrade(self, input: Union[Result, Resource]) -> Result:
        """Degraded fallback: generate a short low-amplitude silent/neutral tone."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        fallback_path = self.output_dir / f"tts_degraded_{self.version}.wav"
        _write_dummy_wav(fallback_path, duration_sec=1.0, freq_hz=220.0, sample_rate=self.sample_rate)

        artifacts = list(input.artifacts) if isinstance(input, Result) else []
        artifacts.append(str(fallback_path))

        res = Result(
            segments=list(input.segments) if isinstance(input, Result) else [],
            source_language=input.source_language if isinstance(input, Result) else None,
            target_language=input.target_language if isinstance(input, Result) else None,
            provenance=dict(input.provenance) if isinstance(input, Result) else {},
            artifacts=artifacts,
            metadata={"tts_degraded": True},
        )
        res.mark_degraded("TTS synthesis degraded to fallback tone")
        return res
