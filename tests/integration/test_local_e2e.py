"""
Level 2 Integration Tests: Local end-to-end pipeline execution with zero-dependency adapters.
"""

from pathlib import Path
from lingualdub.components.asr.dummy import DummyASRComponent
from lingualdub.components.translation.dummy import DummyTranslationComponent
from lingualdub.components.tts.dummy import DummyTTSComponent
from lingualdub.components.eval.metrics import WEREvaluator, TranslationEvaluator, TemporalAlignmentEvaluator
from lingualdub.core.component import FailureMode
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import ResultStatus
from lingualdub.pipeline.executor import PipelineExecutor


def test_full_local_dubbing_pipeline_e2e(tmp_path):
    # 1. Assemble stages
    asr = DummyASRComponent(default_text="Oli otya nnyabo", language="lug", duration=3.0)
    translator = DummyTranslationComponent(source_language="lug", target_language="eng")
    tts = DummyTTSComponent(output_dir=str(tmp_path))

    pipeline = Pipeline(
        stages=[asr, translator, tts],
        source_language="lug",
        target_language="eng",
        name="local_integration_test_pipeline",
    )

    # 2. Prepare audio input resource
    audio_res = Resource(
        id="test_sample_01",
        kind=ResourceKind.SPEECH,
        language="lug",
        version="1.0.0",
        provenance={"consent_basis": "test_consent"},
    )

    # 3. Execute pipeline
    executor = PipelineExecutor(pipeline)
    result = executor.run(audio_res)

    # 4. Assertions on Result
    assert result.status == ResultStatus.COMPLETE
    assert result.source_language == "lug"
    assert result.target_language == "eng"
    assert len(result.segments) == 1

    seg = result.segments[0]
    assert seg.text == "hello madam, how are you"
    assert seg.language == "eng"
    assert seg.source_language == "lug"
    assert seg.speaker == "speaker_0"

    # Verify audio artifact generated
    assert len(result.artifacts) >= 1
    assert Path(result.artifacts[0]).exists()

    # 5. Evaluate results
    wer_eval = WEREvaluator()
    eval_res = wer_eval.evaluate_pair(result, "hello madam, how are you")
    assert eval_res.metadata["metrics"]["wer"] == 0.0

    timing_eval = TemporalAlignmentEvaluator(tolerance_ms=200.0)
    timing_res = timing_eval.run(eval_res)
    assert "timing_metrics" in timing_res.metadata
    assert timing_res.metadata["timing_metrics"]["pct_within_tolerance"] == 100.0


def test_local_pipeline_degraded_fallback(tmp_path):
    class FailingTTS(DummyTTSComponent):
        def run(self, input):
            raise RuntimeError("TTS model failed during synthesis")

    asr = DummyASRComponent(default_text="Oli otya", language="lug")
    translator = DummyTranslationComponent(source_language="lug", target_language="eng")
    tts = FailingTTS(output_dir=str(tmp_path))
    tts.on_failure = FailureMode.DEGRADE

    pipeline = Pipeline(
        stages=[asr, translator, tts],
        source_language="lug",
        target_language="eng",
        on_stage_failure=FailureMode.DEGRADE,
    )

    executor = PipelineExecutor(pipeline)
    result = executor.run(Resource(id="sample", kind=ResourceKind.SPEECH, language="lug", version="1.0.0"))

    assert result.status == ResultStatus.DEGRADED
    assert any("degraded" in w.lower() for w in result.warnings)
    assert len(result.artifacts) >= 1
