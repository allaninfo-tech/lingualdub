# Pipeline Configuration Templates

This directory contains declarative YAML pipeline configuration templates. Configuration-driven
execution allows experiments to be shared as reproducible pipeline definitions
without requiring Python code.

A pipeline configuration specifies:
- Source and target language
- Ordered component selection per stage (`key`, `version`, `params`)
- Per-segment language routing (for code-switching-aware pipelines)
- Stage failure behaviour (`abort`, `skip`, `degrade`)
- Metadata and environment tags

---

## Available Configurations

| File | Purpose | Execution Tier | Models Used |
|---|---|---|---|
| [`local_mock_pipeline.yaml`](local_mock_pipeline.yaml) | Zero-dependency local integration testing | Level 2 (Local) | `dummy_asr` $\to$ `dummy_translator` $\to$ `dummy_tts` |
| [`luganda_english_baseline.yaml`](luganda_english_baseline.yaml) | Full neural Luganda $\to$ English dubbing baseline | Level 3 (Colab GPU) | `sunbird_asr` $\to$ `sunbird_translator` $\to$ `mms_tts` |

---

## Running a Configuration

```bash
# Run local mock pipeline:
lingualdub experiment run configs/local_mock_pipeline.yaml --sample-text "Oli otya nnyabo"

# Run Sunbird baseline on GPU / Colab:
lingualdub experiment run configs/luganda_english_baseline.yaml --input-audio data/samples/sample_lug.wav --output-dir experiments/luganda_baseline
```
