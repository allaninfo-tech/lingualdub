<div align="center">

<a href="https://lingualdub.pages.dev">
  <img src="docs/assets/logo.png" alt="LingualDub Logo" width="340" />
</a>

# LingualDub

**A composable, registry-based speech-AI framework for low-resource languages.**

[![CI](https://github.com/allaninfo-tech/lingualdub/actions/workflows/ci.yml/badge.svg)](https://github.com/allaninfo-tech/lingualdub/actions/workflows/ci.yml)
[![Lint & Type Check](https://github.com/allaninfo-tech/lingualdub/actions/workflows/lint.yml/badge.svg)](https://github.com/allaninfo-tech/lingualdub/actions/workflows/lint.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/type_checker-mypy-blue.svg)](http://mypy-lang.org/)
[![Website](https://img.shields.io/badge/website-lingualdub.pages.dev-indigo)](https://lingualdub.pages.dev)

<br />

[Documentation](https://lingualdub.pages.dev/docs) • [Milestones & Roadmap](docs/milestones.md) • [Contributing](CONTRIBUTING.md) • [Architecture](docs/architecture.md)

</div>

---

## Overview

**LingualDub** is an open, modular speech-AI framework designed as reusable research and production infrastructure for low-resource language contexts. It standardises how language metadata, speech/text data resources, model components, execution pipelines, and evaluation metrics interoperate — so that existing models and tools can be wired together, adapted, and replaced without rewriting framework internals.

Primary validation languages:
- **Luganda (`lug`)**: Bantu (Great Lakes) — speech-moderate / text-moderate baseline.
- **Runyankole (`nyn`)**: Bantu (Great Lakes) — speech-sparse / text-sparse language-family generalisation test.

---

## Key Features

- **Composable Architecture**: Five foundational abstractions (`Language`, `Resource`, `Component`, `Pipeline`, `Result`) forming a closed, provenance-tracked loop.
- **Registry & Dynamic Discovery**: Decoupled component registration supporting multiple conflict policies (`NAMESPACED`, `HIGHEST_VERSION`, `EXPLICIT`) and automatic `lingualdub.manifest.json` scanning.
- **Assembly-Time Capability Checking**: Validates stage input/output contracts (`requires` vs `provides`) at assembly time before any heavy model loads or runs.
- **Graceful Failure Handling**: Multi-tier fault tolerance (`ABORT`, `SKIP`, `DEGRADE`) with built-in degraded fallback paths and warning propagation.
- **Code-Switching Native**: `Segment.language` is authoritative per span, enabling dynamic per-segment language routing across different models in a single run.
- **Built-in Resource Management**: Local file caching, automatic downloads, and cryptographic SHA256 integrity verification.
- **Strict Provenance & Consent Tracking**: Every run automatically records pipeline structure, model versions, dataset provenance, and consent basis for ethical voice AI.

---

## Architecture

```
                 ┌─────────────────────────────┐
                 │    Language + Resources     │
                 └──────────────┬──────────────┘
                                │
                                ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                     Registry Discovery                      │
  │     (Manifest Scanner • Conflict Resolution • Versioning)   │
  └─────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                     Pipeline Assembly                       │
  │     (Stage Composition • Assembly-Time Capability Check)    │
  └─────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                     Pipeline Executor                       │
  │     (Per-Segment Routing • Abort / Skip / Degrade Paths)    │
  └─────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
                 ┌─────────────────────────────┐
                 │   Result + Provenance Loop  │
                 │ (Segments • Metrics • Audio)│
                 └─────────────────────────────┘
```

---

## Quickstart

### Installation

```bash
# Clone and install in editable mode
git clone https://github.com/allaninfo-tech/lingualdub.git
cd lingualdub
pip install -e ".[dev]"
```

For GPU models (Whisper, Sunbird, NLLB, MMS-TTS, metrics):
```bash
pip install -e ".[all]"
```

---

## The 3-Tier Workflow

LingualDub uses **GitHub as the bridge** between local development and cloud GPU execution (e.g. Google Colab):

```text
       YOUR MACHINE                     GITHUB                     COLAB / GPU SERVER
   ┌───────────────────┐        ┌───────────────────┐        ┌───────────────────┐
   │ Fast Unit Tests   │  push  │ Versioned Code,   │ clone  │ Real Heavy Models │
   │ Deterministic     │ ─────► │ Configs & Result  │ ─────► │ Sunbird, Whisper, │
   │ Local Integration │        │ Envelopes (JSON)  │        │ NLLB, MMS-TTS     │
   └───────────────────┘        └─────────┬─────────┘        └─────────┬─────────┘
             ▲                            │                            │
             │            pull            │         push results       │
             └────────────────────────────┴────────────────────────────┘
```

1. **Level 1 (Local Unit Tests)**: Test core objects (`Language`, `Resource`, `Pipeline`, `Registry`) without GPUs or heavy downloads (`pytest`).
2. **Level 2 (Local Integration)**: Run full end-to-end pipelines locally with zero-dependency dummy adapters (`dummy_asr`, `dummy_translator`, `dummy_tts`) in under 0.1s.
3. **Level 3 (Remote Research Experiments)**: Execute real neural models (Sunbird AI, Whisper Large v3, NLLB, Meta MMS-TTS) on Colab GPUs via declarative configs and evaluate with WER, CER, and chrF.

---

### Running via CLI

```bash
# 1. Inspect registered components and languages
lingualdub registry list

# 2. Run a local pipeline test
lingualdub experiment run configs/local_mock_pipeline.yaml \
  --sample-text "Oli otya nnyabo" \
  --output-dir experiments/local_test

# 3. Run a real Sunbird GPU experiment on Colab
lingualdub experiment run configs/luganda_english_baseline.yaml \
  --input-audio data/samples/sample_lug.wav \
  --output-dir experiments/luganda_dubbing/baseline_v1

# 4. Compare metric deltas across two runs
lingualdub compare \
  --baseline experiments/luganda_dubbing/baseline_v1/results.json \
  --candidate experiments/luganda_dubbing/run_v2/results.json
```

---

### Python API Example

```python
import lingualdub as ld

# 1. Initialize registry and load declarative pipeline config
registry = ld.Registry(conflict_policy=ld.ConflictPolicy.HIGHEST_VERSION)
scanner = ld.ManifestScanner(registry)
scanner.scan()

loader = ld.ConfigLoader(registry)
pipeline = loader.load_file("configs/luganda_english_baseline.yaml")

# 2. Execute pipeline with automatic capability validation & fault tolerance
executor = ld.PipelineExecutor(pipeline)
audio_resource = ld.Resource(
    id="lug_test_sample",
    kind=ld.ResourceKind.SPEECH,
    language="lug",
    version="1.0.0",
    path="data/samples/sample_lug.wav",
    provenance={"consent_basis": "research_evaluation"},
)

result = executor.run(audio_resource)

# 3. Inspect structured results and provenance
print(f"Status: {result.status.value.upper()}")
for seg in result.segments:
    print(f"[{seg.start:.2f}s -> {seg.end:.2f}s] ({seg.language}): {seg.text}")
print(f"Synthesised Audio Artifacts: {result.artifacts}")
```

---

## Core Abstractions

| Abstraction | Description |
|---|---|
| **`Language`** | Structured language profile capturing linguistic metadata, resource availability profile, supported tasks, and related language families. |
| **`Resource`** | Data or model asset (speech, parallel text, audio, checkpoint, eval set) with versioning, quality flags, and recorded consent basis. |
| **`Component`** | Replaceable processing unit with typed contracts (`requires` and `provides` capability tokens) and optional `degrade()` fallbacks. |
| **`Pipeline`** | Composed sequence of components with assembly-time compatibility validation and per-segment language routing. |
| **`Result`** | Structured execution envelope containing `Segment` lists, speaker info, confidence, status (`COMPLETE`, `PARTIAL`, `DEGRADED`, `FAILED`), and merged provenance. |
| **`Registry`** | Central repository enabling third-party extensions to register models, datasets, and evaluators without touching framework internals. |

---

## Research Challenge Modules

LingualDub provides modular workspaces for key open research problems in low-resource speech:

| Module | Priority | Focus Area |
|---|---|---|
| **Temporal Alignment** | Near-term | Duration modelling, speech-rate control, segment fitting, and cross-lingual synchronisation |
| **Code-Switching** | Near-term | Detection, representation, and per-segment routing for mixed-language speech |
| **Voice-Retention Evaluation** | Near-term | Repeatable speaker-similarity measurement and MOS human evaluation protocols |
| **Cross-Lingual Voice Transfer** | Open-ended | Speaker identity preservation across language boundaries with consent enforcement |
| **Audio-Visual Synchronisation** | Mid-term | Dialogue timing, scene cues, and lip-sync alignment for dubbed video |

---

## Project Roadmap

We follow a milestone-driven development model. Progress is tracked in [docs/milestones.md](docs/milestones.md):

- [x] **M0 — Foundation & Core Stabilization** (Serialization, Registry, Manifests, Resource Manager, Test Suite, CI)
- [ ] **M1 — First Real Dubbing Pipeline** (Luganda $\to$ English baseline with real model adapters)
- [ ] **M2 — Evaluation Infrastructure** (WER, CER, BLEU, chrF, run comparison utilities)
- [ ] **M3 — Code-Switching** (Per-segment language identification and routing)
- [ ] **M4 — Temporal Alignment** (Forced alignment & speech-rate adaptation)
- [ ] **M5 — Voice-Retention Evaluation** (Speaker embeddings & MOS protocol)
- [ ] **M6 — Cross-Lingual Voice Transfer** (Voice-conditioned TTS with consent checks)
- [ ] **M7 — Audio-Visual Synchronisation** (SyncNet alignment & video artifact export)
- [ ] **M8 — Generalisation Proof** (Runyankole language transfer validation)
- [ ] **M9 — Stable v0.1.0 Release** (Public PyPI package & full documentation)

---

## Repository Structure

```
lingualdub/
├── lingualdub/          # Core framework package (PEP 561 typed)
│   ├── core/            # Language, Resource, Component, Pipeline, Result, Segment
│   ├── registry/        # Registry, ManifestScanner, conflict resolution
│   ├── components/      # Task interfaces (ASR, TTS, MT, Alignment, Speaker, Eval, etc.)
│   ├── pipeline/        # PipelineExecutor and failure handling
│   ├── languages/       # Language profiles (Luganda, Runyankole, etc.)
│   └── utils/           # ResourceManager, provenance, comparison helpers
├── docs/                # Architecture, guides, milestones, manifest format
├── research/            # Research challenge module workspaces & notes
├── configs/             # Declarative pipeline YAML configurations
├── notebooks/           # Interactive demonstration & evaluation notebooks
├── tests/               # Pytest suite with >90% coverage on core modules
├── website/             # Source code for lingualdub.pages.dev (React + Tailwind)
├── .github/             # Issue templates, PR template, CI/CD workflows
├── pyproject.toml       # Build configuration, dependency groups, tool settings
├── LICENSE              # Apache 2.0 License
├── CITATION.cff         # Academic citation metadata
└── CONTRIBUTING.md      # Development and contribution guide
```

---

## Contributing

We welcome contributions! Please read our [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before submitting a pull request.

---

## Citation

If you use LingualDub in your research, please cite:

```bibtex
@software{lingualdub2026,
  author = {LingualDub Authors and Contributors},
  title = {LingualDub: A Composable, Registry-Based Speech-AI Framework for Low-Resource Languages},
  url = {https://github.com/allaninfo-tech/lingualdub},
  version = {0.1.0-dev},
  year = {2026}
}
```

---

## License

This project is licensed under the **Apache License 2.0** — see the [LICENSE](LICENSE) file for details.
