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
