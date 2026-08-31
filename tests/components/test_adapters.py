"""
Unit tests for dummy adapters and evaluation metrics.
"""

from pathlib import Path
from lingualdub.components.asr.dummy import DummyASRComponent
from lingualdub.components.translation.dummy import DummyTranslationComponent
from lingualdub.components.tts.dummy import DummyTTSComponent
from lingualdub.components.eval.metrics import (
    WEREvaluator,
    TranslationEvaluator,
    TemporalAlignmentEvaluator,
    compute_wer,
    compute_cer,
    compute_chrf,
)
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result, ResultStatus
from lingualdub.core.segment import Segment


def test_dummy_asr_from_resource():
    asr = DummyASRComponent(default_text="Oli otya nnyabo", language="lug", duration=2.0)
    res = Resource(id="test_audio", kind=ResourceKind.SPEECH, language="lug", version="1.0.0")
    out = asr.run(res)

    assert isinstance(out, Result)
    assert len(out.segments) == 1
    assert out.segments[0].text == "Oli otya nnyabo"
    assert out.segments[0].language == "lug"
    assert len(out.segments[0].metadata["words"]) == 3


def test_dummy_translation_preserves_speaker():
    trans = DummyTranslationComponent(source_language="lug", target_language="eng")
    inp = Result(
        segments=[
            Segment(start=0.0, end=2.0, text="oli otya", language="lug", speaker="speaker_1", confidence=0.9)
        ],
        source_language="lug",
    )
    out = trans.run(inp)

    assert isinstance(out, Result)
    assert len(out.segments) == 1
    assert out.segments[0].text == "how are you"
    assert out.segments[0].language == "eng"
    assert out.segments[0].source_language == "lug"
    assert out.segments[0].speaker == "speaker_1"


def test_dummy_tts_generates_audio(tmp_path):
    tts = DummyTTSComponent(output_dir=str(tmp_path))
    inp = Result(
        segments=[
            Segment(start=0.0, end=1.5, text="Hello madam", language="eng")
        ],
        source_language="lug",
        target_language="eng",
    )
    out = tts.run(inp)

    assert len(out.artifacts) >= 1
    wav_path = Path(out.artifacts[0])
    assert wav_path.exists()
    assert wav_path.stat().st_size > 0


def test_dummy_tts_degrade(tmp_path):
    tts = DummyTTSComponent(output_dir=str(tmp_path))
    inp = Result(segments=[], source_language="lug")
    out = tts.degrade(inp)

    assert out.status == ResultStatus.DEGRADED
    assert len(out.artifacts) == 1
    assert Path(out.artifacts[0]).exists()


def test_metric_calculations():
    # WER
    assert compute_wer("hello world", "hello world") == 0.0
    assert compute_wer("hello there", "hello world") == 0.5
    assert compute_wer("", "") == 0.0

    # CER
    assert compute_cer("abc", "abc") == 0.0
    assert compute_cer("ab", "abc") == 1 / 3

    # chrF
    assert compute_chrf("hello world", "hello world") == 100.0
    assert 0.0 <= compute_chrf("hello", "world") <= 100.0


def test_evaluators_with_results():
    hyp = Result(
        segments=[Segment(start=0.0, end=2.0, text="hello world", language="eng")],
        provenance={"run_id": "test_hyp"},
    )
    wer_eval = WEREvaluator()
    wer_res = wer_eval.evaluate_pair(hyp, "hello world")
    assert wer_res.metadata["metrics"]["wer"] == 0.0

    trans_eval = TranslationEvaluator()
    trans_res = trans_eval.evaluate_pair(hyp, "hello world")
    assert trans_res.metadata["metrics"]["chrf"] == 100.0

    timing_eval = TemporalAlignmentEvaluator(tolerance_ms=200.0)
    timing_res = timing_eval.run(hyp)
    assert "timing_metrics" in timing_res.metadata
