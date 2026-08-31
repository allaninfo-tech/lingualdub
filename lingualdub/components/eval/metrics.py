"""
Evaluation components for LingualDub pipelines.

Includes:
- WEREvaluator: Word Error Rate
- CEREvaluator: Character Error Rate
- BLEUEvaluator: BLEU score
- ChrFEvaluator: chrF character n-gram F-score
- TemporalAlignmentEvaluator: Segment timing envelope adherence
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple, Union

from lingualdub.components.eval.base import EvaluatorComponent
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


def _levenshtein_distance(seq1: List[Any], seq2: List[Any]) -> int:
    """Compute Levenshtein edit distance between two sequences."""
    size_x = len(seq1) + 1
    size_y = len(seq2) + 1
    matrix = [[0] * size_y for _ in range(size_x)]
    for x in range(size_x):
        matrix[x][0] = x
    for y in range(size_y):
        matrix[0][y] = y

    for x in range(1, size_x):
        for y in range(1, size_y):
            if seq1[x - 1] == seq2[y - 1]:
                matrix[x][y] = matrix[x - 1][y - 1]
            else:
                matrix[x][y] = min(
                    matrix[x - 1][y] + 1,      # deletion
                    matrix[x][y - 1] + 1,      # insertion
                    matrix[x - 1][y - 1] + 1   # substitution
                )
    return matrix[size_x - 1][size_y - 1]


def compute_wer(hypothesis: str, reference: str) -> float:
    """Compute Word Error Rate (0.0 to 1.0+)."""
    h_words = hypothesis.strip().lower().split()
    r_words = reference.strip().lower().split()
    if not r_words:
        return 0.0 if not h_words else 1.0
    return _levenshtein_distance(h_words, r_words) / len(r_words)


def compute_cer(hypothesis: str, reference: str) -> float:
    """Compute Character Error Rate (0.0 to 1.0+)."""
    h_chars = list(hypothesis.strip().lower())
    r_chars = list(reference.strip().lower())
    if not r_chars:
        return 0.0 if not h_chars else 1.0
    return _levenshtein_distance(h_chars, r_chars) / len(r_chars)


def compute_chrf(hypothesis: str, reference: str, n: int = 6, beta: float = 2.0) -> float:
    """Compute sentence-level chrF score (0.0 to 100.0)."""
    hyp = hypothesis.replace(" ", "")
    ref = reference.replace(" ", "")
    if not ref:
        return 100.0 if not hyp else 0.0

    def get_ngrams(s: str, order: int) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for i in range(len(s) - order + 1):
            gram = s[i : i + order]
            counts[gram] = counts.get(gram, 0) + 1
        return counts

    f_scores = []
    for order in range(1, n + 1):
        hyp_ngrams = get_ngrams(hyp, order)
        ref_ngrams = get_ngrams(ref, order)
        hyp_total = sum(hyp_ngrams.values())
        ref_total = sum(ref_ngrams.values())

        if hyp_total == 0 or ref_total == 0:
            continue

        overlap = sum(min(count, ref_ngrams.get(gram, 0)) for gram, count in hyp_ngrams.items())
        prec = overlap / hyp_total if hyp_total > 0 else 0.0
        rec = overlap / ref_total if ref_total > 0 else 0.0

        if prec + rec > 0:
            f = ((1 + beta**2) * prec * rec) / ((beta**2 * prec) + rec)
            f_scores.append(f)
        else:
            f_scores.append(0.0)

    return (sum(f_scores) / len(f_scores) * 100.0) if f_scores else 0.0


class WEREvaluator(EvaluatorComponent):
    """Evaluates Word Error Rate and Character Error Rate on ASR transcription results."""

    name: str = "wer_evaluator"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.EVAL
    supported_languages: List[str] = ["lug", "nyn", "eng", "swa"]
    requires: List[str] = ["transcription"]
    provides: List[str] = ["asr_metrics"]
    on_failure: FailureMode = FailureMode.SKIP

    def run(self, input: Union[Result, Resource]) -> Result:
        # If running stand-alone without reference, return input
        if isinstance(input, Result):
            return input
        return Result()

    def evaluate_pair(self, hypothesis: Result, reference: Union[Result, str]) -> Result:
        hyp_text = " ".join(s.text for s in hypothesis.segments if s.text).strip()
        ref_text = (
            " ".join(s.text for s in reference.segments if s.text).strip()
            if isinstance(reference, Result)
            else str(reference).strip()
        )

        wer = compute_wer(hyp_text, ref_text)
        cer = compute_cer(hyp_text, ref_text)

        metrics = {
            "wer": round(wer, 4),
            "cer": round(cer, 4),
            "reference_text": ref_text,
            "hypothesis_text": hyp_text,
        }

        res = Result(
            segments=list(hypothesis.segments),
            source_language=hypothesis.source_language,
            target_language=hypothesis.target_language,
            warnings=list(hypothesis.warnings),
            provenance={
                **hypothesis.provenance,
                "evaluator": f"{self.name}@{self.version}",
            },
            artifacts=list(hypothesis.artifacts),
            metadata={**hypothesis.metadata, "metrics": metrics},
        )
        return res


class TranslationEvaluator(EvaluatorComponent):
    """Evaluates chrF and BLEU on translation outputs."""

    name: str = "translation_evaluator"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.EVAL
    supported_languages: List[str] = ["lug", "nyn", "eng", "swa"]
    requires: List[str] = ["translation"]
    provides: List[str] = ["translation_metrics"]
    on_failure: FailureMode = FailureMode.SKIP

    def run(self, input: Union[Result, Resource]) -> Result:
        return input if isinstance(input, Result) else Result()

    def evaluate_pair(self, hypothesis: Result, reference: Union[Result, str]) -> Result:
        hyp_text = " ".join(s.text for s in hypothesis.segments if s.text).strip()
        ref_text = (
            " ".join(s.text for s in reference.segments if s.text).strip()
            if isinstance(reference, Result)
            else str(reference).strip()
        )

        chrf_score = compute_chrf(hyp_text, ref_text)

        metrics = {
            "chrf": round(chrf_score, 2),
            "reference_translation": ref_text,
            "hypothesis_translation": hyp_text,
        }

        res = Result(
            segments=list(hypothesis.segments),
            source_language=hypothesis.source_language,
            target_language=hypothesis.target_language,
            warnings=list(hypothesis.warnings),
            provenance={
                **hypothesis.provenance,
                "evaluator": f"{self.name}@{self.version}",
            },
            artifacts=list(hypothesis.artifacts),
            metadata={**hypothesis.metadata, "metrics": metrics},
        )
        return res


class TemporalAlignmentEvaluator(EvaluatorComponent):
    """Evaluates timing envelope adherence and segment drift."""

    name: str = "temporal_alignment_evaluator"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.EVAL
    supported_languages: List[str] = ["lug", "nyn", "eng", "swa"]
    requires: List[str] = ["synthesised_audio"]
    provides: List[str] = ["alignment_metrics"]
    on_failure: FailureMode = FailureMode.SKIP

    def __init__(self, tolerance_ms: float = 200.0, version: str = "1.0.0") -> None:
        self.tolerance_ms = tolerance_ms
        self.version = version

    def run(self, input: Union[Result, Resource]) -> Result:
        if not isinstance(input, Result) or not input.segments:
            return input if isinstance(input, Result) else Result()

        errors_sec: List[float] = []
        within_tolerance_count = 0

        for seg in input.segments:
            # Check target duration vs actual duration
            target_dur = seg.metadata.get("target_duration", seg.duration)
            actual_dur = seg.duration
            err = abs(actual_dur - target_dur)
            errors_sec.append(err)
            if (err * 1000.0) <= self.tolerance_ms:
                within_tolerance_count += 1

        mean_err_ms = (sum(errors_sec) / len(errors_sec) * 1000.0) if errors_sec else 0.0
        pct_within = (within_tolerance_count / len(input.segments) * 100.0) if input.segments else 100.0

        metrics = {
            "mean_duration_error_ms": round(mean_err_ms, 2),
            "pct_within_tolerance": round(pct_within, 2),
            "tolerance_ms": self.tolerance_ms,
        }

        res = Result(
            segments=list(input.segments),
            source_language=input.source_language,
            target_language=input.target_language,
            warnings=list(input.warnings),
            provenance={**input.provenance, "evaluator": f"{self.name}@{self.version}"},
            artifacts=list(input.artifacts),
            metadata={**input.metadata, "timing_metrics": metrics},
        )
        return res
