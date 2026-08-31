# Pipeline Configuration Templates

This directory contains declarative YAML pipeline configuration templates. Configuration-driven
execution allows experiments to be shared as reproducible pipeline definitions
without requiring Python code.

A pipeline configuration specifies:
- **Source and target language** (`source_language: "lug"`, `"yor"`, `"nyn"`, `"swa"`, `"ach"`, etc.)
- **Ordered component selection** per stage (`key`, `version`, `params`)
- **Per-segment language routing** (for code-switching-aware pipelines)
- **Stage failure behaviour** (`abort`, `skip`, `degrade`)
- **Metadata and environment tags**

---

## Available Configurations

| File | Purpose | Execution Tier | Default Adapters |
|---|---|---|---|
| [`local_mock_pipeline.yaml`](local_mock_pipeline.yaml) | Zero-dependency local integration testing | Level 2 (Local) | `dummy_asr` $\to$ `dummy_translator` $\to$ `dummy_tts` |
| [`speech_dubbing_baseline.yaml`](speech_dubbing_baseline.yaml) | Generic multilingual dubbing template (any language) | Level 3 (Colab / Cloud GPU) | Configurable ASR $\to$ MT $\to$ TTS |
| [`luganda_english_baseline.yaml`](luganda_english_baseline.yaml) | Reference baseline for Luganda $\to$ English | Level 3 (Colab GPU) | `sunbird_asr` $\to$ `sunbird_translator` $\to$ `mms_tts` |

---

## Adapting to Any Low-Resource Language

To configure for a new language (e.g. Runyankole `nyn`, Yoruba `yor`, Swahili `swa`):

1. Set `source_language` to your language code.
2. Choose your model adapter in `stages` (e.g. `sunbird_asr` for East African languages, `whisper_asr` for Whisper models, or your custom registered component).
3. Run with:
```bash
lingualdub experiment run configs/speech_dubbing_baseline.yaml \
  --input-audio your_audio.wav \
  --output-dir experiments/your_language_run_01
```
