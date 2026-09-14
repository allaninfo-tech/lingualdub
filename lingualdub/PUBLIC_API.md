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
| `ResourceKind` | Enum | Classification of resources (`SPEECH`, `TEXT`, `PARALLEL_TEXT`, `LEXICON`, `CHECKPOINT`, `EVAL_SET`, `SYNTHETIC`, `ALIGNMENT`, `VIDEO`, `OTHER`) |
| `Component` | Class (ABC) | Base abstraction for all pipeline processing stages |
| `ComponentTask` | Enum | Processing task categorization (`ASR`, `TRANSLATION`, `TTS`, `ALIGNMENT`, `SPEAKER`, `CODE_SWITCH`, `ADAPTATION`, `EVAL`, `PREPROCESSING`, `VIDEO`, `OTHER`) |
| `FailureMode` | Enum | Stage failure execution policy (`ABORT`, `SKIP`, `DEGRADE`) |
| `Pipeline` | Class | Sequence of component stages with compatibility validation and routing |
| `Result` | Class | Structured execution output carrying segments, status, provenance, and artifacts |
| `ResultStatus` | Enum | Execution quality status (`COMPLETE`, `PARTIAL`, `DEGRADED`, `FAILED`) |
| `Segment` | Class | Atomic temporal unit carrying timing, text, per-segment language, speaker, and metadata |

### Protocols (Structural Contracts)
| Symbol | Type | Description |
|---|---|---|
| `ComponentProtocol` | Protocol | Structural contract for pipeline components (`run`, `degrade`, `can_handle`) — duck-typing, `runtime_checkable` |
| `EvaluatorProtocol` | Protocol | Structural contract for evaluators extending `ComponentProtocol` with `evaluate_pair` |
| `RegistrableProtocol` | Protocol | Minimal contract for registry entries (requires `version`) |

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
| `RegistrationConflictError` | Exception | Raised on duplicate registration under `EXPLICIT` policy |
| `ResolutionError` | Exception | Raised when registry lookup fails |
| `ConflictPolicy` | Enum | Strategy for resolving registration key collisions (`NAMESPACED`, `HIGHEST_VERSION`, `EXPLICIT`) |
| `ManifestScanner` | Class | File and entrypoint scanner discovering extensions via `lingualdub.manifest.json` |
| `ManifestError` | Exception | Raised when an extension manifest cannot be found or parsed |

### Configuration
| Symbol | Type | Description |
|---|---|---|
| `FrameworkConfig` | Class | Centralised, validated, immutable framework configuration |
| `SecurityConfig` | Class | Security limits (`max_segment_length`, `max_metadata_depth`, `path_traversal_check_enabled`) |
| `load_config` | Function | Factory that builds a validated `FrameworkConfig` from defaults → env vars → overrides |

### Lifecycle
| Symbol | Type | Description |
|---|---|---|
| `FrameworkLifecycle` | Class | Deterministic state machine (`UNINITIALIZED→...→STOPPED`) with startup/shutdown hook registry |
| `LifecycleState` | Enum | Ordered lifecycle stages (`UNINITIALIZED`, `CONFIGURING`, `CONFIGURED`, `INITIALIZING`, `READY`, `RUNNING`, `SHUTTING_DOWN`, `STOPPED`) |
| `startup_hook` | Decorator | Module-level decorator marking a function as a startup hook (`@startup_hook(name, depends_on)`) |
| `shutdown_hook` | Decorator | Module-level decorator marking a function as a shutdown hook (`@shutdown_hook(name)`) |

### Dependency Injection (`lingualdub.di`)
| Symbol | Type | Description |
|---|---|---|
| `DependencyContainer` | Class | Explicit container (`register`, `register_instance`, `resolve`, `list_registered`, `create_scope`, `override`/`override_context`, circular detection) |
| `DependencyScope` | Class | Scoped context manager for `SCOPED` lifetime; `close()` called on exit, nested scopes raise `LifecycleError` |
| `DependencyDescriptor` | Class | Descriptor `name`, `type_hint`, `lifetime`, `default` (sentinel `_MISSING`) |
| `Lifetime` | Enum | `SINGLETON` (per container), `SCOPED` (per scope), `TRANSIENT` (per resolve) |
| `Dependency` | Descriptor/Annotation | Marker `Dependency[SomeService]` via `Annotated`; supports field injection and `isinstance` checks |

### Extensions (`lingualdub.extensions`)
| Symbol | Type | Description |
|---|---|---|
| `Plugin` | Class | Base plugin dataclass (`name`, `version`, `description`, `author`, `dependencies`/`depends_on`, `state`, `on_startup`/`on_shutdown`) |
| `PluginRegistry` | Class | Registry (`register_plugin`, `get_plugin`, `list_plugins`, `list_failed_plugins`, `discover` via entry_points, `initialize_all`/`shutdown_all` with fail_fast) |
| `PluginState` | Enum | `REGISTERED`/`INITIALIZING`/`ACTIVE`/`FAILED`/`STOPPED` |
| `ComponentExtension` | Protocol | Stable stage extension (`name`, `version`, `task`, `requires`/`provides`, `run`/`degrade`/`can_handle`) |
| `LanguageExtension` | Protocol | Stable language profile extension (`code`, `name`, `family`, `resource_profile`, etc.) |
| `ResourceExtension` | Protocol | Stable resource extension (`id`, `kind`, `language`, `version`, etc.) |
| `EvaluatorExtension` | Protocol | Experimental evaluator (`evaluate_pair` plus component fields) |
| `MiddlewareExtension` | Protocol | Experimental middleware (`name`, `priority`, `before`/`after`/`on_error`) |

### Middleware (`lingualdub.middleware`)
| Symbol | Type | Description |
|---|---|---|
| `MiddlewareProtocol` | Protocol | Cross-cutting `name`/`priority` (lower outermost), `before`/`after`/`on_error` |
| `MiddlewareChain` | Class | Composes middleware in priority order, handles short-circuit and error recovery (`run`, `build`) |
| `MiddlewareRegistry` | Class | Global/scoped registry (`register`/`remove`/`list_middleware`/`build_chain`) |
| `ExecutionContext` | Class | Pipeline execution context (`pipeline_name`, `input`, `run_id`, `metadata`, `short_circuit`) |
| `LoggingMiddleware` | Class | Built-in: logs start/end/error (priority 10) |
| `TimingMiddleware` | Class | Built-in: adds `execution_time_ms` to `Result.metadata` (priority 20) |
| `ConsentMiddleware` | Class | Built-in: raises `ConsentViolationError` if consent absent (priority 5) |

### Observability (`lingualdub.observability`)
| Symbol | Type | Description |
|---|---|---|
| `configure_logging` | Function | Configure structured logging (`json`/`text`) with redaction |
| `get_logger` | Function | Return structured logger for a module |
| `RedactionFilter` | Class | Logging filter that replaces sensitive fields with `[REDACTED]` |
| `MetricsBackend` | Protocol | Metrics protocol (`counter`/`histogram`/`gauge`) |
| `NoOpMetricsBackend` | Class | No-op metrics backend (default, zero overhead) |
| `PrometheusMetricsBackend` | Class | Prometheus metrics backend |
| `StatsdMetricsBackend` | Class | StatsD metrics backend (requires `statsd`) |
| `CaptureMetricsBackend` | Class | In-memory capture backend for tests |
| `configure_metrics` | Function | Configure global metrics backend from `FrameworkConfig` |
| `get_metrics_backend` / `set_metrics_backend` | Functions | Global metrics backend access |
| `TracingBackend` | Protocol | Tracing protocol (`start_span`/`end_span`) |
| `NoOpTracingBackend` | Class | No-op tracing backend |
| `OpenTelemetryTracingBackend` | Class | OpenTelemetry tracing backend |
| `CaptureTracingBackend` | Class | In-memory capture backend for tests |
| `get_tracing_backend` / `set_tracing_backend` | Functions | Global tracing backend access |

### Validation (`lingualdub.utils.validation` via top-level)
| Symbol | Type | Description |
|---|---|---|
| `validate_resource_path` | Function | Validate file path against traversal, null bytes, and length |
| `validate_metadata_depth` | Function | Validate metadata dict nesting depth |
| `validate_segment_text_length` | Function | Validate `Segment.text` length limit |

### Centralized Types (`lingualdub.types`)
| Symbol | Type | Description |
|---|---|---|
| `LanguageCode` | TypeAlias | BCP-47 / ISO 639-3 language code (`str`, e.g. `"lug"`) |
| `PathLike` | TypeAlias | Filesystem path (`str | os.PathLike | Path`) |
| `MetadataDict` | TypeAlias | Free-form metadata dict (`dict[str, Any]`) |
| `ProvenanceDict` | TypeAlias | Structured provenance dict (`dict[str, Any]`) |
| `AudioTensor` | TypeAlias | Audio tensor (`Any` — `torch.Tensor` / `numpy.ndarray` at runtime) |
| `TimestampInterval` | TypeAlias | Time interval (`tuple[float, float]`) |

### Utilities & Management
| Symbol | Type | Description |
|---|---|---|
| `ResourceManager` | Class | Local asset manager verifying sha256 checksums and managing downloads |
| `ChecksumError` | Exception | Raised when a resource file's checksum fails verification |
| `ResourceNotFoundError` | Exception | Raised when a requested resource is not available locally or remotely |
| `ResourceOwnership` | Enum | Ownership semantics (`FRAMEWORK_OWNED`, `USER_OWNED`, `SHARED`) — see `docs/resources.md` |
| `ResourcePool` | Class | Pool managing creation, reuse, and cleanup of expensive resources (`acquire`/`release`, `max_size`/`min_idle`, `total`/`idle`/`active`) |
| `PooledResource` | Class | Wrapper around a pooled instance (context manager, `resource`, `name`, `release`) |
| `make_run_id` | Function | Generates a collision-resistant timestamped run ID |
| `make_provenance` | Function | Assembles a structured provenance record for pipeline execution |
| `compare_runs` | Function | Compares two execution runs across evaluation metrics |
| `ProvenanceMismatchError` | Exception | Raised when comparing runs generated under incompatible configurations |
| `__version__` | String | Package version string |

### Exception Hierarchy (`lingualdub.exceptions`)
| Symbol | Type | Description |
|---|---|---|
| `LingualDubError` | Exception | Base for all framework errors (`message`, `code`, `context`) |
| `ConfigurationError` | Exception | Base for configuration problems |
| `ConfigurationValidationError` | Exception | Field validation failure (also `ValueError`) |
| `LifecycleError` | Exception | Illegal lifecycle transition |
| `InitializationError` | Exception | Startup hook / init failure |
| `ShutdownError` | Exception | Shutdown hook failure |
| `PipelineError` | Exception | Base for pipeline errors |
| `StageCompatibilityError` | Exception | Incompatible stage capabilities |
| `StageExecutionError` | Exception | Stage aborted under `ABORT` |
| `RegistryError` | Exception | Base for registry errors |
| `RegistrationConflictError` | Exception | Duplicate `(kind,key)` under `EXPLICIT` |
| `ResolutionError` | Exception | Registry lookup miss |
| `ComponentError` | Exception | Base for component failures |
| `ComponentContractError` | Exception | Component violates contract |
| `ResourceError` | Exception | Base for resource failures |
| `ResourceNotFoundError` | Exception | Resource not found |
| `ResourceLoadError` | Exception | Resource load/checksum failure |
| `ConsentViolationError` | Exception | Consent check failure |
| `SerializationError` | Exception | `to_dict`/`from_dict` schema violation |
| `InternalError` | Exception | Internal invariant violation |

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
- `ResourcePool` / `PooledResource` — pooled resource management (REL-002)

### `lingualdub.testing` (REL-005)
- `LanguageBuilder` / `ResourceBuilder` / `SegmentBuilder` / `ResultBuilder` — fluent builders
- `FakeASR` / `FakeTranslation` / `FakeTTS` / `FakeAlignment` / `FakeEvaluator` — deterministic fakes
- `assert_result_complete` / `assert_result_failed` / `assert_result_has_segment` / `assert_result_has_language` — matchers
- `PipelineTestHarness` — end-to-end harness (`run`, `run_with_config`)
- `FakeClock` — deterministic clock (`advance`, `sleep`, `install`)

### `lingualdub.async_utils` (REL-004)
- `run_pipeline_async(executor, input)` — `await` pipeline without blocking loop
- `AsyncPipelineExecutor(executor).run(input)` — async wrapper

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
