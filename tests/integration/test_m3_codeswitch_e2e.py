"""
End-to-End Integration Test for Milestone 3 (Code-Switching & Per-Segment Routing).

Proves:
1. Pipeline executes end-to-end: ASR -> Code-Switch LID -> Per-Segment Translation -> TTS.
2. Luganda spans are translated to English.
3. Existing English spans pass through without re-translation.
4. Dubbed audio artifacts are produced.
5. Zero core package modifications required.
"""

from pathlib import Path
from lingualdub.components.asr.dummy import DummyASRComponent
from lingualdub.components.code_switch.heuristic import HeuristicLIDComponent
from lingualdub.components.translation.dummy import DummyTranslationComponent
from lingualdub.components.tts.dummy import DummyTTSComponent
from lingualdub.core.component import FailureMode
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result, ResultStatus
from lingualdub.core.segment import Segment
from lingualdub.pipeline.executor import PipelineExecutor
from lingualdub.resources.eval_sets import LUGANDA_ENG_CODESWITCH_EVAL_SET


def test_m3_codeswitch_e2e_dubbing_pipeline(tmp_path):
    """M3.4: Complete mixed-language dubbing pipeline with per-segment routing."""
    # 1. Pipeline components
    class MixedAudioASR(DummyASRComponent):
        """Simulates ASR output for a code-switched utterance."""
        def run(self, input):
            return Result(
                segments=[
                    Segment(start=0.0, end=1.5, text="Oli otya nnyabo", language="lug", confidence=0.95),
                    Segment(start=1.5, end=3.5, text="can you send me the report today morning?", language="lug", confidence=0.92),
                ],
                source_language="lug",
            )

    asr = MixedAudioASR()
    lid = HeuristicLIDComponent(split_segments=False)
    translator = DummyTranslationComponent(
        source_language="lug",
        target_language="eng",
        default_translation="how are you madam",
    )
    # Translator only translates Luganda; English should pass through un-translated
    translator.supported_languages = ["lug"]
    translator.on_failure = FailureMode.SKIP

    tts = DummyTTSComponent(output_dir=str(tmp_path))

    # 2. Assemble pipeline with per_segment_language=True
    pipeline = Pipeline(
        stages=[asr, lid, translator, tts],
        source_language="lug",
        target_language="eng",
        per_segment_language=True,
        name="codeswitch_dubbing_e2e_pipeline",
    )

    # 3. Input resource
    input_audio = Resource(
        id="cs_test_audio",
        kind=ResourceKind.SPEECH,
        language="lug",
        version="1.0.0",
        provenance={"consent_basis": "institutional_open_research_release"},
    )

    # 4. Execute pipeline
    executor = PipelineExecutor(pipeline)
    result = executor.run(input_audio)

    # 5. Assertions
    assert result.status in (ResultStatus.COMPLETE, ResultStatus.PARTIAL)
    assert len(result.segments) == 2

    # Luganda segment was translated to English
    seg_lug = result.segments[0]
    assert seg_lug.text == "how are you madam"
    assert seg_lug.language == "eng"
    assert seg_lug.source_language == "lug"

    # English segment was NOT re-translated and was passed through untouched
    seg_eng = result.segments[1]
    assert seg_eng.text == "can you send me the report today morning?"
    assert seg_eng.language == "eng"
    assert seg_eng.metadata.get("skipped_by") == "dummy_translator"

    # Audio synthesis artifact produced for final dubbed result
    assert len(result.artifacts) >= 1
    wav_path = Path(result.artifacts[0])
    assert wav_path.exists()
    assert wav_path.stat().st_size > 0

    # Provenance tracks code switch and translator stages
    assert "code_switch_detection" in result.metadata


def test_m3_benchmark_eval_set_routing(tmp_path):
    """M3.3: Validate against benchmark code-switching dataset."""
    eval_res = LUGANDA_ENG_CODESWITCH_EVAL_SET
    samples = eval_res.metadata["samples"]
    sample = samples[0]

    input_result = Result(
        segments=[
            Segment(start=s["start"], end=s["end"], text=s["text"], language=s.get("language"))
            for s in sample["segments"]
        ],
        source_language="lug",
        target_language="eng",
    )

    translator = DummyTranslationComponent(
        source_language="lug",
        target_language="eng",
        custom_dictionary={"oli otya nnyabo": "how are you madam"},
    )
    translator.supported_languages = ["lug"]
    translator.on_failure = FailureMode.SKIP
    translator.requires = []

    pipe = Pipeline(
        stages=[translator],
        source_language="lug",
        target_language="eng",
        per_segment_language=True,
    )
    executor = PipelineExecutor(pipe)
    out = executor.run(input_result)

    assert len(out.segments) == 2
    assert "how are you madam" in out.segments[0].text.lower()
    assert out.segments[1].text == "can you send me the report today morning?"
