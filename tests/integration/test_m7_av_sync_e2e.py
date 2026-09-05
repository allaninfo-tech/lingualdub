"""
Milestone 7 End-to-End Integration Test — Audio-Visual Synchronisation.

Verifies M7 Done When criteria:
  - Source video (Luganda audio) -> pipeline -> dubbed video (English audio)
    where mean AV offset <= 100ms across segments
  - Video artifact registered with full provenance (component versions, run_id,
    source video ref)
  - AV sync evaluator test passes
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from lingualdub.components.alignment.duration import DurationModellingComponent
from lingualdub.components.alignment.forced import DummyForcedAlignmentComponent
from lingualdub.components.av_sync.dialogue_timing import DialogueTimingComponent
from lingualdub.components.av_sync.video_merger import VideoMergerComponent
from lingualdub.components.eval.av_sync import AVSyncEvaluator
from lingualdub.components.translation.dummy import DummyTranslationComponent
from lingualdub.components.tts.dummy import DummyTTSComponent
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment
from lingualdub.pipeline.executor import PipelineExecutor


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_source_result(n: int = 5, with_video_cues: bool = True) -> Result:
    """Build a source Result with n Luganda segments of known timing."""
    segs = []
    for i in range(n):
        start = i * 2.5
        end = start + 2.5
        segs.append(Segment(start=start, end=end, text=f"Oli otya nnyabo {i}", language="lug"))
    prov = {"evaluation_protocol": "AV_SYNC_PROTOCOL_V1", "consent_basis": "research", "source_video": "/tmp/dummy_source.mp4"}
    if with_video_cues:
        # Use perfect cues aligned to segment boundaries for deterministic 0 offset
        cues = [i * 2.5 for i in range(n + 1)]
        prov["video_cues"] = cues
    return Result(segments=segs, source_language="lug", provenance=prov)


def _run_av_pipeline(source: Result, tmp_path: Path) -> Result:
    """
    Run the M7 AV-sync pipeline:
      ForcedAligner -> Translator -> DurationModeller -> DialogueTiming -> TTS -> VideoMerger
    Source already has segments; TTS and VideoMerger use dummy offline paths.
    """
    aligner = DummyForcedAlignmentComponent()
    translator = DummyTranslationComponent()
    modeller = DurationModellingComponent()
    dialogue = DialogueTimingComponent(snap_tolerance=0.15)
    tts = DummyTTSComponent(output_dir=str(tmp_path / "tts_out"))
    merger = VideoMergerComponent(output_dir=str(tmp_path / "video_out"))

    aligned = aligner.run(source)
    translated = translator.run(aligned)
    with_durations = modeller.run(translated)
    # Ensure consent for TTS/video merger (voice)
    with_durations.provenance["consent_basis"] = "research"
    with_dialogue = dialogue.run(with_durations)
    dubbed = tts.run(with_dialogue)
    # Propagate source_video for merger
    dubbed.provenance["source_video"] = source.provenance.get("source_video", "/tmp/dummy_source.mp4")
    dubbed.provenance["video_cues"] = source.provenance.get("video_cues", [])
    # Create dummy source video file if not exists for merger to find
    dummy_video = Path("/tmp/dummy_source.mp4")
    if not dummy_video.exists():
        dummy_video.write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00dummy")
    video_dubbed = merger.run(dubbed)
    return video_dubbed


# ─────────────────────────────────────────────────────────────────────────────
# M7 End-to-End Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestM7AVSyncE2E:
    def test_pipeline_completes_without_error(self, tmp_path):
        source = _make_source_result(n=5)
        dubbed = _run_av_pipeline(source, tmp_path)
        assert dubbed is not None
        assert dubbed.is_usable

    def test_dubbed_segments_produced(self, tmp_path):
        source = _make_source_result(n=5)
        dubbed = _run_av_pipeline(source, tmp_path)
        assert len(dubbed.segments) >= 1

    def test_dialogue_timing_applied(self, tmp_path):
        source = _make_source_result(n=5)
        dubbed = _run_av_pipeline(source, tmp_path)
        # Dialogue timing should have marked segments
        for seg in dubbed.segments:
            assert "dialogue_timing_applied" in seg.metadata or "dubbed_video" in seg.metadata

    def test_video_artifact_produced_with_provenance(self, tmp_path):
        source = _make_source_result(n=5)
        dubbed = _run_av_pipeline(source, tmp_path)
        assert len(dubbed.artifacts) >= 1
        # Last artifact should be the dubbed video
        video_artifacts = [a for a in dubbed.artifacts if str(a).endswith(".mp4")]
        assert len(video_artifacts) >= 1
        video_path = Path(video_artifacts[-1])
        assert video_path.exists()
        # Provenance must contain video_merger and source_video_ref
        assert "video_merger" in dubbed.provenance
        assert "dubbed_video" in dubbed.provenance
        assert "source_video" in dubbed.provenance or "source_video_ref" in dubbed.provenance

    def test_m7_done_when_mean_av_offset_le_100ms(self, tmp_path):
        """
        M7 Done When: mean AV offset <= 100ms across segments.
        Uses AVSyncEvaluator with tolerance 100ms.
        """
        source = _make_source_result(n=5)
        dubbed = _run_av_pipeline(source, tmp_path)

        evaluator = AVSyncEvaluator(tolerance_ms=100.0)
        eval_result = evaluator.evaluate_pair(dubbed, source)

        metrics = eval_result.metadata["av_sync_metrics"]
        mean_offset = metrics["mean_av_offset_ms"]
        assert mean_offset <= 100.0, (
            f"M7 Done When FAILED: mean AV offset {mean_offset:.1f}ms > 100ms "
            f"(pct within 100ms: {metrics['pct_within_100ms']:.1f}%)"
        )

    def test_m7_pct_within_100ms_ge_80(self, tmp_path):
        source = _make_source_result(n=5)
        dubbed = _run_av_pipeline(source, tmp_path)
        evaluator = AVSyncEvaluator(tolerance_ms=100.0)
        eval_result = evaluator.evaluate_pair(dubbed, source)
        pct = eval_result.metadata["av_sync_metrics"]["pct_within_100ms"]
        assert pct >= 80.0, f"Expected >=80% within 100ms, got {pct:.1f}%"

    def test_evaluator_records_provenance(self, tmp_path):
        source = _make_source_result(n=5)
        dubbed = _run_av_pipeline(source, tmp_path)
        evaluator = AVSyncEvaluator(tolerance_ms=100.0)
        eval_result = evaluator.evaluate_pair(dubbed, source)
        assert "evaluator" in eval_result.provenance
        assert "av_sync_evaluator" in eval_result.provenance["evaluator"]

    def test_av_metrics_structure(self, tmp_path):
        source = _make_source_result(n=5)
        dubbed = _run_av_pipeline(source, tmp_path)
        evaluator = AVSyncEvaluator(tolerance_ms=100.0)
        eval_result = evaluator.evaluate_pair(dubbed, source)
        metrics = eval_result.metadata["av_sync_metrics"]
        assert "mean_av_offset_ms" in metrics
        assert "pct_within_100ms" in metrics
        assert "tolerance_ms" in metrics
        assert metrics["tolerance_ms"] == 100.0
        assert "segments_evaluated" in metrics

    def test_evaluate_pair_propagates_evaluation_protocol(self, tmp_path):
        source = _make_source_result(n=3)
        dubbed = _run_av_pipeline(source, tmp_path)
        evaluator = AVSyncEvaluator()
        eval_result = evaluator.evaluate_pair(dubbed, source)
        assert eval_result.provenance.get("evaluation_protocol") == "AV_SYNC_PROTOCOL_V1"

    def test_full_pipeline_via_executor(self, tmp_path):
        """Test M7 pipeline assembled as Pipeline and run via PipelineExecutor."""
        # Create dummy source video file for executor path
        dummy_video = tmp_path / "source.mp4"
        dummy_video.write_bytes(b"\x00\x00\x00\x18ftypisom dummy video")
        # Build pipeline via Pipeline object (assembly-time capability check)
        from lingualdub.components.asr.dummy import DummyASRComponent

        asr = DummyASRComponent(default_text="Oli otya nnyabo", language="lug")
        aligner = DummyForcedAlignmentComponent()
        translator = DummyTranslationComponent()
        modeller = DurationModellingComponent()
        dialogue = DialogueTimingComponent()
        tts = DummyTTSComponent(output_dir=str(tmp_path / "tts_exec"))
        merger = VideoMergerComponent(output_dir=str(tmp_path / "video_exec"))

        pipeline = Pipeline(
            stages=[asr, aligner, translator, modeller, dialogue, tts, merger],
            source_language="lug",
            target_language="eng",
            name="m7_executor_test_pipeline",
            on_stage_failure=merger.on_failure,
        )
        # Input resource with video provenance
        res = Resource(
            id="test_video_audio",
            kind=ResourceKind.SPEECH,
            language="lug",
            version="1.0.0",
            provenance={"consent_basis": "research", "source_video": str(dummy_video), "video_cues": [0.0, 2.5, 5.0]},
        )
        # Pre-create a Result with segments to simulate ASR output? Pipeline first stage is aligner which expects Result,
        # so we feed a Result directly (executor handles Resource->ASR dummy anyway)
        # Use executor.run with Resource; DummyForcedAligner will fail if given Resource (expects Result)
        # So feed a Result with source segments + video provenance
        source_result = Result(
            segments=[Segment(start=0, end=2.5, text="Oli otya", language="lug")],
            source_language="lug",
            provenance={"consent_basis": "research", "source_video": str(dummy_video), "video_cues": [0.0, 2.5]},
        )
        executor = PipelineExecutor(pipeline)
        result = executor.run(source_result)
        assert result.is_usable
        assert any(a.endswith(".mp4") for a in result.artifacts)
        assert "video_merger" in result.provenance

    def test_evaluate_pair_with_empty_hypothesis(self):
        source = _make_source_result(n=3)
        hypothesis = Result(segments=[], source_language="eng")
        evaluator = AVSyncEvaluator()
        result = evaluator.evaluate_pair(hypothesis, source)
        metrics = result.metadata["av_sync_metrics"]
        assert metrics["pct_within_100ms"] == 0.0
        assert metrics["total_dubbed_segments"] == 0
        assert metrics["total_source_segments"] == 3

    def test_evaluate_pair_with_no_source_segments(self, tmp_path):
        source = _make_source_result(n=5)
        dubbed = _run_av_pipeline(source, tmp_path)
        empty_ref = Result(segments=[], source_language="lug", provenance={"evaluation_protocol": "AV_SYNC_PROTOCOL_V1"})
        evaluator = AVSyncEvaluator()
        result = evaluator.evaluate_pair(dubbed, empty_ref)
        # With empty reference, all hypothesis segments are extra -> penalised
        # Should still produce metrics (not crash)
        assert "av_sync_metrics" in result.metadata

    def test_video_merger_degrade_path(self, tmp_path):
        """VideoMerger degrade should produce dummy video and mark degraded."""
        source = _make_source_result(n=2)
        dubbed = _run_av_pipeline(source, tmp_path)
        merger = VideoMergerComponent(output_dir=str(tmp_path / "degrade_test"))
        degraded = merger.degrade(dubbed)
        assert degraded.status.value == "degraded"
        assert any(a.endswith(".mp4") for a in degraded.artifacts)
