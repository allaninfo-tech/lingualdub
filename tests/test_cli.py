"""
Unit tests for lingualdub CLI commands.
"""

import json
from pathlib import Path
import pytest

from lingualdub.cli import main, get_default_registry


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "lingualdub" in out


def test_cli_registry_list(capsys):
    ret = main(["registry", "list"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "[LANGUAGES]" in out
    assert "[COMPONENTS]" in out
    assert "[RESOURCES]" in out


def test_cli_registry_list_filtered(capsys):
    ret = main(["registry", "list", "--kind", "language"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "[LANGUAGES]" in out
    assert "[COMPONENTS]" not in out


def test_cli_experiment_run_missing_config():
    ret = main(["experiment", "run", "nonexistent_config.yaml"])
    assert ret == 1


def test_cli_experiment_run_sample_text(tmp_path, capsys):
    cfg_file = Path("configs/local_mock_pipeline.yaml")
    out_dir = tmp_path / "cli_out"
    ret = main([
        "experiment", "run",
        str(cfg_file),
        "--sample-text", "Oli otya nnyabo",
        "--output-dir", str(out_dir),
    ])
    assert ret == 0
    assert (out_dir / "results.json").exists()
    assert (out_dir / "README.md").exists()


def test_cli_experiment_run_with_audio_input(tmp_path):
    cfg_file = Path("configs/local_mock_pipeline.yaml")
    audio_file = Path("data/samples/sample_lug.wav")
    ret = main([
        "experiment", "run",
        str(cfg_file),
        "--input-audio", str(audio_file),
    ])
    assert ret == 0


def test_cli_compare_runs(tmp_path):
    base_file = tmp_path / "base.json"
    cand_file = tmp_path / "cand.json"

    base_data = {
        "segments": [],
        "source_language": "lug",
        "status": "complete",
        "provenance": {"run_id": "r1", "dataset_version": "1.0"},
        "metadata": {"metrics": {"wer": 0.20, "chrf": 50.0}},
    }
    cand_data = {
        "segments": [],
        "source_language": "lug",
        "status": "complete",
        "provenance": {"run_id": "r2", "dataset_version": "1.0"},
        "metadata": {"metrics": {"wer": 0.15, "chrf": 55.0}},
    }

    base_file.write_text(json.dumps(base_data), encoding="utf-8")
    cand_file.write_text(json.dumps(cand_data), encoding="utf-8")

    ret = main(["compare", "--baseline", str(base_file), "--candidate", str(cand_file)])
    assert ret == 0


def test_cli_no_subcommand(capsys):
    ret = main([])
    assert ret == 0
    out = capsys.readouterr().out
    assert "LingualDub" in out
