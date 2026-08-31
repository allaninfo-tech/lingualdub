from pathlib import Path
from lingualdub.cli import get_default_registry
from lingualdub.core.component import FailureMode
from lingualdub.pipeline.config_loader import ConfigLoader


def test_load_from_dict():
    registry = get_default_registry()
    loader = ConfigLoader(registry)

    config = {
        "name": "test_pipeline",
        "source_language": "lug",
        "target_language": "eng",
        "on_stage_failure": "skip",
        "stages": [
            {"key": "dummy_asr", "version": "1.0.0"},
            {"key": "dummy_translator", "version": "1.0.0"},
            {"key": "dummy_tts", "version": "1.0.0"},
        ],
    }

    pipeline = loader.load_dict(config)
    assert pipeline.name == "test_pipeline"
    assert pipeline.source_language == "lug"
    assert pipeline.target_language == "eng"
    assert pipeline.on_stage_failure == FailureMode.SKIP
    assert pipeline.stage_names == ["dummy_asr", "dummy_translator", "dummy_tts"]


def test_load_from_yaml_file(tmp_path):
    registry = get_default_registry()
    loader = ConfigLoader(registry)

    yaml_file = tmp_path / "pipeline.yaml"
    yaml_file.write_text("""
name: "yaml_pipeline"
source_language: "lug"
target_language: "eng"
on_stage_failure: "abort"

stages:
  - key: "dummy_asr"
  - key: "dummy_translator"
  - key: "dummy_tts"
""", encoding="utf-8")

    pipeline = loader.load_file(yaml_file)
    assert pipeline.name == "yaml_pipeline"
    assert len(pipeline.stages) == 3


def test_load_empty_stages_raises():
    registry = get_default_registry()
    loader = ConfigLoader(registry)
    try:
        loader.load_dict({"source_language": "lug", "stages": []})
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "at least one stage" in str(exc)
