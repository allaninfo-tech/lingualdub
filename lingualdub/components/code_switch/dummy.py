"""
Deterministic dummy code-switch detection component for offline testing.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Union

from lingualdub.components.code_switch.base import CodeSwitchComponent
from lingualdub.components.code_switch.lexicons import DEFAULT_WORD_LANGUAGES
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment


class DummyCodeSwitchComponent(CodeSwitchComponent):
    """
    Fast offline code-switch detection and language identification component.

    Inspects words within Segments to assign language codes ('lug' or 'eng')
    and detect language boundaries within mixed-language utterances.
    """

    name: str = "dummy_code_switch"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.CODE_SWITCH
    supported_languages: List[str] = ["lug", "nyn", "eng", "swa"]
    requires: List[str] = ["transcription"]
    provides: List[str] = ["language_labels", "code_switch_detection"]
    on_failure: FailureMode = FailureMode.DEGRADE

    def __init__(
        self,
        default_language: str = "lug",
        word_map: Optional[Dict[str, str]] = None,
        split_mixed_segments: bool = False,
        version: str = "1.0.0",
    ) -> None:
        self.default_language = default_language
        self.word_map = dict(DEFAULT_WORD_LANGUAGES)
        if word_map:
            self.word_map.update(word_map)
        self.split_mixed_segments = split_mixed_segments
        self.version = version

    def _classify_word(self, word: str) -> str:
        clean = word.strip().lower().rstrip(".,!?;:")
        return self.word_map.get(clean, self.default_language)

    def _classify_segment_text(self, text: str) -> str:
        words = text.strip().split()
        if not words:
            return self.default_language

        counts: Dict[str, int] = {}
        for w in words:
            lang = self._classify_word(w)
            counts[lang] = counts.get(lang, 0) + 1

        # Return language with most word occurrences
        sorted_langs = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_langs[0][0]

    def run(self, input: Union[Result, Resource]) -> Result:
        if not isinstance(input, Result):
            raise ValueError(f"DummyCodeSwitchComponent expects a Result input, got {type(input).__name__}")

        new_segments: List[Segment] = []
        any_switch_detected = False

        for seg in input.segments:
            words = seg.text.strip().split()
            word_langs = [self._classify_word(w) for w in words]
            unique_langs = set(word_langs)

            is_code_switched = len(unique_langs) > 1
            if is_code_switched:
                any_switch_detected = True

            # If segment splitting on mixed spans is requested and word metadata exists
            if self.split_mixed_segments and is_code_switched and seg.metadata.get("words"):
                meta_words = seg.metadata["words"]
                current_span: List[dict] = []
                current_lang: Optional[str] = None

                for w_obj in meta_words:
                    w_text = w_obj.get("word", "")
                    w_lang = self._classify_word(w_text)

                    if current_lang is None or w_lang == current_lang:
                        current_span.append(w_obj)
                        current_lang = w_lang
                    else:
                        # Flush span
                        span_text = " ".join(item.get("word", "") for item in current_span)
                        new_segments.append(
                            Segment(
                                start=current_span[0].get("start", seg.start),
                                end=current_span[-1].get("end", seg.end),
                                text=span_text,
                                language=current_lang,
                                source_language=seg.source_language or input.source_language,
                                speaker=seg.speaker,
                                metadata={
                                    **seg.metadata,
                                    "code_switch_split": True,
                                    "word_languages": [current_lang] * len(current_span),
                                },
                            )
                        )
                        current_span = [w_obj]
                        current_lang = w_lang

                if current_span and current_lang:
                    span_text = " ".join(item.get("word", "") for item in current_span)
                    new_segments.append(
                        Segment(
                            start=current_span[0].get("start", seg.start),
                            end=current_span[-1].get("end", seg.end),
                            text=span_text,
                            language=current_lang,
                            source_language=seg.source_language or input.source_language,
                            speaker=seg.speaker,
                            metadata={
                                **seg.metadata,
                                "code_switch_split": True,
                                "word_languages": [current_lang] * len(current_span),
                            },
                        )
                    )
            else:
                assigned_lang = self._classify_segment_text(seg.text)
                updated_seg = Segment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text,
                    language=assigned_lang,
                    source_language=seg.source_language or input.source_language,
                    speaker=seg.speaker,
                    confidence=seg.confidence,
                    metadata={
                        **seg.metadata,
                        "code_switch_detected": is_code_switched,
                        "word_languages": word_langs,
                    },
                )
                new_segments.append(updated_seg)

        total_unique_langs = len(set(s.language for s in new_segments if s.language))
        has_code_switching = any_switch_detected or total_unique_langs > 1

        res = Result(
            segments=new_segments,
            source_language=input.source_language,
            target_language=input.target_language,
            warnings=list(input.warnings),
            provenance={**input.provenance, "code_switch_detector": f"{self.name}@{self.version}"},
            artifacts=list(input.artifacts),
            metadata={
                **input.metadata,
                "code_switch": {
                    "has_code_switching": has_code_switching,
                    "segments_count": len(new_segments),
                },
            },
        )
        return res
