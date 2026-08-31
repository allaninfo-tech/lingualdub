# Getting Started

LingualDub standardises how speech/text datasets, model components, execution pipelines, and evaluation metrics interoperate for low-resource languages.

---

## Installation

### Core Package (Zero heavy ML dependencies)
```bash
git clone https://github.com/allaninfo-tech/lingualdub.git
cd lingualdub
pip install -e ".[dev]"
```

### Full Model Support (GPU / Colab)
```bash
pip install -e ".[all]"
```

---

## The 3-Tier Development Loop

```text
       YOUR MACHINE                     GITHUB                     COLAB / GPU SERVER
   ┌───────────────────┐        ┌───────────────────┐        ┌───────────────────┐
   │ Level 1: Unit Test│  push  │ Versioned Code,   │ clone  │ Level 3: GPU Exps │
   │ Level 2: Local E2E│ ─────► │ Configs & Results │ ─────► │ Sunbird, Whisper, │
   │ (Dummy Adapters)  │        │ (results.json)    │        │ NLLB, MMS-TTS     │
   └───────────────────┘        └─────────┬─────────┘        └─────────┬─────────┘
             ▲                            │                            │
             │            pull            │         push results       │
             └────────────────────────────┴────────────────────────────┘
```

1. **Level 1 (Unit Testing)**: Verify core contracts (`Language`, `Resource`, `Segment`, `Result`, `Pipeline`, `Registry`) without GPUs using `pytest`.
2. **Level 2 (Local Integration)**: Run the full ASR $\to$ Translation $\to$ TTS $\to$ Evaluation workflow locally in milliseconds using deterministic dummy adapters.
3. **Level 3 (Remote Research Experiments)**: Execute real neural models (Sunbird AI, Whisper Large v3, NLLB, Meta MMS-TTS) on Colab GPUs using declarative YAML configurations.

---

## Running Your First Pipeline

### 1. Using the Command Line Interface (CLI)

```bash
# Test local pipeline with zero external model dependencies:
lingualdub experiment run configs/local_mock_pipeline.yaml \
  --sample-text "Oli otya nnyabo" \
  --output-dir experiments/local_test

# Run the real Sunbird Luganda baseline on Colab GPU:
lingualdub experiment run configs/luganda_english_baseline.yaml \
  --input-audio data/samples/sample_lug.wav \
  --output-dir experiments/luganda_dubbing/baseline_v1
```

### 2. Using the Python API

```python
import lingualdub as ld

# 1. Initialize registry and load declarative pipeline config
registry = ld.Registry()
scanner = ld.ManifestScanner(registry)
scanner.scan()

loader = ld.ConfigLoader(registry)
pipeline = loader.load_file("configs/luganda_english_baseline.yaml")

# 2. Execute pipeline with automatic capability validation & fault tolerance
executor = ld.PipelineExecutor(pipeline)
audio_resource = ld.Resource(
    id="sample_01",
    kind=ld.ResourceKind.SPEECH,
    language="lug",
    version="1.0.0",
    path="data/samples/sample_lug.wav",
    provenance={"consent_basis": "research_evaluation"},
)

result = executor.run(audio_resource)

# 3. Inspect results
print(f"Status: {result.status.value.upper()}")
for seg in result.segments:
    print(f"[{seg.start:.2f}s -> {seg.end:.2f}s] ({seg.language}): {seg.text}")
```

---

## Next Steps

- Explore available pipeline configs in [`configs/`](../configs/)
- Run the interactive Colab experiment notebook in [`notebooks/colab_luganda_m1_experiment.ipynb`](../notebooks/colab_luganda_m1_experiment.ipynb)
- Read the [Architecture Overview](architecture.md) and [Milestones](milestones.md)
