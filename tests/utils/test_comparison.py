from lingualdub.core.result import Result, ResultStatus
from lingualdub.core.segment import Segment
from lingualdub.utils.comparison import compare_runs, ProvenanceMismatchError


def test_compare_runs_wer_chrf_deltas():
    base = Result(
        segments=[Segment(0.0, 2.0, "hello world", "eng")],
        status=ResultStatus.COMPLETE,
        provenance={"run_id": "run_01", "dataset_version": "v1.0"},
        metadata={"metrics": {"wer": 0.20, "chrf": 60.0}},
    )

    cand = Result(
        segments=[Segment(0.0, 2.0, "hello world", "eng")],
        status=ResultStatus.COMPLETE,
        provenance={"run_id": "run_02", "dataset_version": "v1.0"},
        metadata={"metrics": {"wer": 0.15, "chrf": 65.0}},
    )

    comp = compare_runs(base, cand, require_matching_dataset=True)
    assert comp["deltas"]["wer_delta"] == -0.05
    assert comp["deltas"]["chrf_delta"] == 5.0
    assert comp["deltas"]["wer_relative_reduction_pct"] == 25.0


def test_compare_runs_provenance_mismatch_raises():
    base = Result(provenance={"dataset_version": "dataset_v1"})
    cand = Result(provenance={"dataset_version": "dataset_v2"})

    try:
        compare_runs(base, cand, require_matching_dataset=True)
        assert False, "Expected ProvenanceMismatchError"
    except ProvenanceMismatchError as exc:
        assert "baseline dataset" in str(exc)

    # Protocol mismatch check
    p_base = Result(provenance={"evaluation_protocol": "PROTO_A"})
    p_cand = Result(provenance={"evaluation_protocol": "PROTO_B"})
    try:
        compare_runs(p_base, p_cand)
        assert False, "Expected ProvenanceMismatchError on protocol mismatch"
    except ProvenanceMismatchError as exc:
        assert "evaluation protocol" in str(exc)


def test_compare_runs_bleu_deltas():
    base = Result(
        provenance={"run_id": "b", "dataset_version": "1.0"},
        metadata={"metrics": {"bleu": 25.0, "chrf": 40.0}},
    )
    cand = Result(
        provenance={"run_id": "c", "dataset_version": "1.0"},
        metadata={"metrics": {"bleu": 32.5, "chrf": 48.0}},
    )
    comp = compare_runs(base, cand)
    assert comp["deltas"]["bleu_delta"] == 7.5
    assert comp["deltas"]["chrf_delta"] == 8.0
