"""
Unit tests for Milestone 7 — Audio-Visual Synchronisation.

Covers:
- AVSyncEvaluator: mean offset, pct_within_100ms, split handling, provenance
- DialogueTimingComponent: cue snapping, fallback, provenance
- VideoMergerComponent: artifact generation, provenance, degrade
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lingualdub.components.av_sync.dialogue_timing import DialogueTimingComponent
from lingualdub.components.av_sync.video_merger import VideoMergerComponent
from lingualdub.components.eval.av_sync import AVSyncEvaluator
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _seg(text: str, start: float, end: float, lang: str = "lug", **meta):
    s = Segment(start=start, end=end, text=text, language=lang)
    s.metadata.update(meta)
    return s


def _res(*segs, src="lug", tgt="eng", prov=None):
    return Result(segments=list(segs), source_language=src, target_language=tgt, provenance=prov or {})


# ─────────────────────────────────────────────────────────────────────────────
# AVSyncEvaluator
# ─────────────────────────────────────────────────────────────────────────────

class TestAVSyncEvaluator:
    def test_evaluate_pair_perfect_alignment(self):
        src = _res(_seg("a", 0, 2.5, lang="lug"), _seg("b", 2.5, 5.0, lang="lug"), prov={"evaluation_protocol": "AV_SYNC_PROTOCOL_V1"})
        hyp = _res(_seg("a", 0, 2.5, lang="eng"), _seg("b", 2.5, 5.0, lang="eng"), prov={})
        ev = AVSyncEvaluator(tolerance_ms=100)
        out = ev.evaluate_pair(hyp, src)
        m = out.metadata["av_sync_metrics"]
        assert m["mean_av_offset_ms"] == pytest.approx(0.0, abs=1e-6)
        assert m["pct_within_100ms"] == pytest.approx(100.0, abs=1e-6)

    def test_evaluate_pair_offset_computation(self):
        src = _res(_seg("a", 0, 2.5, lang="lug"), _seg("b", 2.5, 5.0, lang="lug"))
        # 50ms and 120ms offsets
        hyp = _res(_seg("a", 0, 2.55, lang="eng"), _seg("b", 2.55, 5.12, lang="eng"))
        ev = AVSyncEvaluator(tolerance_ms=100)
        out = ev.evaluate_pair(hyp, src)
        m = out.metadata["av_sync_metrics"]
        # offsets: 50ms, 120ms -> mean 85ms, pct within 100ms = 50%
        assert m["mean_av_offset_ms"] == pytest.approx(85.0, abs=0.1)
        assert m["pct_within_100ms"] == pytest.approx(50.0, abs=0.1)

    def test_evaluate_pair_with_split_subsegments(self):
        src = _res(_seg("a", 0, 5.0, lang="lug"))
        # Simulate SPLIT: two subsegments with source_segment_index 0
        s1 = _seg("part1", 0, 2.5, lang="eng", source_segment_index=0, fitting_strategy="split")
        s2 = _seg("part2", 2.5, 5.02, lang="eng", source_segment_index=0, fitting_strategy="split")
        hyp = _res(s1, s2)
        src_single = _res(_seg("a", 0, 5.0, lang="lug"))
        ev = AVSyncEvaluator(tolerance_ms=100)
        out = ev.evaluate_pair(hyp, src_single)
        m = out.metadata["av_sync_metrics"]
        # Final hyp end 5.02 vs src 5.0 -> 20ms offset, within tolerance
        assert m["mean_av_offset_ms"] == pytest.approx(20.0, abs=1.0)
        assert m["pct_within_100ms"] == 100.0

    def test_evaluate_pair_unfit_penalised(self):
        src = _res(_seg("a", 0, 2.5, lang="lug"))
        hyp = _res(_seg("a", 0, 2.5, lang="eng", fitting_strategy="skip", unfit=True))
        ev = AVSyncEvaluator(tolerance_ms=100)
        out = ev.evaluate_pair(hyp, src)
        m = out.metadata["av_sync_metrics"]
        assert m["pct_within_100ms"] == 0.0
        assert m["mean_av_offset_ms"] > 100

    def test_evaluate_pair_empty_hypothesis(self):
        src = _res(_seg("a", 0, 2.5, lang="lug"), _seg("b", 2.5, 5.0, lang="lug"))
        hyp = _res()
        ev = AVSyncEvaluator(tolerance_ms=100)
        out = ev.evaluate_pair(hyp, src)
        m = out.metadata["av_sync_metrics"]
        assert m["pct_within_100ms"] == 0.0
        assert m["total_dubbed_segments"] == 0
        assert m["total_source_segments"] == 2

    def test_evaluate_pair_empty_both(self):
        ev = AVSyncEvaluator()
        out = ev.evaluate_pair(_res(), _res())
        m = out.metadata["av_sync_metrics"]
        assert m["mean_av_offset_ms"] == 0.0
        assert m["pct_within_100ms"] == 100.0

    def test_evaluate_pair_provenance(self):
        src = _res(_seg("a", 0, 1.0, lang="lug"), prov={"evaluation_protocol": "AV_SYNC_PROTOCOL_V1", "dataset_version": "1.0.0"})
        hyp = _res(_seg("a", 0, 1.0, lang="eng"))
        ev = AVSyncEvaluator(version="1.0.0")
        out = ev.evaluate_pair(hyp, src)
        assert "evaluator" in out.provenance
        assert "av_sync_evaluator" in out.provenance["evaluator"]
        assert out.provenance["evaluation_protocol"] == "AV_SYNC_PROTOCOL_V1"
        assert out.provenance["dataset_version"] == "1.0.0"

    def test_run_single_result(self):
        seg = _seg("hello", 0, 2.0, lang="eng", target_duration=2.0)
        inp = _res(seg)
        ev = AVSyncEvaluator(tolerance_ms=100)
        out = ev.run(inp)
        m = out.metadata["av_sync_metrics"]
        assert m["mean_av_offset_ms"] == pytest.approx(0.0, abs=1e-6)
        assert m["pct_within_100ms"] == 100.0

    def test_run_with_av_offset_metadata(self):
        seg = _seg("hello", 0, 2.0, lang="eng", av_offset_ms=80)
        inp = _res(seg)
        ev = AVSyncEvaluator(tolerance_ms=100)
        out = ev.run(inp)
        assert out.metadata["av_sync_metrics"]["mean_av_offset_ms"] == pytest.approx(80.0, abs=1e-6)

    def test_capability_tokens(self):
        ev = AVSyncEvaluator()
        assert "dubbed_video" in ev.requires
        assert "av_sync_metrics" in ev.provides

    def test_compare_runs_delta(self):
        from lingualdub.utils.comparison import compare_runs
        src = _res(_seg("a", 0, 2.5, lang="lug"))
        hyp_base = _res(_seg("a", 0, 2.65, lang="eng"), prov={"dataset_version": "1.0.0"})  # 150ms offset
        hyp_cand = _res(_seg("a", 0, 2.52, lang="eng"), prov={"dataset_version": "1.0.0"})  # 20ms
        ev = AVSyncEvaluator(tolerance_ms=100)
        base = ev.evaluate_pair(hyp_base, src)
        cand = ev.evaluate_pair(hyp_cand, src)
        base.provenance["dataset_version"] = "1.0.0"
        cand.provenance["dataset_version"] = "1.0.0"
        deltas = compare_runs(base, cand)
        assert "mean_av_offset_ms_delta" in deltas["deltas"]
        assert deltas["deltas"]["mean_av_offset_ms_delta"] < 0  # candidate better (lower offset)


# ─────────────────────────────────────────────────────────────────────────────
# DialogueTimingComponent
# ─────────────────────────────────────────────────────────────────────────────

class TestDialogueTimingComponent:
    def setup_method(self):
        self.comp = DialogueTimingComponent(snap_tolerance=0.15)

    def test_rejects_non_result(self):
        from lingualdub.core.resource import Resource, ResourceKind
        r = Resource(id="r1", kind=ResourceKind.SPEECH, language="lug", version="1.0.0")
        with pytest.raises(ValueError):
            self.comp.run(r)

    def test_snap_within_tolerance(self):
        # source cues at 0.0, 2.5, 5.0; segments slightly off should snap
        src = _res(
            _seg("a", 0.1, 2.48, lang="lug"),
            _seg("b", 2.52, 5.03, lang="lug"),
            prov={"video_cues": [0.0, 2.5, 5.0]},
        )
        from lingualdub.components.alignment.forced import DummyForcedAlignmentComponent
        aligned = DummyForcedAlignmentComponent().run(src)
        out = self.comp.run(aligned)
        assert out.segments[0].start == pytest.approx(0.0, abs=0.02)
        assert out.segments[0].end == pytest.approx(2.5, abs=0.02)
        assert out.segments[0].metadata["dialogue_timing_applied"] is True

    def test_no_snap_beyond_tolerance(self):
        src = _res(_seg("a", 0, 2.5, lang="lug"), prov={"video_cues": [10.0]})  # far cue
        from lingualdub.components.alignment.forced import DummyForcedAlignmentComponent
        aligned = DummyForcedAlignmentComponent().run(src)
        out = self.comp.run(aligned)
        assert out.segments[0].start == pytest.approx(0.0, abs=1e-6)
        assert out.segments[0].end == pytest.approx(2.5, abs=1e-6)
        assert out.segments[0].metadata["dialogue_timing_applied"] is False

    def test_no_cues_noop(self):
        src = _res(_seg("a", 0, 2.5, lang="lug"))
        from lingualdub.components.alignment.forced import DummyForcedAlignmentComponent
        aligned = DummyForcedAlignmentComponent().run(src)
        out = self.comp.run(aligned)
        assert out.segments[0].start == pytest.approx(0.0, abs=1e-6)
        assert out.metadata["dialogue_cues"] == []

    def test_provenance_and_metadata(self):
        src = _res(_seg("a", 0, 2.5, lang="lug"), prov={"video_cues": [0.0, 2.5]})
        from lingualdub.components.alignment.forced import DummyForcedAlignmentComponent
        aligned = DummyForcedAlignmentComponent().run(src)
        out = self.comp.run(aligned)
        assert "dialogue_timing" in out.provenance
        assert out.metadata.get("av_aligned_timestamps") is True
        assert "dialogue_timing" in out.metadata

    def test_preserves_duration_target(self):
        from lingualdub.components.alignment.duration import DurationModellingComponent
        from lingualdub.components.alignment.forced import DummyForcedAlignmentComponent
        src = _res(_seg("hello world", 0, 2.0, lang="eng"), prov={"video_cues": [0.0, 2.0]})
        aligned = DummyForcedAlignmentComponent().run(src)
        # Need translation step for duration modeller; use eng target
        from lingualdub.components.translation.dummy import DummyTranslationComponent
        translated = DummyTranslationComponent(source_language="lug", target_language="eng").run(aligned)
        modeller = DurationModellingComponent()
        with_dur = modeller.run(translated)
        out = self.comp.run(with_dur)
        assert "target_duration" in out.segments[0].metadata

    def test_capability_tokens(self):
        assert "aligned_timestamps" in self.comp.requires
        assert "dialogue_timing" in self.comp.provides
        assert "av_aligned_timestamps" in self.comp.provides


# ─────────────────────────────────────────────────────────────────────────────
# VideoMergerComponent
# ─────────────────────────────────────────────────────────────────────────────

class TestVideoMergerComponent:
    def test_rejects_non_result(self):
        from lingualdub.core.resource import Resource, ResourceKind
        r = Resource(id="r1", kind=ResourceKind.SPEECH, language="lug", version="1.0.0")
        comp = VideoMergerComponent(output_dir="/tmp/test_video_reject")
        with pytest.raises(ValueError):
            comp.run(r)

    def test_produces_artifact_and_provenance(self, tmp_path):
        seg = _seg("hello world", 0, 2.0, lang="eng", target_duration=2.0)
        inp = _res(seg, prov={"consent_basis": "research", "source_video": str(tmp_path / "dummy.mp4")})
        # Create dummy source video
        dummy_vid = tmp_path / "dummy.mp4"
        dummy_vid.write_bytes(b"fake video")
        # Add dummy audio artifact via TTS
        from lingualdub.components.tts.dummy import DummyTTSComponent
        # Ensure consent
        inp.provenance["consent_basis"] = "research"
        tts = DummyTTSComponent(output_dir=str(tmp_path / "tts_tmp"))
        with_audio = tts.run(inp)
        comp = VideoMergerComponent(output_dir=str(tmp_path / "video_out"))
        out = comp.run(with_audio)
        assert len(out.artifacts) >= 1
        video_art = [a for a in out.artifacts if a.endswith(".mp4")]
        assert len(video_art) == 1
        assert Path(video_art[0]).exists()
        assert "video_merger" in out.provenance
        assert "dubbed_video" in out.provenance
        assert "dubbed_video" in out.metadata

    def test_degrade_path(self, tmp_path):
        seg = _seg("hello", 0, 1.0, lang="eng")
        inp = _res(seg, prov={"consent_basis": "research"})
        comp = VideoMergerComponent(output_dir=str(tmp_path / "degrade"))
        out = comp.degrade(inp)
        assert out.status.value == "degraded"
        assert any(a.endswith(".mp4") for a in out.artifacts)

    def test_handles_no_segments(self, tmp_path):
        inp = _res(prov={"consent_basis": "research"})
        comp = VideoMergerComponent(output_dir=str(tmp_path / "no_seg"))
        out = comp.run(inp)
        assert len(out.artifacts) >= 1
        assert Path(out.artifacts[-1]).exists()

    def test_capability_tokens(self):
        comp = VideoMergerComponent()
        assert "synthesised_audio" in comp.requires
        assert "dubbed_video" in comp.provides

    def test_output_deterministic_hash(self, tmp_path):
        seg = _seg("hello world", 0, 2.0, lang="eng")
        inp = _res(seg, prov={"consent_basis": "research", "source_video": "/tmp/fake.mp4"})
        comp = VideoMergerComponent(output_dir=str(tmp_path / "hash_test"))
        out1 = comp.run(inp)
        out2 = comp.run(inp)
        # Same input -> same output path (content hash)
        assert out1.artifacts[-1] == out2.artifacts[-1]
