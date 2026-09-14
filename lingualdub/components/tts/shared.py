# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0
# Internal — not part of public API

"""
Shared TTS utilities — single source of truth for dummy synthesis and fitting strategies.

Centralises the WAV generation, strategy selection, and threshold constants
previously duplicated across dummy.py, voice_conditioned.py, and mms_tts.py.
"""

from __future__ import annotations

import math
import re
import wave
from pathlib import Path

from lingualdub.components.tts.base import FittingStrategy

# Clause-boundary punctuation used to detect SPLIT candidates (including newlines)
_SPLIT_PATTERN = re.compile(r"[,;:—–]|\.\s|\?\s|!\s|\n")

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
    """Generate a clean synthetic WAV file using Python standard library."""
    if duration_sec < 0:
        raise ValueError(  # justified: component input validation — duration must be >=0
            f"duration_sec must be >=0, got {duration_sec!r}"
        )
    if duration_sec == 0:
        duration_sec = 0.1
    filepath.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_sec * sample_rate)
    # Cap to 10 seconds to avoid huge files
    max_samples = sample_rate * 10
    if num_samples > max_samples:
        num_samples = max_samples
    # Use array for efficient packing instead of splat
    import array

    buf = array.array("h")
    for i in range(num_samples):
        envelope = math.sin(math.pi * (i / max(num_samples, 1)))
        val = int(32767.0 * 0.3 * envelope * math.sin(2.0 * math.pi * freq_hz * (i / sample_rate)))
        buf.append(val)
    with wave.open(str(filepath), "wb") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(buf.tobytes())
