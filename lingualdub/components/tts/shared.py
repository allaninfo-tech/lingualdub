"""
Shared TTS utilities — single source of truth for dummy synthesis and fitting strategies.

Centralises the WAV generation, strategy selection, and threshold constants
previously duplicated across dummy.py, voice_conditioned.py, and mms_tts.py.
"""

from __future__ import annotations

import math
import re
import struct
import wave
from pathlib import Path

from lingualdub.components.tts.base import FittingStrategy

# Clause-boundary punctuation used to detect SPLIT candidates
_SPLIT_PATTERN = re.compile(r"[,;:—–]|\.\s|\?\s|!\s")

# Duration-ratio thresholds for fitting strategy selection (single source of truth)
# Previously duplicated 6× across tts components; tuning M4 SLO now requires 1 edit.
_COMPRESS_MAX_RATIO = 1.35
_SKIP_MIN_RATIO = 1.75


def choose_strategy(ratio: float, text: str) -> FittingStrategy:
    """Select the fitting strategy based on duration ratio and text structure."""
    if ratio <= _COMPRESS_MAX_RATIO:
        return FittingStrategy.COMPRESS
    if ratio <= _SKIP_MIN_RATIO or _SPLIT_PATTERN.search(text):
        return FittingStrategy.SPLIT
    return FittingStrategy.SKIP


def write_dummy_wav(
    filepath: Path, duration_sec: float = 1.0, freq_hz: float = 440.0, sample_rate: int = 16000
) -> None:
    """Generate a clean synthetic WAV file using Python standard library.

    Uses sine wave with smooth envelope; efficient enough for testing but
    marked as Python-loop O(n) — replace with numpy for long durations if needed.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_sec * sample_rate)
    with wave.open(str(filepath), "wb") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        frames = bytearray()
        for i in range(num_samples):
            envelope = math.sin(math.pi * (i / max(num_samples, 1)))
            val = int(32767.0 * 0.3 * envelope * math.sin(2.0 * math.pi * freq_hz * (i / sample_rate)))
            frames.extend(struct.pack("<h", val))
        wav_file.writeframes(frames)
