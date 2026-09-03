"""
Integration test verifying Milestone 2 completion (Evaluation Infrastructure & Benchmarks).

Validates:
1. Luganda evaluation resources are registered with valid provenance.
2. Pipeline evaluation on the ASR and Parallel evaluation sets records WER, CER, and chrF.
3. compare_runs() computes deterministic metric deltas across runs.
"""

from lingualdub.components.asr.dummy import DummyASRComponent
from lingualdub.components.translation.dummy import DummyTranslationComponent
from lingualdub.components.eval.metrics import WEREvaluator, TranslationEvaluator
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import ResultStatus
from lingualdub.pipeline.executor import PipelineExecutor
from lingualdub.resources.eval_sets import (
    LUGANDA_ASR_EVAL_SET,
    LUGANDA_ENG_PARALLEL_EVAL_SET,
    get_evaluation_resource,
)
from lingualdub.utils.comparison import compare_runs


def test_m2_evaluation_resources_registered():
    """M2.4: Ensure evaluation resources carry provenance, licensing, and protocol."""
    asr_res = get_evaluation_resource("lug_asr_eval_salt_v1")
    assert asr_res is not None
    assert asr_res.kind == ResourceKind.EVAL_SET
    assert asr_res.language == "lug"
    assert asr_res.provenance.get("license") == "CC-BY-4.0"
    assert asr_res.provenance.get("dataset_version") == "1.0.0"
    assert "SALT_ASR_EVAL_PROTOCOL" in asr_res.provenance.get("evaluation_protocol", "")

    mt_res = get_evaluation_resource("lug_eng_parallel_eval_salt_v1")
    assert mt_res is not None
    assert mt_res.kind == ResourceKind.PARALLEL_TEXT
    assert mt_res.provenance.get("license") == "CC-BY-4.0"
    assert mt_res.provenance.get("dataset_version") == "1.0.0"


def test_m2_pipeline_evaluation_and_compare_runs():
    """M2 Done-When: Run pipeline on evaluation set, evaluate metrics, and compare runs."""
    asr_res = LUGANDA_ASR_EVAL_SET
    first_sample = asr_res.metadata["samples"][0]
    ref_text = first_sample["reference_text"]

    # --- Run 1: Baseline Component (Simulating higher WER) ---
    asr_v1 = DummyASRComponent(
        default_text="Oli otya nnyabo tusanyuse nnyo",  # Missing trailing words
        language="lug",
        duration=3.8,
    )
    asr_v1.version = "1.0.0"

    pipe_v1 = Pipeline(
        stages=[asr_v1],
        source_language="lug",
        name="baseline_eval_pipeline",
    )
    exec_v1 = PipelineExecutor(pipe_v1)
    res_v1 = exec_v1.run(asr_res)
    assert res_v1.status == ResultStatus.COMPLETE

    # Evaluate WER/CER on Run 1
    evaluator = WEREvaluator()
    eval_res_v1 = evaluator.evaluate_pair(res_v1, ref_text)
    eval_res_v1.provenance["dataset_version"] = "1.0.0"
    eval_res_v1.provenance["run_id"] = "run_baseline_01"

    m1 = eval_res_v1.metadata["metrics"]
    assert "wer" in m1 and "cer" in m1
    assert m1["wer"] > 0.0  # Incomplete match has positive WER

    # --- Run 2: Candidate Component (Exact match -> 0.0 WER) ---
    asr_v2 = DummyASRComponent(
        default_text=ref_text,
        language="lug",
        duration=3.8,
    )
    asr_v2.version = "2.0.0"

    pipe_v2 = Pipeline(
        stages=[asr_v2],
        source_language="lug",
        name="candidate_eval_pipeline",
    )
    exec_v2 = PipelineExecutor(pipe_v2)
    res_v2 = exec_v2.run(asr_res)

    eval_res_v2 = evaluator.evaluate_pair(res_v2, ref_text)
    eval_res_v2.provenance["dataset_version"] = "1.0.0"
    eval_res_v2.provenance["run_id"] = "run_candidate_02"

    m2 = eval_res_v2.metadata["metrics"]
    assert m2["wer"] == 0.0
    assert m2["cer"] == 0.0

    # --- Compare Runs ---
    diff = compare_runs(eval_res_v1, eval_res_v2, require_matching_dataset=True)

    assert diff["baseline_run_id"] == "run_baseline_01"
    assert diff["candidate_run_id"] == "run_candidate_02"
    assert "wer_delta" in diff["deltas"]
    assert diff["deltas"]["wer_delta"] < 0.0  # Candidate improved over baseline
    assert diff["deltas"]["wer_relative_reduction_pct"] == 100.0


def test_m2_translation_evaluation():
    """M2: Validate translation evaluation on parallel benchmark dataset."""
    mt_res = LUGANDA_ENG_PARALLEL_EVAL_SET
    pair = mt_res.metadata["pairs"][0]
    source_lug = pair["source_lug"]
    reference_eng = pair["reference_eng"]

    # Translation pipeline with upstream ASR providing transcription
    asr_comp = DummyASRComponent(default_text=source_lug, language="lug")
    trans_comp = DummyTranslationComponent(
        source_language="lug",
        target_language="eng",
        default_translation=reference_eng,
    )
    pipe = Pipeline(
        stages=[asr_comp, trans_comp],
        source_language="lug",
        target_language="eng",
    )

    executor = PipelineExecutor(pipe)
    dubbed_res = executor.run(Resource(id="sample", kind=ResourceKind.SPEECH, language="lug", version="1.0.0"))

    evaluator = TranslationEvaluator()
    eval_res = evaluator.evaluate_pair(dubbed_res, reference_eng)

    assert eval_res.metadata["metrics"]["chrf"] == 100.0
