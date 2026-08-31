# Contributing to LingualDub

Thank you for your interest in contributing to **LingualDub**! We welcome contributions from speech-AI researchers, low-resource NLP practitioners, software engineers, and language communities worldwide.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Architecture & Design Principles](#architecture--design-principles)
- [Development Setup](#development-setup)
- [Contribution Workflows](#contribution-workflows)
  - [1. Adding a New Language](#1-adding-a-new-language)
  - [2. Creating a New Component Adapter](#2-creating-a-new-component-adapter)
  - [3. Registering a Dataset or Eval Resource](#3-registering-a-dataset-or-eval-resource)
  - [4. Creating a New Pipeline](#4-creating-a-new-pipeline)
- [Code Standards & Quality](#code-standards--quality)
- [Testing & CI](#testing--ci)
- [Submitting a Pull Request](#submitting-a-pull-request)

---

## Code of Conduct

All contributors are expected to uphold our [Code of Conduct](CODE_OF_CONDUCT.md). Please report any unacceptable behavior to `conduct@lingualdub.org`.

---

## Architecture & Design Principles

LingualDub is built on three core tenets:

1. **Composable & Replaceable**: Components are modular building blocks that declare `requires` and `provides` capability tokens. No framework core changes are required to add new models, languages, or evaluators.
2. **Provenance & Reproducibility**: Every run tracks exact model versions, dataset versions, run UUIDs, and configuration hashes in `Result.provenance`.
3. **Data Consent & Ethics**: All voice and speech data must carry an explicit `consent_basis` in its `Resource.provenance` before downstream voice synthesis or transfer components will execute.

---

## Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/allaninfo-tech/lingualdub.git
cd lingualdub
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install in editable mode with development dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
```

### 4. Install pre-commit hooks (Optional but recommended)

```bash
pre-commit install
```

---

## Contribution Workflows

### 1. Adding a New Language

New language profiles live in `lingualdub/languages/` (or within external extension packages).

```python
from lingualdub.core.language import Language

SWAHILI = Language(
    code="swh",
    name="Swahili",
    family="Bantu (Northeast Savannah)",
    resource_profile="speech-moderate / text-rich",
    supported_tasks=["asr", "translation", "tts"],
    related_languages=["lug", "nyn"],
)
```

### 2. Creating a New Component Adapter

Subclass the appropriate base class (e.g. `ASRComponent`, `TTSComponent`, `TranslationComponent`, `AlignmentComponent`, `EvaluatorComponent`) and implement `run()` and optionally `degrade()`:

```python
from typing import Union
from lingualdub.core.component import ComponentTask, FailureMode
from lingualdub.components.asr.base import ASRComponent
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result, ResultStatus

class WhisperASRComponent(ASRComponent):
    name: str = "whisper_asr"
    version: str = "1.0.0"
    task: ComponentTask = ComponentTask.ASR
    supported_languages = ["lug", "swh", "eng"]
    requires = []
    provides = ["transcription", "word_timestamps", "language_detection"]
    on_failure = FailureMode.ABORT

    def run(self, input: Union[Resource, Result]) -> Result:
        # Run inference using ResourceManager for cached weights
        ...
        return Result(segments=[...], source_language="lug")
```

### 3. Declaring Extension Manifests

Extensions ship a `lingualdub.manifest.json` in their package directory:

```json
{
  "name": "lingualdub-whisper",
  "version": "1.0.0",
  "entries": [
    {
      "kind": "component",
      "key": "whisper_asr",
      "module": "my_package.asr",
      "attr": "WhisperASRComponent",
      "version": "1.0.0",
      "metadata": { "tasks": ["asr"] }
    }
  ]
}
```

The framework's `ManifestScanner` dynamically discovers and loads these entries without modifying any core files.

---

## Code Standards & Quality

We maintain high engineering standards:

- **Python Version**: `>= 3.10`
- **Formatting**: Checked with `ruff format --check .` (configured to 100 char line limit).
- **Linting**: Checked with `ruff check .`.
- **Type Checking**: Full type annotations required on public interfaces; verified with `mypy lingualdub`.
- **Docstrings**: Google/Sphinx style docstrings on all public classes, methods, and functions.

Run code formatters and linters:
```bash
ruff format .
ruff check --fix .
mypy lingualdub
```

---

## Testing & CI

All pull requests must pass our automated CI suite:

```bash
# Run pytest with coverage
pytest --cov=lingualdub --cov-report=term-missing
```

- Ensure test coverage remains `>= 80%` across core modules.
- Add mock components to test execution paths without requiring heavy GPU/ML dependencies.

---

## Submitting a Pull Request

1. Create a descriptive branch: `git checkout -b feat/swahili-asr-adapter`
2. Commit your changes following [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: add Swahili language profile`
   - `fix: resolve duration calculation rounding issue`
   - `docs: update pipeline configuration guide`
3. Push to your fork and open a Pull Request using our [PR Template](.github/PULL_REQUEST_TEMPLATE.md).
4. Address review comments and ensure all CI checks turn green!
