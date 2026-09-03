"""
Deterministic dummy translation component for offline testing.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Union

from lingualdub.components.translation.base import TranslationComponent
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment


# Sample dictionary of common Luganda/Runyankole words/phrases to English
SAMPLE_DICTIONARY: Dict[str, str] = {
    "oli otya": "how are you",
    "oli otya nnyabo": "hello madam, how are you",
    "twebaza nnyo": "thank you very much",
    "emirimu gyo": "for your work",
    "bulungi": "good / well",
    "webale": "thank you",
    "ki kati": "what's up",
    "agandi": "how are you (Runyankole)",
    "nungi": "fine (Runyankole)",
}


class DummyTranslationComponent(TranslationComponent):
    """
    Fast offline translation component for local pipeline execution.
    """

    name: str = "dummy_translator"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.TRANSLATION
    supported_languages: List[str] = ["lug", "nyn", "eng", "swa"]
    requires: List[str] = ["transcription"]
    provides: List[str] = ["translation"]
    on_failure: FailureMode = FailureMode.ABORT

    def __init__(
        self,
        source_language: str = "lug",
        target_language: str = "eng",
        prefix: str = "[EN] ",
        custom_dictionary: Optional[Dict[str, str]] = None,
        default_translation: Optional[str] = None,
        version: str = "1.0.0",
    ) -> None:
        self.source_language = source_language
        self.target_language = target_language
        self.prefix = prefix
        self.custom_dictionary = custom_dictionary or {}
        self.default_translation = default_translation
        self.version = version

    def _translate_text(self, text: str) -> str:
        if self.default_translation is not None:
            return self.default_translation
        clean = text.strip().lower().rstrip(".,!?")
        # Check custom dictionary first
        for key in sorted(self.custom_dictionary.keys(), key=len, reverse=True):
            if key in clean:
                return text.lower().replace(key, self.custom_dictionary[key])
        # Check longest matching phrases from sample dictionary
        for key in sorted(SAMPLE_DICTIONARY.keys(), key=len, reverse=True):
            if key in clean:
                return text.lower().replace(key, SAMPLE_DICTIONARY[key])
        return f"{self.prefix}{text}"

    def run(self, input: Union[Result, Resource]) -> Result:
        if not isinstance(input, Result):
            raise ValueError(f"DummyTranslationComponent expects a Result input, got {type(input).__name__}")

        translated_segments: List[Segment] = []
        for s in input.segments:
            translated_text = self._translate_text(s.text)
            new_seg = Segment(
                start=s.start,
                end=s.end,
                text=translated_text,
                language=self.target_language,
                source_language=s.language or self.source_language,
                speaker=s.speaker,
                confidence=s.confidence,
                metadata=dict(s.metadata),
            )
            translated_segments.append(new_seg)

        res = Result(
            segments=translated_segments,
            source_language=input.source_language or self.source_language,
            target_language=self.target_language,
            warnings=list(input.warnings),
            provenance=dict(input.provenance),
            artifacts=list(input.artifacts),
            metadata={**input.metadata, "translator": f"{self.name}@{self.version}"},
        )
        return res
