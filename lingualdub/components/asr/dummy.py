"""
Deterministic dummy ASR component for offline testing and fast local verification.
"""

from __future__ import annotations
from typing import List, Optional, Union

from lingualdub.components.asr.base import ASRComponent
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment


class DummyASRComponent(ASRComponent):
    """
    A lightweight, deterministic ASR component for testing pipelines locally.
    
    Returns predefined Segments without requiring GPU or machine learning dependencies.
    """

    name: str = "dummy_asr"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.ASR
    supported_languages: List[str] = ["lug", "nyn", "eng", "swa"]
    requires: List[str] = []
    provides: List[str] = ["transcription", "word_timestamps", "language_detection"]
    on_failure: FailureMode = FailureMode.ABORT

    def __init__(
        self,
        default_text: str = "Oli otya nnyabo, twebaza nnyo emirimu gyo.",
        language: str = "lug",
        duration: float = 3.5,
        confidence: float = 0.95,
        version: str = "1.0.0",
    ) -> None:
        self.default_text = default_text
        self.language = language
        self.duration = duration
        self.confidence = confidence
        self.version = version

    def run(self, input: Union[Result, Resource]) -> Result:
        source_lang = getattr(input, "language", None) or self.language
        text = self.default_text

        # If input is a Result and already has segments, we can derive or use text
        if isinstance(input, Result) and input.segments:
            source_lang = input.source_language or self.language
            segments = [
                Segment(
                    start=s.start,
                    end=s.end,
                    text=s.text or text,
                    language=s.language or source_lang,
                    confidence=self.confidence,
                    speaker=s.speaker,
                    metadata={
                        **s.metadata,
                        "words": [
                            {"word": w, "start": s.start + i * 0.3, "end": s.start + (i + 1) * 0.3}
                            for i, w in enumerate((s.text or text).split())
                        ],
                    },
                )
                for s in input.segments
            ]
        else:
            words = text.split()
            step = self.duration / max(len(words), 1)
            segments = [
                Segment(
                    start=0.0,
                    end=self.duration,
                    text=text,
                    language=source_lang,
                    confidence=self.confidence,
                    speaker="speaker_0",
                    metadata={
                        "words": [
                            {"word": w, "start": round(i * step, 2), "end": round((i + 1) * step, 2)}
                            for i, w in enumerate(words)
                        ]
                    },
                )
            ]

        result = Result(
            segments=segments,
            source_language=source_lang,
            metadata={"asr_model": f"{self.name}@{self.version}"},
        )
        return result
