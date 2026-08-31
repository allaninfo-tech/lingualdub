"""
Deterministic dummy TTS component for offline testing without ML dependencies.
"""

from __future__ import annotations
import math
import struct
import tempfile
import wave
from pathlib import Path
from typing import List, Optional, Union

from lingualdub.components.tts.base import TTSComponent
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


def _write_dummy_wav(filepath: Path, duration_sec: float = 1.0, freq_hz: float = 440.0, sample_rate: int = 16000) -> None:
    """Generate a clean synthetic WAV file using Python standard library."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_sec * sample_rate)
    with wave.open(str(filepath), "wb") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        frames = bytearray()
        for i in range(num_samples):
            # Sine wave with smooth envelope
            envelope = math.sin(math.pi * (i / max(num_samples, 1)))
            val = int(32767.0 * 0.3 * envelope * math.sin(2.0 * math.pi * freq_hz * (i / sample_rate)))
            frames.extend(struct.pack("<h", val))
        wav_file.writeframes(frames)


class DummyTTSComponent(TTSComponent):
    """
    Fast offline TTS component generating synthetic WAV audio for pipeline testing.
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
    ) -> None:
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "lingualdub_dummy_tts"
        self.sample_rate = sample_rate
        self.version = version

    def run(self, input: Union[Result, Resource]) -> Result:
        if not isinstance(input, Result):
            raise ValueError(f"DummyTTSComponent expects a Result input, got {type(input).__name__}")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        artifacts: List[str] = list(input.artifacts)

        # Generate audio for each segment or for the full utterance
        if input.segments:
            for idx, seg in enumerate(input.segments):
                seg_dur = max(seg.duration, 0.5)
                audio_path = self.output_dir / f"tts_segment_{idx}_{self.version}.wav"
                _write_dummy_wav(audio_path, duration_sec=seg_dur, freq_hz=440.0 + idx * 50, sample_rate=self.sample_rate)
                artifacts.append(str(audio_path))
        else:
            # Utterance fallback
            audio_path = self.output_dir / f"tts_output_{self.version}.wav"
            _write_dummy_wav(audio_path, duration_sec=2.0, sample_rate=self.sample_rate)
            artifacts.append(str(audio_path))

        return Result(
            segments=list(input.segments),
            source_language=input.source_language,
            target_language=input.target_language,
            warnings=list(input.warnings),
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
