"""
Unit tests for Milestone 4 — Temporal Alignment components.

Covers:
- DummyForcedAlignmentComponent: word timestamps within segment boundaries
- DurationModellingComponent: duration ratio and target duration calculations
- FittingStrategy enum: all three values exist
- TTS fitting strategies: COMPRESS / SPLIT / SKIP triggered correctly
"""
from __future__ import annotations
import pytest
from lingualdub.components.alignment.forced import (
    DummyForcedAlignmentComponent,
    _distribute_word_timestamps,
)
from lingualdub.components.alignment.duration import (
    DurationModellingComponent,
    _estimate_speech_duration,
)
from lingualdub.components.tts.base import FittingStrategy
from lingualdub.components.tts.dummy import DummyTTSComponent, _choose_strategy
from lingualdub.core.result import Result
from lingualdub.core.segment import Segment


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_segment(text: str, start: float = 0.0, end: float = 3.0, lang: str = "lug", **meta):
    seg = Segment(start=start, end=end, text=text, language=lang)
    seg.metadata.update(meta)
    return seg


def _make_result(*segs, src="lug", tgt="eng"):
    return Result(segments=list(segs), source_language=src, target_language=tgt)


# ─────────────────────────────────────────────────────────────────────────────
# FittingStrategy Enum
# ─────────────────────────────────────────────────────────────────────────────

class TestFittingStrategyEnum:
    def test_all_values_exist(self):
        assert FittingStrategy.COMPRESS == "compress"
        assert FittingStrategy.SPLIT == "split"
        assert FittingStrategy.SKIP == "skip"

    def test_is_string_comparable(self):
        assert FittingStrategy.COMPRESS.value == "compress"
        assert str(FittingStrategy.SKIP.value) == "skip"


# ─────────────────────────────────────────────────────────────────────────────
# _distribute_word_timestamps helper
# ─────────────────────────────────────────────────────────────────────────────

class TestDistributeWordTimestamps:
    def test_empty_words(self):
        result = _distribute_word_timestamps([], 0.0, 3.0)
        assert result == []

    def test_single_word_covers_full_span(self):
        result = _distribute_word_timestamps(["hello"], 1.0, 4.0)
        assert len(result) == 1
        assert result[0]["start"] == pytest.approx(1.0)
        assert result[0]["end"] == pytest.approx(4.0)
        assert result[0]["word"] == "hello"

    def test_all_words_within_segment_bounds(self):
        words = ["Oli", "otya", "nnyabo", "nnyo"]
        seg_start, seg_end = 2.0, 5.0
        timestamps = _distribute_word_timestamps(words, seg_start, seg_end)
        assert len(timestamps) == len(words)
        for ts in timestamps:
            assert ts["start"] >= seg_start - 1e-9
            assert ts["end"] <= seg_end + 1e-9
            assert ts["start"] <= ts["end"]

    def test_last_word_clamps_to_seg_end(self):
        words = ["a", "bb", "ccc"]
        result = _distribute_word_timestamps(words, 0.0, 3.0)
        assert result[-1]["end"] == pytest.approx(3.0)

    def test_monotonically_increasing(self):
        words = ["word1", "word2", "word3", "word4", "word5"]
        result = _distribute_word_timestamps(words, 0.0, 5.0)
        for i in range(1, len(result)):
            assert result[i]["start"] >= result[i - 1]["end"] - 1e-9


# ─────────────────────────────────────────────────────────────────────────────
# DummyForcedAlignmentComponent
# ─────────────────────────────────────────────────────────────────────────────

class TestDummyForcedAlignmentComponent:
    def setup_method(self):
        self.aligner = DummyForcedAlignmentComponent()

    def test_rejects_non_result_input(self):
        from lingualdub.core.resource import Resource, ResourceKind
        r = Resource(id="r1", kind=ResourceKind.SPEECH, language="lug", version="1.0.0")
        with pytest.raises(ValueError):
            self.aligner.run(r)

    def test_word_timestamps_within_segment_boundaries(self):
        seg = _make_segment("Oli otya nnyabo nnyo", start=1.5, end=4.5)
        result = self.aligner.run(_make_result(seg))
        assert len(result.segments) == 1
        out_seg = result.segments[0]
        wts = out_seg.metadata["word_timestamps"]
        assert len(wts) == 4
        for wt in wts:
            assert wt["start"] >= 1.5 - 1e-9
            assert wt["end"] <= 4.5 + 1e-9

    def test_empty_text_segment_has_empty_word_timestamps(self):
        seg = _make_segment("", start=0.0, end=2.0)
        result = self.aligner.run(_make_result(seg))
        wts = result.segments[0].metadata["word_timestamps"]
        assert wts == []

    def test_provenance_contains_aligner_key(self):
        seg = _make_segment("Hello world", start=0.0, end=2.0, lang="eng")
        result = self.aligner.run(_make_result(seg))
        assert "forced_aligner" in result.provenance
        assert "aligner" in result.segments[0].provenance

    def test_aligned_flag_set_in_metadata(self):
        seg = _make_segment("text", start=0.0, end=1.0)
        result = self.aligner.run(_make_result(seg))
        assert result.segments[0].metadata.get("aligned") is True
        assert result.metadata.get("aligned_timestamps") is True

    def test_offline_mode_no_resource_manager(self):
        """Falls back gracefully without ResourceManager — no crash."""
        aligner = DummyForcedAlignmentComponent(resource_manager=None)
        seg = _make_segment("test words", start=0.0, end=2.0)
        result = aligner.run(_make_result(seg))
        assert len(result.segments) == 1

    def test_capability_tokens(self):
        assert "transcription" in self.aligner.requires
        assert "aligned_timestamps" in self.aligner.provides


# ─────────────────────────────────────────────────────────────────────────────
# DurationModellingComponent
# ─────────────────────────────────────────────────────────────────────────────

class TestDurationModellingComponent:
    def setup_method(self):
        self.modeller = DurationModellingComponent()

    def test_rejects_non_result_input(self):
        from lingualdub.core.resource import Resource, ResourceKind
        r = Resource(id="r1", kind=ResourceKind.SPEECH, language="lug", version="1.0.0")
        with pytest.raises(ValueError):
            self.modeller.run(r)

    def test_duration_ratio_and_target_stored_in_metadata(self):
        # 5 words at 2.5 wps = 2.0s expected, source = 2.0s → ratio ≈ 1.0
        seg = _make_segment("Hello world from the test", start=0.0, end=2.0, lang="eng")
        result = self.modeller.run(_make_result(seg, tgt="eng"))
        out = result.segments[0]
        assert "target_duration" in out.metadata
        assert "duration_ratio" in out.metadata
        ratio = out.metadata["duration_ratio"]
        target = out.metadata["target_duration"]
        assert ratio > 0
        assert target > 0

    def test_known_ratio_computation(self):
        # 5 eng words / 2.5 wps = 2.0s estimated; source = 2.0s → ratio = 1.0
        seg = _make_segment("one two three four five", start=0.0, end=2.0, lang="eng")
        result = self.modeller.run(_make_result(seg, tgt="eng"))
        ratio = result.segments[0].metadata["duration_ratio"]
        assert ratio == pytest.approx(1.0, abs=0.05)

    def test_long_translation_gives_high_ratio(self):
        # Many words in a very short source segment → ratio > 1.35
        text = "one two three four five six seven eight nine ten"
        seg = _make_segment(text, start=0.0, end=1.0, lang="eng")
        result = self.modeller.run(_make_result(seg, tgt="eng"))
        ratio = result.segments[0].metadata["duration_ratio"]
        assert ratio > 1.35

    def test_capability_tokens(self):
        assert "translation" in self.modeller.requires
        assert "aligned_timestamps" in self.modeller.requires
        assert "duration_target" in self.modeller.provides

    def test_provenance_set(self):
        seg = _make_segment("hello world", start=0.0, end=1.0, lang="eng")
        result = self.modeller.run(_make_result(seg, tgt="eng"))
        assert "duration_modeller" in result.provenance


# ─────────────────────────────────────────────────────────────────────────────
# TTS Fitting Strategy Selection
# ─────────────────────────────────────────────────────────────────────────────

class TestChooseStrategy:
    def test_compress_for_normal_ratio(self):
        assert _choose_strategy(1.0, "Hello world") == FittingStrategy.COMPRESS

    def test_compress_for_low_ratio(self):
        assert _choose_strategy(0.5, "Short text") == FittingStrategy.COMPRESS

    def test_compress_at_boundary(self):
        assert _choose_strategy(1.35, "Just fits") == FittingStrategy.COMPRESS

    def test_split_for_high_ratio_with_comma(self):
        assert _choose_strategy(1.5, "Hello, world this is a long sentence") == FittingStrategy.SPLIT

    def test_split_for_high_ratio_without_punctuation(self):
        # ratio 1.5 <= 1.75, so SPLIT even without punctuation
        assert _choose_strategy(1.5, "nopunctuation longwordhere") == FittingStrategy.SPLIT

    def test_skip_for_very_high_ratio_no_split(self):
        # ratio > 1.75 and no clause boundaries → SKIP
        assert _choose_strategy(2.0, "verylongwordwithnopunctuationatall") == FittingStrategy.SKIP

    def test_split_for_very_high_ratio_with_comma(self):
        # ratio > 1.75 but has a comma → SPLIT (splittable)
        assert _choose_strategy(2.0, "this is a long sentence, with a clause boundary") == FittingStrategy.SPLIT


class TestDummyTTSStrategies:
    def _make_tts_result(self, text: str, start: float = 0.0, end: float = 3.0,
                         duration_ratio: float = 1.0, target_duration: float = 3.0):
        seg = _make_segment(text, start=start, end=end, lang="eng",
                            duration_ratio=duration_ratio, target_duration=target_duration)
        return _make_result(seg)

    def test_compress_strategy_applied(self, tmp_path):
        tts = DummyTTSComponent(output_dir=str(tmp_path))
        inp = self._make_tts_result("Hello world", duration_ratio=1.0, target_duration=2.5)
        result = tts.run(inp)
        assert any(s.metadata.get("fitting_strategy") == "compress" for s in result.segments)

    def test_split_strategy_applied(self, tmp_path):
        tts = DummyTTSComponent(output_dir=str(tmp_path))
        inp = self._make_tts_result(
            "Hello world, this is a very long sentence for the segment",
            start=0.0, end=2.0,
            duration_ratio=1.5, target_duration=3.0,
        )
        result = tts.run(inp)
        strategies = [s.metadata.get("fitting_strategy") for s in result.segments]
        assert "split" in strategies

    def test_skip_strategy_applied(self, tmp_path):
        tts = DummyTTSComponent(output_dir=str(tmp_path))
        inp = self._make_tts_result(
            "verylongwordwithoutsplitpoints",
            start=0.0, end=1.0,
            duration_ratio=2.5, target_duration=5.0,
        )
        result = tts.run(inp)
        assert any(s.metadata.get("fitting_strategy") == "skip" for s in result.segments)
        assert any(s.metadata.get("unfit") is True for s in result.segments)
        # SKIP segments should have a warning
        assert any("skipped" in w for w in result.warnings)

    def test_fitting_strategy_recorded_for_every_segment(self, tmp_path):
        tts = DummyTTSComponent(output_dir=str(tmp_path))
        segs = [
            _make_segment("Hello world", start=0.0, end=2.0, lang="eng",
                          duration_ratio=1.0, target_duration=2.0),
            _make_segment("A longer translation text here", start=2.0, end=3.5, lang="eng",
                          duration_ratio=1.5, target_duration=4.0),
        ]
        inp = _make_result(*segs, tgt="eng")
        result = tts.run(inp)
        for seg in result.segments:
            assert "fitting_strategy" in seg.metadata

    def test_requires_includes_duration_target(self):
        tts = DummyTTSComponent(require_duration_target=True)
        assert "duration_target" in tts.requires
        assert "translation" in tts.requires

        from lingualdub.components.tts.mms_tts import MMSTTSComponent
        mms = MMSTTSComponent()
        assert "duration_target" in mms.requires
        assert "translation" in mms.requires
