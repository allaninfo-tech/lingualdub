# LingualDub — Public API Specification

> **Status:** Canonical Specification (v0.1.0)  
> **Rule:** Any symbol not explicitly documented here or exposed in a module's `__all__` is considered an internal implementation detail and subject to change without notice.

---

## 1. Top-Level Namespace (`lingualdub`)

External applications, extensions, and integration scripts should primarily import from `lingualdub`:

```python
import lingualdub as ld
```

The top-level `lingualdub` package exposes the following stable symbols:

### Core Abstractions
| Symbol | Type | Description |
|---|---|---|
| `Language` | Class | Structured language representation with metadata, family, and phonetic properties |
| `Resource` | Class | File or dataset asset with metadata, language tagging, checksums, and consent tracking |
| `ResourceKind` | Enum | Classification of resources (`SPEECH`, `TEXT`, `PARALLEL_TEXT`, `MODEL_WEIGHTS`, `EVAL_SET`, `VIDEO`, `OTHER`) |
| `Component` | Class (ABC) | Base abstraction for all pipeline processing stages |
| `ComponentTask` | Enum | Processing task categorization (`ASR`, `TRANSLATION`, `TTS`, `ALIGNMENT`, `SPEAKER`, `CODE_SWITCH`, `ADAPTATION`, `EVAL`, `PREPROCESSING`, `OTHER`) |
| `FailureMode` | Enum | Stage failure execution policy (`ABORT`, `SKIP`, `DEGRADE`) |
| `Pipeline` | Class | Sequence of component stages with compatibility validation and routing |
| `Result` | Class | Structured execution output carrying segments, status, provenance, and artifacts |
| `ResultStatus` | Enum | Execution quality status (`COMPLETE`, `PARTIAL`, `DEGRADED`, `FAILED`) |
| `Segment` | Class | Atomic temporal unit carrying timing, text, per-segment language, speaker, and metadata |

### Pipeline & Execution
| Symbol | Type | Description |
|---|---|---|
| `PipelineExecutor` | Class | Linear stage executor supporting abort, skip, and degrade paths |
| `PipelineExecutionError` | Exception | Raised when a pipeline stage aborts under `FailureMode.ABORT` |
| `ConfigLoader` | Class | Loader that resolves YAML/dict definitions into executable `Pipeline` instances |

### Registry & Discovery
| Symbol | Type | Description |
|---|---|---|
| `Registry` | Class | Central service locator for resolving components, languages, and resources |
| `RegistryError` | Exception | Base exception for registry resolution or duplicate registration failures |
| `ConflictPolicy` | Enum | Strategy for resolving registration key collisions (`REPLACE`, `REJECT`, `WARN_REPLACE`) |
| `ManifestScanner` | Class | File and entrypoint scanner discovering extensions via `lingualdub.manifest.json` |
| `ManifestError` | Exception | Raised when an extension manifest cannot be found or parsed |

### Utilities & Management
| Symbol | Type | Description |
|---|---|---|
| `ResourceManager` | Class | Local asset manager verifying sha256 checksums and managing downloads |
| `ChecksumError` | Exception | Raised when a resource file's checksum fails verification |
| `ResourceNotFoundError` | Exception | Raised when a requested resource is not available locally or remotely |
| `make_run_id` | Function | Generates a collision-resistant timestamped run ID |
| `make_provenance` | Function | Assembles a structured provenance record for pipeline execution |
| `compare_runs` | Function | Compares two execution runs across evaluation metrics |
| `ProvenanceMismatchError` | Exception | Raised when comparing runs generated under incompatible configurations |
| `__version__` | String | Package version string |

---

## 2. Component Package Namespaces (`lingualdub.components.*`)

Individual task packages provide base component classes and reference implementations:

### `lingualdub.components.adaptation`
- `AdaptationComponent` (Base)

### `lingualdub.components.alignment`
- `AlignmentComponent` (Base)
- `DurationModellingComponent`
- `DummyForcedAlignmentComponent`

### `lingualdub.components.asr`
- `ASRComponent` (Base)
- `DummyASRComponent`
- `RunyankoleASRComponent`
- `SunbirdASRComponent`
- `WhisperASRComponent`

### `lingualdub.components.av_sync`
- `DialogueTimingComponent`
- `VideoMergerComponent`

### `lingualdub.components.code_switch`
- `CodeSwitchComponent` (Base)
- `DummyCodeSwitchComponent`
- `HeuristicLIDComponent`

### `lingualdub.components.eval`
- `EvaluatorComponent` (Base)
- `AVSyncEvaluator`
- `SpeakerSimilarityEvaluator`
- `TemporalAlignmentEvaluator`
- `TranslationEvaluator`
- `WEREvaluator`

### `lingualdub.components.speaker`
- `SpeakerComponent` (Base)
- `SpeakerEmbeddingComponent`

### `lingualdub.components.translation`
- `TranslationComponent` (Base)
- `DummyTranslationComponent`
- `HuggingFaceTranslationComponent`
- `SunbirdTranslationComponent`

### `lingualdub.components.tts`
- `TTSComponent` (Base)
- `FittingStrategy`
- `DummyTTSComponent`
- `MMSTTSComponent`
- `VoiceConditionedTTSComponent`

---

## 3. Language & Resource Profiles (`lingualdub.languages`, `lingualdub.resources`)

### `lingualdub.languages`
- `LUGANDA`: Canonical Language profile for Luganda (`lug`)
- `RUNYANKOLE`: Canonical Language profile for Runyankole (`nyn`)
- `NLLB_CODE_MAP`: Mapping between ISO 639-3 and Flores/NLLB language codes

### `lingualdub.resources`
- `LUGANDA_ASR_EVAL_SET`
- `LUGANDA_ENG_PARALLEL_EVAL_SET`
- `LUGANDA_ENG_CODESWITCH_EVAL_SET`
- `get_evaluation_resource()`

---

## 4. Internal Implementation Policy

1. **Private by Default:** All helper functions, internal state, and scratch utilities are prefixed with a leading underscore `_`.
2. **Explicit Exports:** Every package and sub-package must specify `__all__` in its `__init__.py`. External code must not rely on unexported symbols.
3. **Internal Module Annotations:** Modules containing framework internals are designated with the header:
   ```python
   # Internal — not part of public API
   ```
4. **No Direct Import of Internals:** The following modules are private internal implementations:
   - `lingualdub.utils.resource_helpers`
   - `lingualdub.components.tts.shared`
   - `lingualdub.components.code_switch.lexicons`
