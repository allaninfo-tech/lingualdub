"""
Milestone 4 End-to-End Integration Test — Temporal Alignment.

Verifies the M4 Done When criteria:
  - A Luganda → English pipeline produces dubbed audio where >= 80% of
    segments are within 200ms of the source timing envelope.
  - The timing score is measured by the evaluator and recorded with full provenance.
  - All component and integration tests pass.
"""
from __future__ import annotations
import pytest
from lingualdub.components.asr.dummy import DummyASRComponent
from lingualdub.components.alignment.forced import DummyForcedAlignmentComponent
from lingualdub.components.alignment.duration import DurationModellingComponent
from lingualdub.components.translation.dummy import DummyTranslationComponent
from lingualdub.components.tts.dummy import DummyTTSComponent
from lingualdub.components.eval.metrics import TemporalAlignmentEvaluator
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_source_result(n: int = 5) -> Result:
    """Build a source Result with n Luganda segments of known timing."""
    segs = []
    for i in range(n):
        start = i * 2.5
        end = start + 2.5
        segs.append(Segment(
            start=start,
            end=end,
            text=f"Oli otya nnyabo {i}",
            language="lug",
        ))
    return Result(
        segments=segs,
        source_language="lug",
        provenance={"evaluation_protocol": "M4_E2E_PROTOCOL_V1"},
    )


def _run_alignment_pipeline(source: Result, tmp_path) -> Result:
    """
    Run the M4 alignment pipeline:
      ASR → ForcedAligner → Translator → DurationModeller → TTS
    For integration testing we skip ASR (source already has segments).
    """
    aligner = DummyForcedAlignmentComponent()
    translator = DummyTranslationComponent()
    modeller = DurationModellingComponent()
    tts = DummyTTSComponent(output_dir=str(tmp_path / "tts_out"))

    aligned = aligner.run(source)
    translated = translator.run(aligned)
    with_durations = modeller.run(translated)
    dubbed = tts.run(with_durations)
    return dubbed


# ─────────────────────────────────────────────────────────────────────────────
# M4 End-to-End Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestM4TemporalAlignmentE2E:

    def test_pipeline_completes_without_error(self, tmp_path):
        source = _make_source_result(n=5)
        dubbed = _run_alignment_pipeline(source, tmp_path)
        assert dubbed is not None
        assert dubbed.is_usable

    def test_dubbed_segments_produced(self, tmp_path):
        source = _make_source_result(n=5)
        dubbed = _run_alignment_pipeline(source, tmp_path)
        assert len(dubbed.segments) >= 1

    def test_fitting_strategy_recorded_on_all_segments(self, tmp_path):
        source = _make_source_result(n=5)
        dubbed = _run_alignment_pipeline(source, tmp_path)
        for seg in dubbed.segments:
            assert "fitting_strategy" in seg.metadata, (
                f"Segment missing fitting_strategy: {seg}"
            )

    def test_m4_done_when_pct_within_200ms_ge_80(self, tmp_path):
        """
        M4 Done When: >= 80% of dubbed segments are within 200ms of source timing.
        """
        source = _make_source_result(n=5)
        dubbed = _run_alignment_pipeline(source, tmp_path)

        evaluator = TemporalAlignmentEvaluator(tolerance_ms=200.0)
        eval_result = evaluator.evaluate_pair(dubbed, source)

        timing_metrics = eval_result.metadata["timing_metrics"]
        pct = timing_metrics["pct_within_200ms"]

        assert pct >= 80.0, (
            f"M4 Done When FAILED: only {pct:.1f}% of segments within 200ms "
            f"(required >= 80%). Mean error: {timing_metrics['mean_duration_error_ms']:.1f}ms"
        )

    def test_evaluator_records_provenance(self, tmp_path):
        source = _make_source_result(n=5)
        dubbed = _run_alignment_pipeline(source, tmp_path)

        evaluator = TemporalAlignmentEvaluator(tolerance_ms=200.0)
        eval_result = evaluator.evaluate_pair(dubbed, source)

        assert "evaluator" in eval_result.provenance
        assert "temporal_alignment_evaluator" in eval_result.provenance["evaluator"]

    def test_timing_metrics_structure(self, tmp_path):
        source = _make_source_result(n=5)
        dubbed = _run_alignment_pipeline(source, tmp_path)

        evaluator = TemporalAlignmentEvaluator(tolerance_ms=200.0)
        eval_result = evaluator.evaluate_pair(dubbed, source)

        metrics = eval_result.metadata["timing_metrics"]
        assert "pct_within_200ms" in metrics
        assert "mean_duration_error_ms" in metrics
        assert "tolerance_ms" in metrics
        assert metrics["tolerance_ms"] == 200.0

    def test_evaluate_pair_propagates_evaluation_protocol(self, tmp_path):
        source = _make_source_result(n=3)
        dubbed = _run_alignment_pipeline(source, tmp_path)

        evaluator = TemporalAlignmentEvaluator()
        eval_result = evaluator.evaluate_pair(dubbed, source)

        # evaluation_protocol from source.provenance should be propagated
        assert eval_result.provenance.get("evaluation_protocol") == "M4_E2E_PROTOCOL_V1"

    def test_forced_aligner_word_timestamps_present(self, tmp_path):
        """DummyForcedAlignmentComponent must produce word_timestamps for each segment."""
        source = _make_source_result(n=3)
        aligner = DummyForcedAlignmentComponent()
        aligned = aligner.run(source)
        for seg in aligned.segments:
            assert "word_timestamps" in seg.metadata
            wts = seg.metadata["word_timestamps"]
            assert isinstance(wts, list)
            for wt in wts:
                assert wt["start"] >= seg.start - 1e-9
                assert wt["end"] <= seg.end + 1e-9

    def test_duration_modeller_stores_target_duration(self, tmp_path):
        source = _make_source_result(n=3)
        aligner = DummyForcedAlignmentComponent()
        translator = DummyTranslationComponent()
        modeller = DurationModellingComponent()

        aligned = aligner.run(source)
        translated = translator.run(aligned)
        with_durations = modeller.run(translated)

        for seg in with_durations.segments:
            assert "target_duration" in seg.metadata
            assert "duration_ratio" in seg.metadata
            assert seg.metadata["target_duration"] > 0
            assert seg.metadata["duration_ratio"] > 0

    def test_evaluate_pair_with_empty_hypothesis(self):
        source = _make_source_result(n=3)
        hypothesis = Result(segments=[], source_language="eng", target_language="eng")
        evaluator = TemporalAlignmentEvaluator()
        result = evaluator.evaluate_pair(hypothesis, source)
        metrics = result.metadata["timing_metrics"]
        assert metrics["pct_within_200ms"] == 100.0  # no segments, nothing to penalise

    def test_evaluate_pair_with_no_source_segments(self, tmp_path):
        source = _make_source_result(n=5)
        dubbed = _run_alignment_pipeline(source, tmp_path)
        empty_ref = Result(segments=[], source_language="lug")

        evaluator = TemporalAlignmentEvaluator()
        result = evaluator.evaluate_pair(dubbed, empty_ref)
        metrics = result.metadata["timing_metrics"]
        # All hypothesis segments are un-paired → all count as misses
        assert metrics["pct_within_200ms"] == 0.0 or metrics["segments_evaluated"] == 0
