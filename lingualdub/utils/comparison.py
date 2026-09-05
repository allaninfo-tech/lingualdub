"""
Run comparison utility.

Enables reproducible comparison of two pipeline results, validating provenance
compatibility and returning metric deltas.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Union

from lingualdub.core.result import Result


class ProvenanceMismatchError(Exception):
    """Raised when comparing two runs that do not share the same evaluation baseline."""


def _load_result(result_or_path: Union[Result, dict, str, Path]) -> Result:
    """Load or coerce an input to a Result object."""
    if isinstance(result_or_path, Result):
        return result_or_path
    if isinstance(result_or_path, dict):
        return Result.from_dict(result_or_path)
    path = Path(result_or_path)
    if not path.exists():
        raise FileNotFoundError(f"Result file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return Result.from_dict(data)


def compare_runs(
    baseline: Union[Result, dict, str, Path],
    candidate: Union[Result, dict, str, Path],
    require_matching_dataset: bool = True,
) -> Dict[str, Any]:
    """
    Compare two execution results and return a structured dictionary of metric deltas.

    Args:
        baseline: The reference or baseline Result (or path to results.json).
        candidate: The new or candidate Result (or path to results.json).
        require_matching_dataset: If True (default), raises ProvenanceMismatchError
            if dataset_version differs. Set to False to allow cross-dataset comparison
            with a warning (not recommended for evaluation).

    Returns:
        Dict with metric differences, status changes, and comparison summary.
    """
    res_base = _load_result(baseline)
    res_cand = _load_result(candidate)

    # Validate provenance — dataset_version and protocol must match for comparable evaluation
    base_ds = res_base.provenance.get("dataset_version")
    cand_ds = res_cand.provenance.get("dataset_version")
    if base_ds and cand_ds and base_ds != cand_ds:
        if require_matching_dataset:
            raise ProvenanceMismatchError(
                f"Cannot compare runs: baseline dataset is {base_ds!r} but candidate dataset is {cand_ds!r}."
            )
        else:
            import warnings

            warnings.warn(
                f"Comparing runs across different datasets: baseline {base_ds!r} vs candidate {cand_ds!r}. "
                "Metric deltas may not be meaningful.",
                UserWarning,
                stacklevel=2,
            )

    base_proto = res_base.provenance.get("evaluation_protocol")
    cand_proto = res_cand.provenance.get("evaluation_protocol")
    if base_proto and cand_proto and base_proto != cand_proto:
        raise ProvenanceMismatchError(
            f"Cannot compare runs: baseline evaluation protocol is {base_proto!r} "
            f"but candidate protocol is {cand_proto!r}."
        )

    base_metrics = res_base.metadata.get("metrics", {})
    cand_metrics = res_cand.metadata.get("metrics", {})

    deltas: Dict[str, Any] = {}

    # Word Error Rate (WER): lower is better -> candidate - baseline
    if "wer" in base_metrics and "wer" in cand_metrics:
        b_wer = float(base_metrics["wer"])
        c_wer = float(cand_metrics["wer"])
        deltas["wer_delta"] = round(c_wer - b_wer, 4)
        deltas["wer_relative_reduction_pct"] = round(((b_wer - c_wer) / b_wer * 100.0) if b_wer > 0 else 0.0, 2)

    # Character Error Rate (CER): lower is better
    if "cer" in base_metrics and "cer" in cand_metrics:
        b_cer = float(base_metrics["cer"])
        c_cer = float(cand_metrics["cer"])
        deltas["cer_delta"] = round(c_cer - b_cer, 4)

    # chrF: higher is better -> candidate - baseline
    if "chrf" in base_metrics and "chrf" in cand_metrics:
        b_chrf = float(base_metrics["chrf"])
        c_chrf = float(cand_metrics["chrf"])
        deltas["chrf_delta"] = round(c_chrf - b_chrf, 2)

    # BLEU: higher is better -> candidate - baseline
    if "bleu" in base_metrics and "bleu" in cand_metrics:
        b_bleu = float(base_metrics["bleu"])
        c_bleu = float(cand_metrics["bleu"])
        deltas["bleu_delta"] = round(c_bleu - b_bleu, 2)

    # Timing metrics
    base_timing = res_base.metadata.get("timing_metrics", {})
    cand_timing = res_cand.metadata.get("timing_metrics", {})
    if "mean_duration_error_ms" in base_timing and "mean_duration_error_ms" in cand_timing:
        b_dur = float(base_timing["mean_duration_error_ms"])
        c_dur = float(cand_timing["mean_duration_error_ms"])
        deltas["duration_error_ms_delta"] = round(c_dur - b_dur, 2)

    # Speaker similarity (M5): higher is better
    if "speaker_similarity" in base_metrics and "speaker_similarity" in cand_metrics:
        b_spk = float(base_metrics["speaker_similarity"])
        c_spk = float(cand_metrics["speaker_similarity"])
        deltas["speaker_similarity_delta"] = round(c_spk - b_spk, 4)
        # Relative improvement
        deltas["speaker_similarity_relative_pct"] = round(((c_spk - b_spk) / max(b_spk, 1e-9) * 100.0) if b_spk > 0 else (100.0 if c_spk > 0 else 0.0), 2)

    return {
        "baseline_run_id": res_base.provenance.get("run_id"),
        "candidate_run_id": res_cand.provenance.get("run_id"),
        "baseline_status": res_base.status.value,
        "candidate_status": res_cand.status.value,
        "baseline_metrics": base_metrics,
        "candidate_metrics": cand_metrics,
        "deltas": deltas,
    }
