"""
Heuristic and lexicon-based Language Identification (LID) component.

Identifies language boundaries in mixed Luganda-English speech and text,
populating Segment.language per segment.
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple, Union

from lingualdub.components.code_switch.base import CodeSwitchComponent
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment
from lingualdub.components.code_switch.lexicons import ENGLISH_LEXICON, LUGANDA_LEXICON


class HeuristicLIDComponent(CodeSwitchComponent):
    """
    Lightweight, dependency-free Language Identification (LID) component
    for Bantu (Luganda) and English mixed-language utterances.
    """

    name: str = "heuristic_lid"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.CODE_SWITCH
    supported_languages: List[str] = ["lug", "nyn", "eng"]
    requires: List[str] = ["transcription"]
    provides: List[str] = ["language_labels", "code_switch_detection"]
    on_failure: FailureMode = FailureMode.DEGRADE

    def __init__(
        self,
        default_language: str = "lug",
        split_segments: bool = True,
        confidence_threshold: float = 0.6,
        version: str = "1.0.0",
    ) -> None:
        self.default_language = default_language
        self.split_segments = split_segments
        self.confidence_threshold = confidence_threshold
        self.version = version

    def _score_word(self, word: str) -> Tuple[str, float]:
        """Score an individual token as 'lug' or 'eng'."""
        clean = re.sub(r"[^\w\s]", "", word.lower().strip())
        if not clean:
            return self.default_language, 0.5

        if clean in ENGLISH_LEXICON and clean not in LUGANDA_LEXICON:
            return "eng", 0.9
        if clean in LUGANDA_LEXICON and clean not in ENGLISH_LEXICON:
            return "lug", 0.9

        # Bantu morphological rules: Luganda words often begin with typical Bantu prefixes
        # (e.g., 'omu-', 'aba-', 'emi-', 'eki-', 'ebi-', 'oku-') and end in vowels.
        bantu_prefixes = ("omu", "aba", "emi", "eki", "ebi", "oku", "olu", "aka")
        if any(clean.startswith(p) for p in bantu_prefixes) and clean[-1] in "aeiou":
            return "lug", 0.75

        # Words ending in consonant clusters (e.g. -ct, -rt, -th, -ng, -nd) are characteristic of English
        english_endings = ("ct", "rt", "th", "ng", "nd", "st", "ed", "ly", "tion", "ment")
        if any(clean.endswith(e) for e in english_endings):
            return "eng", 0.75

        return self.default_language, 0.5

    def classify_text(self, text: str) -> Tuple[str, float]:
        """Classify the dominant language of a text string."""
        tokens = text.strip().split()
        if not tokens:
            return self.default_language, 1.0

        scores: Dict[str, float] = {"lug": 0.0, "eng": 0.0}
        for token in tokens:
            lang, weight = self._score_word(token)
            scores[lang] = scores.get(lang, 0.0) + weight

        total = sum(scores.values())
        if total == 0:
            return self.default_language, 0.5

        sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        winner_lang, winner_weight = sorted_scores[0]
        confidence = winner_weight / total
        return winner_lang, round(confidence, 3)

    def run(self, input: Union[Result, Resource]) -> Result:
        if not isinstance(input, Result):
            raise ValueError(f"HeuristicLIDComponent expects a Result input, got {type(input).__name__}")

        processed_segments: List[Segment] = []
        code_switch_count = 0

        for seg in input.segments:
            tokens = seg.text.strip().split()
            token_langs = [self._score_word(t)[0] for t in tokens]
            has_mixed_languages = len(set(token_langs)) > 1

            if has_mixed_languages:
                code_switch_count += 1

            # Split segment into sub-segments if word timing exists and splitting is requested
            if self.split_segments and has_mixed_languages and seg.metadata.get("words"):
                words_meta = seg.metadata["words"]
                current_span: List[dict] = []
                current_lang: Optional[str] = None

                for w in words_meta:
                    w_text = w.get("word", "")
                    w_lang, _ = self._score_word(w_text)

                    if current_lang is None or w_lang == current_lang:
                        current_span.append(w)
                        current_lang = w_lang
                    else:
                        span_text = " ".join(item.get("word", "") for item in current_span)
                        processed_segments.append(
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
                        current_span = [w]
                        current_lang = w_lang

                if current_span and current_lang:
                    span_text = " ".join(item.get("word", "") for item in current_span)
                    processed_segments.append(
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
                dominant_lang, conf = self.classify_text(seg.text)
                updated_seg = Segment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text,
                    language=dominant_lang,
                    source_language=seg.source_language or input.source_language,
                    speaker=seg.speaker,
                    confidence=seg.confidence or conf,
                    metadata={
                        **seg.metadata,
                        "lid_confidence": conf,
                        "token_languages": token_langs,
                        "is_code_switched": has_mixed_languages,
                    },
                )
                processed_segments.append(updated_seg)

        res = Result(
            segments=processed_segments,
            source_language=input.source_language,
            target_language=input.target_language,
            warnings=list(input.warnings),
            provenance={**input.provenance, "lid_component": f"{self.name}@{self.version}"},
            artifacts=list(input.artifacts),
            metadata={
                **input.metadata,
                "code_switch_detection": {
                    "detected_switches": code_switch_count,
                    "final_segment_count": len(processed_segments),
                },
            },
        )
        return res
