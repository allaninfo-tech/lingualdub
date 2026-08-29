# LingualDub

**A composable, registry-based framework for building, adapting, composing, and evaluating speech-AI systems for low-resource languages.**

---

## Overview

LingualDub is an open, modular framework designed as reusable infrastructure for speech-AI research and development in low-resource language contexts. It standardises how language metadata, data resources, processing components, pipelines, and evaluation results interoperate — so that existing models and tools can be wired together and extended rather than rewritten for each new language or research task.

---

## The Problem

Low-resource languages rarely share the same combination of speech data, text corpora, parallel translations, pronunciation resources, pretrained models, and evaluation sets. Developers and researchers repeatedly glue together incompatible ASR, translation, TTS, alignment, data, and evaluation components by hand. Critical research challenges — code-switching, language transfer, voice preservation, timing alignment, and evaluation — are typically scattered across separate projects rather than available in one composable environment.

When a new language or research method is introduced, the surrounding infrastructure often has to be rebuilt rather than simply extended.

LingualDub addresses this by making the repeated engineering and research work around low-resource speech **reusable, composable, and replaceable**.

---

## Core Abstractions

LingualDub is built around five interoperable objects that form a closed, provenance-tracked loop.

### Language
Represents a language together with its metadata, supported processing tasks, available resources, related languages, and compatible components. Resource profile is a first-class property — the framework does not assume every language has the same data or model coverage.

### Resource
Represents a data asset — speech recordings, text corpora, parallel translations, lexicons, pronunciation resources, model checkpoints, or evaluation sets — along with its provenance, version, quality flags, and compatible components.

### Component
A replaceable processing unit with a stable input/output contract. A component declares what capabilities it **requires** from upstream stages and what capabilities it **provides** to downstream stages, allowing the framework to catch incompatible compositions at assembly time rather than at runtime.

Component types include: ASR, translation, TTS, speaker modelling, code-switch handling, alignment, preprocessing, adaptation, and evaluation.

Components also define an optional degraded execution path — returning a partial result rather than failing entirely when full processing cannot complete.

### Pipeline
A composition of components connected by shared data representations and executed as a reproducible workflow. Each pipeline specifies how stage failures are handled: abort, skip and mark the result as partial, or invoke the component's degraded path.

Per-segment language routing is built in — different language spans within a single utterance can be routed to appropriate components independently, which is what makes code-switching a structural property of execution rather than a post-processing note.

### Result
A structured output carrying content, segment-level data, speaker and language information, confidence, processing status, warnings, provenance, and links to generated artifacts. Status distinguishes complete, partial, and degraded outputs so downstream consumers can act on result quality rather than treating all outputs identically.

### Registry
The mechanism for discovering, registering, and resolving languages, resources, components, and evaluators without editing framework internals. Extensions ship a manifest declaring what they provide; the registry scans installed manifests at startup. Every entry is versioned so pipeline configurations can pin to specific implementations and provenance is mechanically traceable.

---

## Architecture

```
LANGUAGE + RESOURCES
        ↓
COMPONENTS  ↔  MODELS / ALGORITHMS
        ↓
PIPELINE COMPOSITION + EXECUTION
        ↓
ADAPT / GENERATE DATA / PROCESS
        ↓
EVALUATE + SAVE ARTIFACTS
        ↓
DEVELOPER / RESEARCH SYSTEM
        ↓
DUBBING / SPEECH-TO-SPEECH / SUBTITLES / OTHER USE CASES
```

---

## Extension System

Components are the primary extension point. The framework defines contracts; implementations come from the framework itself, from external researchers, or from third-party projects. A new model or method is added by implementing the component contract and registering it — without modifying framework internals.

Extensions register through a manifest file. The registry discovers these at startup, making contribution practical at scale.

---

## Low-Resource Adaptation and Data Workflows

The framework treats adaptation and data work as composable capabilities. Supported workflows include:

- Cross-lingual transfer and multilingual model reuse
- Parameter-efficient adaptation (adapters, LoRA, and similar methods)
- Synthetic speech and text generation with filtering
- Back-translation and data augmentation
- Language-family and related-language transfer
- Human correction and validation feeding back into datasets and evaluation sets
- Resource and dataset auditing
- Active learning and targeted data selection

Artifacts produced by adaptation workflows are registered with their own version and provenance — resolved by later pipelines the same way first-party components are.

---

## Research Challenge Modules

| Module | Priority | Summary |
|---|---|---|
| **Temporal alignment** | Near-term | Duration modelling, speech-rate control, segment fitting, and cross-lingual synchronisation |
| **Code-switching** | Near-term | Detection, representation, and per-segment routing for mixed-language speech |
| **Voice-retention evaluation** | Near-term | Repeatable speaker-similarity measurement and human evaluation protocols |
| **Cross-lingual voice transfer** | Open-ended | Speaker representation and voice preservation across languages |
| **Audio-visual synchronisation** | Mid-term | Dialogue timing and lip-sync alignment for audiovisual dubbing |

Voice-retention evaluation is a dependency for cross-lingual voice transfer. Temporal alignment is a dependency for audio-visual synchronisation. Near-term modules are prioritised accordingly.

**Ethical note:** Voice transfer and voice-retention evaluation both process someone's voice. Consent is enforced as a compatibility requirement at the resource level — a voice resource without recorded consent is not compatible with voice-transfer or voice-retention components.

---

## Evaluation and Reproducibility

Evaluators are implemented as components of type `eval` — they take one or more results as input and produce a result carrying metrics. They register, version, and compose through the same registry as every other component.

Every run records:

- Input data and dataset version
- Language and dialect metadata
- Component versions and identifiers
- Pipeline configuration and parameters
- Evaluation metrics and protocol
- Generated artifacts and their provenance
- Adaptation or checkpoint information

Two runs with the same dataset version, language, and evaluation protocol but different component versions are directly comparable.

---

## Development Lifecycle

```
Profile language + resources
        ↓
Select / register components
        ↓
Compose pipeline
        ↓
Run baseline
        ↓
Adapt / generate data / process
        ↓
Evaluate
        ↓
Save models, datasets, metrics, and artifacts
        ↓
Replace components or iterate
```

Saved artifacts re-enter the loop as registered resources and components — making iteration a real mechanism, not just a return to the starting point.

---

## Extending LingualDub

| Goal | How |
|---|---|
| New language | Register language metadata, resource profile, and available resources |
| New model | Implement and register a component |
| New method | Add a component or pipeline stage |
| New dataset or resource | Register it with provenance and metadata |
| New evaluator | Implement an evaluator component and register it |
| New application | Compose existing components into a new pipeline |

---

## Architectural Success Criteria

The framework succeeds if the following changes can happen **without modifying the framework core**:

- New language → add language metadata and resources
- New model → implement and register a component
- New method → add a component or pipeline stage
- New dataset → register a resource
- New evaluator → implement and register an evaluator component
- New pipeline → compose existing components

---

## Repository Structure

```
lingualdub/
├── lingualdub/          # Core framework package
│   ├── core/            # Language, Resource, Component, Pipeline, Result, Segment
│   ├── registry/        # Registry, discovery, conflict resolution
│   ├── components/      # Component category interfaces and built-in stubs
│   │   ├── asr/
│   │   ├── translation/
│   │   ├── tts/
│   │   ├── alignment/
│   │   ├── speaker/
│   │   ├── code_switch/
│   │   ├── adaptation/
│   │   └── eval/
│   ├── pipeline/        # Pipeline executor and stage router
│   ├── languages/       # Language and resource registrations
│   └── utils/           # Shared utilities
├── docs/                # Architecture, guides, and per-module documentation
├── research/            # Research challenge module workspaces
│   ├── temporal_alignment/
│   ├── code_switching/
│   ├── voice_transfer/
│   ├── voice_retention_eval/
│   └── av_sync/
├── configs/             # Pipeline configuration templates
└── tests/               # Test suite mirroring the package structure
```

---

## License

To be determined.

---

## Contributing

The primary extension mechanism is the component and registry system. New languages, models, methods, datasets, and evaluators can all be contributed as registered extensions without requiring changes to framework internals. Contribution guidelines will be published alongside the first stable release.
