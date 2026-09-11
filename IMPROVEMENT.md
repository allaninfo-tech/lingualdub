# IMPROVEMENT.md — LingualDub Framework Engineering Roadmap

> **Purpose:** Define the target professional state of the LingualDub framework and the ordered task sequence required to reach it.
>
> **This is a future roadmap, not a code review.** Tasks describe what must be *built or established*, not what is currently broken.
>
> **Task discipline:** Complete one task at a time — Understand → Implement → Test → Verify → Commit → Push → STOP.
>
> **Deep Codebase Analysis & Dynamic Discovery Principle:**
> While this roadmap outlines the primary architectural milestones, each phase requires active empirical analysis of the existing codebase before and during execution. Any concrete technical gaps, missing typing constructs, unspoken assumptions, or edge cases discovered through deep analysis of the codebase must be added into that phase's task list (e.g., FND-007, FND-008, FND-009) and satisfied to achieve genuine production quality.

---

## Roadmap Overview

```text
Phase 1 — Core Foundation (FND)
        ↓
Phase 2 — Lifecycle & Initialization (LCY)
        ↓
Phase 3 — Execution Architecture (EXE)
        ↓
Phase 4 — Extensibility & Plugins (EXT)
        ↓
Phase 5 — Reliability & Resources (REL)
        ↓
Phase 6 — Production Quality (PRO)
        ↓
Phase 7 — Performance & Evolution (PEV)
```

---

## Phase 1 — Core Foundation

> Establish the base contracts, error model, configuration system, and public/private API boundaries that all other phases depend on.

---

### FND-001 — Define Public/Private API Boundaries

**Area:** Abstraction
**Phase:** 1
**Priority:** Critical

**Goal:**
Establish a single authoritative definition of what constitutes the public API of the framework versus its internal implementation details.

**What should be built/improved:**
- Create `lingualdub/PUBLIC_API.md` documenting the complete list of public-facing symbols: classes, functions, enumerations, and dataclasses that external users may depend on.
- Apply `__all__` to every `__init__.py` in the `lingualdub` package, explicitly restricting exports to public symbols.
- Prefix all internal implementation symbols with a single underscore (`_`) consistently.
- Mark internal modules with a module-level comment `# Internal — not part of public API`.

**Why it matters:**
Without defined boundaries, users will accidentally import internal symbols, making refactoring impossible without breaking callers. Clear boundaries allow internals to be freely restructured.

**Dependencies:** None

**Expected outcome:**
Running `python -c "import lingualdub; print(dir(lingualdub))"` shows only intentionally public names. All public symbols are listed in `PUBLIC_API.md`.

**Tests required:**
- Test that every symbol listed in `PUBLIC_API.md` is importable from the top-level `lingualdub` namespace.
- Test that internal symbols are not importable from the top-level namespace.

**Verification required:**
Code review confirms `__all__` is present in all `__init__.py` files and every public name is documented.

**Definition of Done:**
`PUBLIC_API.md` exists and is accurate. All `__init__.py` files have `__all__`. All internal symbols are prefixed with `_`. Tests pass confirming importable public surface and blocked internal surface.

---

### FND-002 — Establish Framework Exception Hierarchy

**Area:** Error Handling
**Phase:** 1
**Priority:** Critical

**Goal:**
Define a structured, hierarchical exception model that distinguishes framework errors from application errors, with specific subtypes for configuration, validation, lifecycle, and infrastructure failures.

**What should be built/improved:**
- Create `lingualdub/exceptions.py` as the single source of truth for all framework exceptions.
- Define the following hierarchy:
  ```
  LingualDubError (base)
  ├── ConfigurationError
  │   └── ConfigurationValidationError
  ├── LifecycleError
  │   ├── InitializationError
  │   └── ShutdownError
  ├── PipelineError
  │   ├── StageCompatibilityError
  │   └── StageExecutionError
  ├── RegistryError
  │   ├── RegistrationConflictError
  │   └── ResolutionError
  ├── ComponentError
  │   └── ComponentContractError
  ├── ResourceError
  │   ├── ResourceNotFoundError
  │   ├── ResourceLoadError
  │   └── ConsentViolationError
  └── InternalError
  ```
- Each exception class must carry: a human-readable `message`, an optional machine-readable `code` (e.g. `"STAGE_COMPAT_001"`), and optional `context` dict for structured details.
- Export all exceptions from `lingualdub/__init__.py` via `__all__`.

**Why it matters:**
Without a hierarchy, callers cannot catch framework errors at an appropriate granularity. Structured exceptions enable automated monitoring, useful error messages, and testable error paths.

**Dependencies:** FND-001

**Expected outcome:**
Any framework error raised by LingualDub is a subclass of `LingualDubError`. Callers can `except ConfigurationError` to handle config problems without catching lifecycle errors.

**Tests required:**
- Test that every defined exception is importable from `lingualdub`.
- Test that each exception is a subclass of the expected parent.
- Test that creating each exception with valid arguments succeeds and `.message`, `.code`, `.context` are accessible.

**Verification required:**
All `raise` statements in the codebase either raise a `LingualDubError` subclass or are explicitly justified with an inline comment.

**Definition of Done:**
`exceptions.py` exists with the full hierarchy. All exceptions exported. Every exception has `message`, `code`, `context`. Tests pass. No `raise ValueError(...)` or `raise RuntimeError(...)` in framework code without justification.

---

### FND-003 — Establish Framework Configuration System

**Area:** Configuration
**Phase:** 1
**Priority:** Critical

**Goal:**
Define a typed, validated, centralized configuration model with support for defaults, environment variable overrides, validation at load time, and immutability after initialization.

**What should be built/improved:**
- Create `lingualdub/config.py` with a `FrameworkConfig` dataclass (or Pydantic model if already a dependency).
- Configuration must support:
  - Default values for every field.
  - Optional environment variable overrides via a naming convention (e.g. `LINGUALDUB_LOG_LEVEL`).
  - Explicit `validate()` method that raises `ConfigurationValidationError` on invalid values.
  - Frozen/immutable state after `validate()` is called.
- Create a `Config` section covering: log level, default failure mode, registry conflict policy, resource manager path, consent enforcement enabled/disabled.
- Provide a `load_config(overrides: dict | None = None) -> FrameworkConfig` factory that applies defaults → env vars → explicit overrides, in that precedence order.

**Why it matters:**
Without centralized config, components each read env vars independently, making testing difficult and behavior unpredictable. Type-safe config catches errors at startup, not during execution.

**Dependencies:** FND-002

**Expected outcome:**
Calling `load_config()` returns a validated, immutable `FrameworkConfig`. Passing `overrides={"log_level": "invalid"}` raises `ConfigurationValidationError`. Setting `LINGUALDUB_LOG_LEVEL=DEBUG` in the environment takes effect.

**Tests required:**
- Test that `load_config()` returns a valid config with all defaults.
- Test that env var overrides take effect.
- Test that explicit overrides take precedence over env vars.
- Test that invalid values raise `ConfigurationValidationError`.
- Test that mutating a frozen config raises an error.

**Verification required:**
No component reads environment variables directly — all go through `FrameworkConfig`.

**Definition of Done:**
`config.py` exists. `FrameworkConfig` covers all framework-wide settings. `load_config()` applies correct precedence. Validation raises correct exception. Immutability enforced. Tests pass.

---

### FND-004 — Define Component Contract Protocol

**Area:** Abstraction / API & Contracts
**Phase:** 1
**Priority:** High

**Goal:**
Define a formal `Protocol` (PEP 544) for what it means to be a component in the framework, making type checking structural rather than inheritance-dependent.

**What should be built/improved:**
- In `lingualdub/core/protocols.py`, define:
  ```python
  class ComponentProtocol(Protocol):
      name: str
      version: str
      task: ComponentTask
      supported_languages: list[str]
      requires: list[str]
      provides: list[str]
      on_failure: FailureMode

      def run(self, input: Result | Resource) -> Result: ...
      def degrade(self, input: Result | Resource) -> Result: ...
      def can_handle(self, language: str) -> bool: ...
  ```
- Define `EvaluatorProtocol`, `RegistrableProtocol` similarly.
- Add `runtime_checkable=True` so `isinstance()` checks work.
- Update type annotations in `Pipeline`, `Registry`, and `PipelineExecutor` to reference these protocols rather than abstract base classes.

**Why it matters:**
Protocols allow duck-typed components to satisfy the framework without inheriting from specific base classes. This makes the framework more composable and supports third-party implementations without requiring import of framework internals.

**Dependencies:** FND-001, FND-002

**Expected outcome:**
A third-party class with the correct attributes and methods satisfies `isinstance(obj, ComponentProtocol)` without inheriting from `Component`. mypy accepts protocol-typed arguments.

**Tests required:**
- Test that the abstract base `Component` satisfies `ComponentProtocol`.
- Test that a standalone class with matching shape satisfies the protocol.
- Test that a class missing a required method fails the protocol check.

**Verification required:**
mypy reports no errors on protocol usage for `core/protocols.py`.

**Definition of Done:**
`protocols.py` exists with all three protocols. `runtime_checkable=True`. Types updated in `Pipeline`, `Registry`, `PipelineExecutor`. Tests pass. mypy passes on `protocols.py`.

---

### FND-005 — Establish Input Validation Utilities

**Area:** API & Contracts
**Phase:** 1
**Priority:** High

**Goal:**
Create a shared input validation utility module that all framework components use for consistent, safe argument validation at API boundaries.

**What should be built/improved:**
- Create `lingualdub/utils/validation.py` with:
  - `require_non_empty_string(value, field_name)` — raises `ConfigurationValidationError`.
  - `require_positive_number(value, field_name)`.
  - `require_one_of(value, allowed, field_name)`.
  - `require_not_none(value, field_name)`.
  - `validate_language_code(code)` — validates BCP-47 or ISO 639-3 format.
  - `validate_version_string(version)` — validates `MAJOR.MINOR.PATCH` format.
- All validators raise the appropriate subclass of `LingualDubError`.
- Apply these validators in `Language`, `Resource`, `Segment`, `Component`, and `Pipeline` constructors.

**Why it matters:**
Consistent validation at API entry points produces clear, early error messages instead of cryptic failures deep in the pipeline. Centralizing validators prevents duplicated validation logic.

**Dependencies:** FND-002

**Expected outcome:**
Constructing a `Resource` with `language=""` raises `ConfigurationValidationError("language must be a non-empty string")` immediately, not a `KeyError` at pipeline execution time.

**Tests required:**
- Unit test each validator with valid and invalid inputs.
- Test that `Resource(language="")` raises `ConfigurationValidationError`.
- Test that `Language(code="")` raises `ConfigurationValidationError`.

**Verification required:**
All public constructors in the framework call at least one validator.

**Definition of Done:**
`validation.py` exists with all listed validators. Constructors of `Language`, `Resource`, `Segment`, `Component`, `Pipeline` call appropriate validators. Tests pass. No raw `if not x: raise ValueError` patterns remain in public constructors.

---

### FND-006 — Establish Stable Result and Segment Contracts

**Area:** API & Contracts
**Phase:** 1
**Priority:** High

**Goal:**
Make `Result` and `Segment` fully immutable, self-validating value objects with explicit factories for mutation (producing new instances), consistent provenance, and documented edge-case behaviour.

**What should be built/improved:**
- Convert `Result` to a frozen dataclass or enforce immutability via `__setattr__`.
- Add `Result.replace(**changes) -> Result` factory for producing modified copies.
- Remove all direct mutations in framework code — use `replace()` instead.
- Add `Segment.replace(**changes) -> Segment` similarly.
- Document the meaning and invariants of every field in both classes as docstrings.
- Ensure `ResultStatus` transitions are documented: which statuses can follow which.

**Why it matters:**
Mutable result objects allow pipeline stages to inadvertently corrupt shared state. Immutable value objects make pipelines easier to reason about and test.

**Dependencies:** FND-005

**Expected outcome:**
`result.status = ResultStatus.FAILED` after construction raises `FrozenInstanceError`. `result.replace(status=ResultStatus.FAILED)` returns a new `Result`. All framework mutations go through `replace()`.

**Tests required:**
- Test that direct mutation of `Result` raises `FrozenInstanceError`.
- Test that `replace()` returns a new instance with the changed fields and identical other fields.
- Test that `replace()` with invalid field values raises `ConfigurationValidationError`.

**Verification required:**
Grep confirms no `result.field = ...` assignments remain in framework code.

**Definition of Done:**
`Result` and `Segment` are immutable. `replace()` factories exist. All fields documented with invariants. Tests pass. No direct mutation in framework code.

---

### FND-007 — Centralized Common Types and Aliases

**Area:** Abstraction / API & Contracts
**Phase:** 1
**Priority:** High

**Goal:**
Create a dedicated `lingualdub/types.py` module defining centralized type aliases and common data contracts across all framework components, avoiding duplicated and inconsistent type annotations.

**What should be built/improved:**
- Create `lingualdub/types.py` with standard type definitions:
  - `PathLike = str | os.PathLike[str] | Path`
  - `LanguageCode = str` (BCP-47 or ISO 639-3 format)
  - `MetadataDict = dict[str, Any]`
  - `ProvenanceDict = dict[str, Any]`
  - `AudioTensor = Any`
  - `TimestampInterval = tuple[float, float]`
- Re-export common types from `lingualdub/__init__.py`.
- Update core models (`Resource`, `Result`, `Segment`, `Component`) to use these centralized types.

**Why it matters:**
Ad-hoc typing (`str | None`, `dict`, `Any`) across 15+ component files leads to recurring mypy regressions and subtle type mismatches at pipeline integration boundaries.

**Dependencies:** FND-001, FND-004

**Expected outcome:**
All component interfaces consistently use `PathLike`, `MetadataDict`, `LanguageCode`, and `ProvenanceDict` without ad-hoc type aliases scattered across files.

**Tests required:**
- Test that all exported types in `types.py` are importable from `lingualdub`.
- Type check with `mypy lingualdub` to verify consistency.

**Verification required:**
`mypy lingualdub` passes with zero errors against `types.py`.

**Definition of Done:**
`types.py` exists with all canonical type aliases. Core abstractions updated. Exports updated. Tests and mypy pass.

---

### FND-008 — Robust Serialization and Deserialization Contracts

**Area:** API & Contracts / Reliability
**Phase:** 1
**Priority:** High

**Goal:**
Standardize and harden `to_dict()` and `from_dict()` across `Result`, `Segment`, `Resource`, and `Language` with explicit schema validation, handling missing/corrupted fields, and providing round-trip idempotency guarantees.

**What should be built/improved:**
- Enhance `Segment.from_dict()` and `Result.from_dict()`:
  - Validate required keys with specific descriptive exceptions (`SerializationError` or `ConfigurationValidationError`).
  - Validate data types (e.g. `start` must be numeric and `>= 0`).
  - Gracefully handle schema evolution (e.g. unknown keys preserved in metadata rather than crashing).
- Add `Resource.to_dict()` and `Resource.from_dict()`.
- Add `Language.to_dict()` and `Language.from_dict()`.
- Ensure round-trip idempotence: `cls.from_dict(obj.to_dict()) == obj`.

**Why it matters:**
Pipelines serialize results and segments to disk and across network/process boundaries. Malformed inputs currently trigger unhandled `KeyError` or `TypeError` crashes during deserialization.

**Dependencies:** FND-002, FND-005, FND-006

**Expected outcome:**
Passing malformed JSON or a dict with missing required keys to `Segment.from_dict()` raises a clear `SerializationError` stating exactly which field was invalid. Valid instances serialize and deserialize with 100% round-trip equality.

**Tests required:**
- Round-trip serialization tests for `Result`, `Segment`, `Resource`, `Language`.
- Error tests verifying that missing or invalid keys raise `SerializationError`.
- Backward-compatibility tests verifying that legacy or extra metadata fields are safely retained.

**Verification required:**
Tests verify round-trip fidelity and error messages on malformed dictionaries.

**Definition of Done:**
`to_dict()` and `from_dict()` implemented and hardened across all four core classes. Schema errors raise structured framework exceptions. Round-trip tests pass.

---

### FND-009 — Manifest Schema Enforcement & Scanner Validation

**Area:** Extensibility / Configuration
**Phase:** 1
**Priority:** High

**Goal:**
Enforce strict JSON schema validation and early integrity verification on `lingualdub.manifest.json` via `ManifestScanner`, catching malformed components, invalid task names, and duplicate registrations before execution.

**What should be built/improved:**
- Create `lingualdub/registry/manifest_schema.json` (or inline JSON Schema) formalizing the manifest structure.
- In `ManifestScanner`:
  - Validate manifest JSON against schema during `scan_file()` and `scan_installed()`.
  - Validate that declared `task` matches a valid `ComponentTask` enum.
  - Verify that declared `entrypoint` classes actually exist and are importable when requested.
  - Raise `ManifestError` with the file path, section, and specific violation.

**Why it matters:**
Manifests are the backbone of dynamic component discovery. A typo in a manifest currently fails silently or causes a late runtime crash when a pipeline is executed.

**Dependencies:** FND-002, FND-004

**Expected outcome:**
A manifest with an invalid task string like `"audio_processing"` fails with `ManifestError: Invalid task 'audio_processing' for component 'foo'; must be one of ComponentTask values` immediately during scan.

**Tests required:**
- Test valid manifest passes validation.
- Test manifest with invalid task fails with `ManifestError`.
- Test manifest with missing required fields fails with `ManifestError`.

**Verification required:**
Existing `lingualdub.manifest.json` passes schema validation.

**Definition of Done:**
Manifest schema defined and enforced in `ManifestScanner`. Detailed error messages on invalid manifests. Tests pass.

---

## Phase 2 — Lifecycle & Initialization

> Establish deterministic application lifecycle: startup, initialization, shutdown, and failure handling at each stage.

---

### LCY-001 — Define Framework Lifecycle Model

**Area:** Inversion of Control & Lifecycle
**Phase:** 2
**Priority:** Critical

**Goal:**
Define the formal lifecycle model of the framework: the ordered stages of startup and shutdown, what happens at each stage, and how lifecycle failures are handled.

**What should be built/improved:**
- Document in `docs/lifecycle.md`:
  - Lifecycle stages: `UNINITIALIZED → CONFIGURING → CONFIGURED → INITIALIZING → READY → RUNNING → SHUTTING_DOWN → STOPPED`.
  - What occurs at each stage.
  - Which stage is responsible for: config validation, component registration, registry resolution, resource acquisition, pipeline assembly, execution.
  - How failures at each stage are surfaced and what cleanup occurs.
- Create `lingualdub/lifecycle.py` with a `LifecycleState` enum covering the above states.
- Create `FrameworkLifecycle` class with `.state` property and state-transition validation.

**Why it matters:**
Without a formal lifecycle, components initialize in undefined order, leading to race conditions, partial initialization, and obscure startup failures that are hard to debug.

**Dependencies:** FND-002, FND-003

**Expected outcome:**
The framework can be queried for its current lifecycle state at any time. Attempting to execute a pipeline while `state == INITIALIZING` raises `LifecycleError`.

**Tests required:**
- Test that state transitions proceed in legal order.
- Test that illegal state transitions raise `LifecycleError`.
- Test that the framework reports the correct state at each stage.

**Verification required:**
`docs/lifecycle.md` exists and matches the implementation.

**Definition of Done:**
`lifecycle.py` exists. `LifecycleState` enum defined. `FrameworkLifecycle` class with state-transition validation. `docs/lifecycle.md` documents the model. Tests pass.

---

### LCY-002 — Implement Application Startup Hooks

**Area:** Inversion of Control & Lifecycle
**Phase:** 2
**Priority:** High

**Goal:**
Provide a mechanism for registering startup hooks — callbacks invoked in a deterministic order during the INITIALIZING stage — with support for dependency-ordered hook execution.

**What should be built/improved:**
- Add to `FrameworkLifecycle`:
  - `register_startup_hook(name: str, hook: Callable[[], None], depends_on: list[str] | None = None)`.
  - Hook execution respects declared dependencies (topological ordering).
  - If a hook raises, `InitializationError` is raised wrapping the original exception, and no further hooks run.
- Provide a `@startup_hook(name, depends_on=None)` decorator as a convenience.

**Why it matters:**
Startup hooks allow component initialization to declare ordering constraints explicitly, preventing race conditions and undefined initialization order in complex deployments.

**Dependencies:** LCY-001

**Expected outcome:**
Two hooks registered with `depends_on` ordering always execute in the declared order. A failing hook stops initialization and raises `InitializationError` with the hook name and original error.

**Tests required:**
- Test that hooks run in dependency order.
- Test that hooks without dependencies run before dependent hooks.
- Test that a failing hook raises `InitializationError` and stops the sequence.
- Test that circular hook dependencies raise `LifecycleError`.

**Verification required:**
Topological sort correctly handles: no deps, linear deps, diamond deps, and cycles.

**Definition of Done:**
`register_startup_hook()` and `@startup_hook` decorator exist. Hooks run in topological order. Failures raise `InitializationError`. Circular deps raise `LifecycleError`. Tests pass.

---

### LCY-003 — Implement Shutdown Hooks and Deterministic Teardown

**Area:** Inversion of Control & Lifecycle
**Phase:** 2
**Priority:** High

**Goal:**
Provide symmetrical shutdown hooks that execute in reverse dependency order, ensuring resources are released deterministically and partial initialization failures trigger appropriate cleanup.

**What should be built/improved:**
- Add to `FrameworkLifecycle`:
  - `register_shutdown_hook(name: str, hook: Callable[[], None])`.
  - Shutdown runs hooks in reverse startup order.
  - If a shutdown hook raises, the error is logged and remaining hooks continue (best-effort teardown).
  - `framework.shutdown()` transitions state through `SHUTTING_DOWN → STOPPED`.
- Add Python `atexit` registration to ensure `shutdown()` is called on normal interpreter exit.
- Handle the case where `shutdown()` is called before `startup()` completes (partial initialization cleanup).

**Why it matters:**
Without deterministic teardown, resources leak, file handles stay open, and background threads keep running.

**Dependencies:** LCY-002

**Expected outcome:**
Calling `framework.shutdown()` after startup runs all registered shutdown hooks in reverse order. A failing shutdown hook logs the error but does not prevent remaining hooks from running.

**Tests required:**
- Test that shutdown hooks run in reverse startup order.
- Test that a failing shutdown hook logs but does not abort teardown.
- Test that calling `shutdown()` before `startup()` does not crash.
- Test that `atexit` registration is present.

**Verification required:**
Manual test: start a framework instance, register resource hooks, call `shutdown()`, confirm resources released.

**Definition of Done:**
`register_shutdown_hook()` exists. Reverse-order execution verified. Failing hooks logged but not fatal. `atexit` registered. Partial teardown safe. Tests pass.

---

### LCY-004 — Implement Lifecycle Testing Utilities

**Area:** Inversion of Control & Lifecycle / Testability
**Phase:** 2
**Priority:** Medium

**Goal:**
Provide testing utilities that allow framework users to write deterministic lifecycle tests.

**What should be built/improved:**
- Create `lingualdub/testing/lifecycle.py` with:
  - `TestFramework` context manager that initializes a fresh framework instance per test and tears it down after.
  - `LifecycleCapture` helper that records all state transitions in order.
  - `assert_lifecycle_sequence(capture, expected_sequence)` assertion helper.
- Document usage in `docs/testing.md`.

**Why it matters:**
Without testing utilities, tests that touch lifecycle code are fragile, share global state, and are difficult to isolate.

**Dependencies:** LCY-001, LCY-002, LCY-003

**Expected outcome:**
A test using `with TestFramework() as fw:` gets an isolated framework instance, and state transitions are capturable and assertable.

**Tests required:**
- Test that `TestFramework` provides an isolated, initialized framework instance.
- Test that `LifecycleCapture` records all transitions.
- Test that two concurrent `TestFramework` contexts do not share state.

**Verification required:**
Tests using `TestFramework` do not interfere with each other when run in parallel.

**Definition of Done:**
`testing/lifecycle.py` exists. `TestFramework`, `LifecycleCapture`, `assert_lifecycle_sequence` implemented. `docs/testing.md` documents usage. Tests pass.

---

## Phase 3 — Execution Architecture

> Establish the dependency injection system, pipeline executor contract, and middleware model.

---

### EXE-001 — Define Dependency Contract

**Area:** Dependency Injection
**Phase:** 3
**Priority:** Critical

**Goal:**
Define the formal concept of a "dependency" in the framework: what a dependency is, how it is declared, what a dependency descriptor looks like, and the lifetime categories.

**What should be built/improved:**
- Create `lingualdub/di/contracts.py` with:
  - `DependencyDescriptor` dataclass: `name`, `type_hint`, `lifetime: Lifetime`, `default: Any | _MISSING`.
  - `Lifetime` enum: `SINGLETON`, `SCOPED`, `TRANSIENT`.
  - `Dependency` — a descriptor applied to class fields via annotation or decorator.
- Document the semantics of each lifetime: when created, when reused, when destroyed.

**Why it matters:**
A formal dependency contract is the prerequisite for any injection system.

**Dependencies:** FND-001, FND-002, FND-004

**Expected outcome:**
A class can declare `my_dep: Dependency[SomeService]` and the DI container can inspect and resolve it.

**Tests required:**
- Test that `DependencyDescriptor` stores name, type, lifetime, and default correctly.
- Test that `Lifetime` has exactly the three expected values.

**Verification required:**
Code review of `contracts.py` confirms no implementation logic — purely definitions.

**Definition of Done:**
`di/contracts.py` exists with `DependencyDescriptor`, `Lifetime`, and `Dependency` definitions. Tests pass.

---

### EXE-002 — Implement Dependency Registration

**Area:** Dependency Injection
**Phase:** 3
**Priority:** Critical

**Goal:**
Implement a dependency container that allows explicit registration of services with their lifetime, implementation, and optional factory functions.

**What should be built/improved:**
- Create `lingualdub/di/container.py` with `DependencyContainer`:
  - `register(name, implementation_or_factory, lifetime=Lifetime.SINGLETON)`.
  - `register_instance(name, instance)` — registers a pre-built singleton.
  - Raises `RegistrationConflictError` on duplicate names unless `override=True` is passed.
  - `list_registered() -> list[str]` for inspection.

**Why it matters:**
Explicit registration makes dependencies visible and auditable.

**Dependencies:** EXE-001

**Expected outcome:**
`container.register("registry", Registry, Lifetime.SINGLETON)` stores the binding. Registering the same name twice without `override=True` raises `RegistrationConflictError`.

**Tests required:**
- Test successful registration of a class.
- Test registration of a factory function.
- Test `register_instance()`.
- Test duplicate registration raises `RegistrationConflictError`.
- Test `override=True` replaces the existing binding.

**Verification required:**
`list_registered()` returns exactly the registered names after a sequence of registrations.

**Definition of Done:**
`di/container.py` with `DependencyContainer`. `register()`, `register_instance()`, `list_registered()`. Conflict error raised correctly. Tests pass.

---

### EXE-003 — Implement Dependency Resolution

**Area:** Dependency Injection
**Phase:** 3
**Priority:** Critical

**Goal:**
Implement `DependencyContainer.resolve(name)` that retrieves or constructs the registered service, respecting lifetime semantics.

**What should be built/improved:**
- `resolve(name: str) -> Any`:
  - `SINGLETON`: construct once, cache in container.
  - `TRANSIENT`: construct fresh each call.
- Recursive dependency construction: if the resolved class has `__init__` parameters that are registered names, resolve them too.
- Raises `ResolutionError` if a name is not registered.
- Raises `ResolutionError` if construction fails (wraps original exception).

**Why it matters:**
Resolution is the delivery side of DI. Automatic resolution reduces boilerplate and makes wiring explicit.

**Dependencies:** EXE-002

**Expected outcome:**
`container.resolve("pipeline_executor")` returns a fully constructed `PipelineExecutor` with its dependencies auto-resolved from the container.

**Tests required:**
- Test that `resolve()` returns a singleton on repeated calls.
- Test that `resolve()` of `TRANSIENT` returns new instances.
- Test that nested dependencies are resolved recursively.
- Test that resolving an unregistered name raises `ResolutionError`.
- Test that construction failure raises `ResolutionError` wrapping the original.

**Verification required:**
Singleton identity verified: `container.resolve("x") is container.resolve("x")` for singletons.

**Definition of Done:**
`resolve()` implemented with SINGLETON and TRANSIENT lifetimes. Recursive resolution works. Error cases raise `ResolutionError`. Tests pass.

---

### EXE-004 — Implement Scoped Dependencies

**Area:** Dependency Injection
**Phase:** 3
**Priority:** High

**Goal:**
Implement scoped dependency lifetime where a service is a singleton within a defined scope but a new instance is created for each new scope.

**What should be built/improved:**
- `container.create_scope() -> DependencyScope` context manager.
- Within a scope, `scope.resolve(name)` returns the same instance for `SCOPED` lifetime.
- Outside the scope, new scopes get new instances.
- `DependencyScope.__exit__` calls cleanup on any scoped instances that implement a `close()` method.

**Why it matters:**
Per-execution state must be isolated per pipeline run. Scoped dependencies provide this naturally.

**Dependencies:** EXE-003

**Expected outcome:**
Two calls to `scope.resolve("execution_context")` return the same instance. A new scope returns a new instance. Exiting the scope calls `close()` on scoped instances.

**Tests required:**
- Test that two resolves within the same scope return identical instances.
- Test that two different scopes return different instances.
- Test that `close()` is called on scope exit for instances that have it.
- Test that nested scopes are not supported and raise `LifecycleError`.

**Verification required:**
Scope cleanup verified by testing that a resource's `close()` is called exactly once per scope.

**Definition of Done:**
`create_scope()` implemented. `SCOPED` lifetime works correctly. Scope cleanup calls `close()`. Tests pass.

---

### EXE-005 — Implement Dependency Override for Testing

**Area:** Dependency Injection / Testability
**Phase:** 3
**Priority:** High

**Goal:**
Provide a mechanism for test code to override registered dependencies with fakes or mocks without modifying the container permanently.

**What should be built/improved:**
- `container.override(name, fake_instance)` — temporarily replaces a registration.
- `container.restore(name)` — restores the original.
- `container.override_context(name, fake_instance)` — context manager that auto-restores.
- Overrides apply to `resolve()` immediately.

**Why it matters:**
Without dependency overrides, tests must either construct the full dependency tree or monkeypatch module globals.

**Dependencies:** EXE-003

**Expected outcome:**
Within `container.override_context("registry", FakeRegistry()):`, resolving any service that depends on "registry" gets the `FakeRegistry` instance.

**Tests required:**
- Test that override replaces the resolved instance within context.
- Test that after context exit, original is restored.
- Test that overriding an unregistered name raises `ResolutionError`.

**Verification required:**
Nested override contexts work correctly: inner context restores to outer override, not original.

**Definition of Done:**
`override()`, `restore()`, `override_context()` implemented. Override scope is correct. Tests pass.

---

### EXE-006 — Detect Circular Dependencies

**Area:** Dependency Injection
**Phase:** 3
**Priority:** High

**Goal:**
Detect circular dependency chains at resolution time and raise a clear `ResolutionError` identifying the cycle, rather than hitting Python's recursion limit.

**What should be built/improved:**
- During `resolve()`, maintain a resolution stack.
- If the same name appears in the resolution stack, raise `ResolutionError` with a message like: `Circular dependency detected: A → B → C → A`.
- Detection must work for both direct (`A → A`) and indirect circular dependencies.

**Why it matters:**
Circular dependencies would otherwise cause infinite recursion with an incomprehensible stack trace.

**Dependencies:** EXE-003

**Expected outcome:**
Registering `A` that depends on `B`, and `B` that depends on `A`, then calling `container.resolve("A")` raises `ResolutionError("Circular dependency detected: A → B → A")`.

**Tests required:**
- Test direct circular dependency (`A → A`).
- Test indirect circular dependency (`A → B → A`).
- Test three-node cycle (`A → B → C → A`).
- Test non-circular chain of same length to confirm no false positives.

**Verification required:**
The error message includes the full chain, not just the conflicting node.

**Definition of Done:**
Circular dependency detection implemented. `ResolutionError` includes full chain. Tests pass for direct, indirect, and N-node cycles.

---

### EXE-007 — Add DI Test Suite and Testing Utilities

**Area:** Dependency Injection / Testability
**Phase:** 3
**Priority:** Medium

**Goal:**
Provide a `lingualdub/testing/di.py` module with helpers that make DI testing ergonomic.

**What should be built/improved:**
- `TestContainer` — a `DependencyContainer` pre-populated with fakes for all framework services.
- `FakeRegistry`, `FakeResourceManager`, `FakeLanguage` — minimal fakes for common framework types.
- `assert_resolved_as(container, name, expected_type)` — assertion helper.

**Why it matters:**
Without test utilities, every test that exercises DI must manually construct and populate a container.

**Dependencies:** EXE-005, LCY-004

**Expected outcome:**
A test can do `container = TestContainer()` and immediately resolve any framework service using fakes.

**Tests required:**
- Test that `TestContainer` pre-registers all framework services.
- Test that `FakeRegistry` satisfies `RegistryProtocol`.
- Test that `assert_resolved_as()` passes and fails correctly.

**Verification required:**
`TestContainer` resolves all framework services without raising errors.

**Definition of Done:**
`testing/di.py` exists with `TestContainer`, `FakeRegistry`, `FakeResourceManager`, `FakeLanguage`, and `assert_resolved_as`. Tests pass.

---

## Phase 4 — Extensibility & Plugins

> Establish stable extension points, plugin registration, lifecycle integration, and isolation guarantees.

---

### EXT-001 — Define Extension Point Contracts

**Area:** Extensibility / Plugins
**Phase:** 4
**Priority:** Critical

**Goal:**
Define the formal set of extension points the framework provides and the stable contracts each extension must satisfy.

**What should be built/improved:**
- Create `lingualdub/extensions/contracts.py` defining:
  - `ComponentExtension` — adding new pipeline stage implementations.
  - `LanguageExtension` — registering new language profiles.
  - `ResourceExtension` — registering new resource types.
  - `EvaluatorExtension` — registering custom evaluation strategies.
  - `MiddlewareExtension` — injecting cross-cutting behaviour.
- Each extension type must have: a Protocol definition, required fields, and a declared stability level (`stable` / `experimental`).

**Why it matters:**
Without defined extension points, third-party developers will extend internal classes and break on every refactor.

**Dependencies:** FND-004, FND-001

**Expected outcome:**
A third-party developer can implement `ComponentExtension` without importing anything except from `lingualdub.extensions`.

**Tests required:**
- Test that all framework built-in components satisfy `ComponentExtension` protocol.
- Test that a minimal stub satisfies the protocol.

**Verification required:**
Code review confirms `extensions/contracts.py` imports nothing from internal modules.

**Definition of Done:**
`extensions/contracts.py` exists. All extension protocols defined with stability levels. Built-in components satisfy their protocols. Tests pass.

---

### EXT-002 — Implement Plugin Registration API

**Area:** Extensibility / Plugins
**Phase:** 4
**Priority:** Critical

**Goal:**
Provide a `Plugin` base class and `PluginRegistry` that allow external packages to register themselves as LingualDub plugins.

**What should be built/improved:**
- `lingualdub/extensions/plugin.py`:
  - `Plugin` dataclass: `name`, `version`, `description`, `author`, `dependencies: list[str]`.
  - `PluginRegistry` class with `register_plugin()`, `list_plugins()`, `get_plugin()`.
  - Raises `RegistrationConflictError` on name collision.
- Support `entry_points` (setuptools) for auto-discovery.
- Plugin registration must occur during `CONFIGURING` lifecycle stage only.

**Why it matters:**
Without a plugin system, extension code has no standard way to register itself or declare dependencies.

**Dependencies:** EXT-001, LCY-001, EXE-002

**Expected outcome:**
An installed package with `entry_points = {"lingualdub.plugins": ["my_plugin = my_package:MyPlugin"]}` is auto-discovered and registered on framework startup.

**Tests required:**
- Test manual `register_plugin()` succeeds.
- Test duplicate registration raises `RegistrationConflictError`.
- Test `list_plugins()` returns all registered plugins.
- Test auto-discovery from mocked `entry_points`.

**Verification required:**
Auto-discovery tested with a real temporary package installed in the test environment.

**Definition of Done:**
`extensions/plugin.py` with `Plugin` and `PluginRegistry`. Auto-discovery via `entry_points`. Lifecycle-stage enforcement. Tests pass.

---

### EXT-003 — Implement Plugin Lifecycle Hooks

**Area:** Extensibility / Plugins
**Phase:** 4
**Priority:** High

**Goal:**
Allow plugins to register startup and shutdown hooks that are called during the framework lifecycle.

**What should be built/improved:**
- Extend `Plugin` with:
  - `on_startup(container: DependencyContainer) -> None` — optional override.
  - `on_shutdown() -> None` — optional override.
  - `depends_on: list[str]` — list of plugin names that must initialize before this one.
- `PluginRegistry.initialize_all(container)` — calls `on_startup()` in dependency order.
- `PluginRegistry.shutdown_all()` — calls `on_shutdown()` in reverse order.
- A plugin's `on_startup` failure raises `InitializationError`.

**Why it matters:**
Plugins often need to register services in the DI container or acquire resources at startup.

**Dependencies:** EXT-002, LCY-002, LCY-003

**Expected outcome:**
A plugin that overrides `on_startup()` to register a custom component has that component available for resolution immediately after `initialize_all()`.

**Tests required:**
- Test that `on_startup()` is called for all registered plugins.
- Test that startup ordering respects `depends_on`.
- Test that a failing `on_startup()` raises `InitializationError`.
- Test that `on_shutdown()` is called in reverse startup order.

**Verification required:**
Shutdown hooks tested to confirm they still run when an earlier shutdown hook raises.

**Definition of Done:**
Plugin lifecycle hooks implemented. Ordering respected. Failures surface correctly. Tests pass.

---

### EXT-004 — Implement Plugin Isolation and Failure Handling

**Area:** Extensibility / Plugins
**Phase:** 4
**Priority:** High

**Goal:**
Ensure that a failing or misbehaving plugin does not crash the entire framework.

**What should be built/improved:**
- `PluginRegistry` option: `fail_fast: bool = True`.
  - `fail_fast=True`: plugin startup failure raises `InitializationError` immediately.
  - `fail_fast=False`: plugin startup failure is logged, plugin is marked `FAILED`, initialization continues for non-dependent plugins.
- `Plugin.state` property: `REGISTERED | INITIALIZING | ACTIVE | FAILED | STOPPED`.
- `list_failed_plugins() -> list[Plugin]`.
- Failed plugins must not be resolvable from the DI container.

**Why it matters:**
In production, an optional analytics plugin failing should not prevent the core dubbing pipeline from operating.

**Dependencies:** EXT-003

**Expected outcome:**
With `fail_fast=False`, a plugin that raises in `on_startup()` is marked `FAILED`, logged, and the framework continues. Non-dependent plugins initialize normally.

**Tests required:**
- Test `fail_fast=True` raises `InitializationError` on first failure.
- Test `fail_fast=False` logs failure and continues.
- Test that failed plugins are returned by `list_failed_plugins()`.
- Test that a plugin dependent on a failed plugin is also marked `FAILED`.

**Verification required:**
Non-dependent plugins remain `ACTIVE` when one plugin fails with `fail_fast=False`.

**Definition of Done:**
Plugin state machine implemented. `fail_fast` mode works. `list_failed_plugins()` accurate. Tests pass.

---

### EXT-005 — Implement Middleware Pipeline

**Area:** Middleware / Pipeline
**Phase:** 4
**Priority:** High

**Goal:**
Implement a formal middleware system that wraps pipeline execution with before/after hooks, supports short-circuiting, input/output transformation, and deterministic ordering.

**What should be built/improved:**
- Create `lingualdub/middleware/base.py` with `MiddlewareProtocol`:
  - `name: str`, `priority: int` (lower = outermost).
  - `before(context: ExecutionContext) -> ExecutionContext`.
  - `after(context: ExecutionContext, result: Result) -> Result`.
  - `on_error(context: ExecutionContext, error: Exception) -> Result | None`.
- `ExecutionContext` dataclass: pipeline name, input resource, run ID, metadata dict.
- `MiddlewareChain` that composes a list of middleware in priority order.
- `PipelineExecutor` updated to pass execution through `MiddlewareChain`.

**Why it matters:**
Cross-cutting concerns (logging, timing, consent checking) should not be embedded in pipeline stages.

**Dependencies:** EXE-003, FND-004

**Expected outcome:**
A `LoggingMiddleware` registered at priority 10 logs the start and end of every pipeline execution without modifying any pipeline stage code.

**Tests required:**
- Test that middleware `before()` is called before pipeline execution.
- Test that middleware `after()` is called after pipeline execution.
- Test that multiple middleware execute in priority order (before) and reverse order (after).
- Test that short-circuiting in `before()` skips pipeline execution.
- Test that `on_error()` is called when a stage raises.

**Verification required:**
Order of before/after calls confirmed with a capture list in tests.

**Definition of Done:**
`middleware/base.py` with protocol, `ExecutionContext`, and `MiddlewareChain`. `PipelineExecutor` uses middleware chain. Tests confirm ordering and error behaviour.

---

### EXT-006 — Implement Built-in Middleware: Logging, Timing, Consent

**Area:** Middleware / Pipeline
**Phase:** 4
**Priority:** High

**Goal:**
Ship three built-in middleware implementations using the middleware system defined in EXT-005.

**What should be built/improved:**
- `lingualdub/middleware/logging_mw.py`: `LoggingMiddleware` — logs pipeline name, run ID, start/end/error.
- `lingualdub/middleware/timing_mw.py`: `TimingMiddleware` — adds `execution_time_ms` to `Result.metadata`.
- `lingualdub/middleware/consent_mw.py`: `ConsentMiddleware` — raises `ConsentViolationError` if consent is absent.
- All three registered by default when the framework initializes.

**Why it matters:**
Logging and consent enforcement are currently scattered in component code. Moving them to middleware centralizes them and makes them configurable.

**Dependencies:** EXT-005, FND-002

**Expected outcome:**
Every pipeline execution automatically produces a structured log entry and adds `execution_time_ms` to the result metadata.

**Tests required:**
- Test that `LoggingMiddleware` produces a log record per execution.
- Test that `TimingMiddleware` adds `execution_time_ms` to result metadata.
- Test that `ConsentMiddleware` raises `ConsentViolationError` for unconsented resources.
- Test that `ConsentMiddleware` passes for consented resources.

**Verification required:**
`execution_time_ms` is always a positive number in results.

**Definition of Done:**
Three middleware implemented and auto-registered. Tests pass for each middleware's behaviour and edge cases.

---

### EXT-007 — Implement Middleware Registration and Ordering API

**Area:** Middleware / Pipeline / Extensibility
**Phase:** 4
**Priority:** Medium

**Goal:**
Provide a clean API for registering, removing, and reordering middleware, including scoped middleware (per-pipeline-type) and global middleware.

**What should be built/improved:**
- `MiddlewareRegistry`:
  - `register(middleware, scope="global" | pipeline_name)`.
  - `remove(middleware_name)`.
  - `list_middleware(scope=None) -> list[MiddlewareProtocol]` in priority order.
- `MiddlewareChain.build(pipeline_name)` combines global + scoped middleware in priority order.

**Why it matters:**
Some middleware must apply globally; others only to specific pipeline types.

**Dependencies:** EXT-005, EXT-002

**Expected outcome:**
A middleware registered with `scope="dubbing_pipeline"` only appears in the chain when that pipeline executes.

**Tests required:**
- Test global middleware appears in all pipeline chains.
- Test scoped middleware appears only in the correct pipeline chain.
- Test `remove()` removes middleware from the chain.
- Test priority ordering is correct when mixing global and scoped middleware.

**Verification required:**
Middleware list is ordered correctly after registering middleware with various priorities.

**Definition of Done:**
`MiddlewareRegistry` implemented. Global and scoped registration work. `remove()` and `list_middleware()` correct. Tests pass.

---

## Phase 5 — Reliability & Resources

> Establish resource management, concurrency guarantees, and comprehensive test infrastructure.

---

### REL-001 — Define Resource Ownership Model

**Area:** Resource & State Management
**Phase:** 5
**Priority:** Critical

**Goal:**
Define formal ownership semantics for framework resources.

**What should be built/improved:**
- Document in `docs/resources.md`:
  - Ownership categories: `FRAMEWORK_OWNED`, `USER_OWNED`, `SHARED`.
  - Cleanup responsibility for each category.
- Add `Resource.ownership: ResourceOwnership` field.
- `ResourceManager` only cleans up `FRAMEWORK_OWNED` resources.
- Cleanup called deterministically during scoped dependency teardown.

**Why it matters:**
Without defined ownership, cleanup is either missed (leaks) or double-freed (errors).

**Dependencies:** EXE-004, FND-006

**Expected outcome:**
Creating a resource with `ownership=ResourceOwnership.FRAMEWORK_OWNED` causes it to be cleaned up automatically at scope exit.

**Tests required:**
- Test that `FRAMEWORK_OWNED` resources are cleaned up at scope exit.
- Test that `USER_OWNED` resources are not cleaned up by the framework.

**Verification required:**
A resource's `close()` method is called exactly once and at the right time.

**Definition of Done:**
`ResourceOwnership` enum in `Resource`. Cleanup behaviour implemented. `docs/resources.md` written. Tests pass.

---

### REL-002 — Implement Resource Pool

**Area:** Resource & State Management
**Phase:** 5
**Priority:** Medium

**Goal:**
Implement a resource pool that manages creation, reuse, and cleanup of expensive framework resources, with configurable pool size and timeout.

**What should be built/improved:**
- `lingualdub/resources/pool.py` with `ResourcePool`:
  - `acquire(name: str, timeout_s: float | None = None) -> PooledResource`.
  - `release(resource: PooledResource)`.
  - Context manager protocol for acquire/release.
  - `max_size` and `min_idle` configuration.
  - Pool reports metrics: `total`, `idle`, `active` counts.

**Why it matters:**
Loading a neural model is expensive. Without pooling, every pipeline execution may re-load it.

**Dependencies:** REL-001, FND-003

**Expected outcome:**
Acquiring the same resource twice from a pool of size 2 returns two distinct instances. Acquiring from a full pool with `timeout_s=0` raises `ResourceError`.

**Tests required:**
- Test acquire and release cycle.
- Test that `max_size` is respected.
- Test that timeout raises `ResourceError`.
- Test pool metrics are accurate.

**Verification required:**
Pool never returns the same instance to two concurrent acquirers.

**Definition of Done:**
`ResourcePool` implemented with acquire, release, context manager, max_size, timeout, and metrics. Tests pass.

---

### REL-003 — Implement Concurrency Safety for Registry

**Area:** Concurrency
**Phase:** 5
**Priority:** High

**Goal:**
Make the `Registry` class safe for concurrent reads from multiple threads, with serialized writes, and document its thread-safety guarantees.

**What should be built/improved:**
- Add a `threading.RLock` to `Registry` protecting all write operations (`register()`, `deregister()`).
- Read operations use the same lock for atomicity.
- Add a module-level docstring to `registry.py` stating thread-safety guarantees.

**Why it matters:**
In multi-threaded pipeline execution, multiple threads may read the registry concurrently while a plugin is registering new components.

**Dependencies:** EXE-002, EXT-002

**Expected outcome:**
Running 100 threads simultaneously reading and writing the registry does not raise errors or produce corrupted state.

**Tests required:**
- Concurrent read test: 50 threads reading simultaneously — no errors.
- Concurrent write test: 10 threads writing simultaneously — no state corruption.
- Mixed read/write test.

**Verification required:**
Tests run with `pytest-xdist` in threaded mode.

**Definition of Done:**
`Registry` has `RLock`. Thread-safety documented. Concurrent tests pass.

---

### REL-004 — Implement Async/Sync Boundary Utilities

**Area:** Concurrency
**Phase:** 5
**Priority:** High

**Goal:**
Formally define the framework's synchronous execution model and provide async-compatible utilities for callers using asyncio.

**What should be built/improved:**
- Document in `docs/concurrency.md`:
  - The framework's primary execution model is synchronous.
  - Which operations block (model loading, file I/O, network calls).
  - Recommended patterns for calling from async code.
- Provide `lingualdub/async_utils.py`:
  - `run_pipeline_async(executor, input_resource) -> Coroutine[Result]`.
  - `AsyncPipelineExecutor` — thin async wrapper.

**Why it matters:**
Users building web APIs cannot safely call blocking pipeline code from an event loop.

**Dependencies:** EXE-003, FND-001

**Expected outcome:**
`result = await run_pipeline_async(executor, audio_resource)` runs the pipeline in a thread without blocking the event loop.

**Tests required:**
- Test that `run_pipeline_async()` returns the correct result.
- Test that it does not block the event loop.
- Test that exceptions from the executor propagate correctly.

**Verification required:**
No blocking detected during async pipeline execution in tests.

**Definition of Done:**
`async_utils.py` implemented. `docs/concurrency.md` written. Tests pass.

---

### REL-005 — Implement Comprehensive Test Infrastructure

**Area:** Testability
**Phase:** 5
**Priority:** Critical

**Goal:**
Create a comprehensive `lingualdub/testing/` module that provides all utilities framework users and contributors need to test against the framework effectively.

**What should be built/improved:**
- `testing/builders.py` — `ResourceBuilder`, `ResultBuilder`, `SegmentBuilder`, `LanguageBuilder`.
- `testing/fakes.py` — `FakeASR`, `FakeTTS`, `FakeTranslation`, `FakeAlignment`, `FakeEvaluator`.
- `testing/matchers.py` — `assert_result_complete(result)`, `assert_result_failed(result)`, `assert_result_has_segment(result, text)`.
- `testing/pipeline.py` — `PipelineTestHarness`.
- `testing/clock.py` — `FakeClock`.
- Document all utilities in `docs/testing.md`.

**Why it matters:**
Without official test utilities, every team invents their own builders and fakes, leading to inconsistency and duplication.

**Dependencies:** EXE-007, LCY-004, FND-006

**Expected outcome:**
A new contributor can write a meaningful integration test in under 20 lines using `PipelineTestHarness` and `ResultBuilder`.

**Tests required:**
- Test every builder produces a valid instance with defaults.
- Test every fake satisfies the corresponding protocol.
- Test every matcher passes and fails correctly.
- Test `PipelineTestHarness` runs a pipeline end-to-end.

**Verification required:**
The test utilities themselves must have 100% branch coverage.

**Definition of Done:**
`testing/` module exists with all listed utilities. All utilities tested. 100% branch coverage on test utilities. `docs/testing.md` written.

---

### REL-006 — Implement Regression Test Suite for Public API

**Area:** Testability / API Stability
**Phase:** 5
**Priority:** High

**Goal:**
Create a regression test suite that specifically tests the public API surface, ensuring no public behaviour changes without an explicit, documented decision.

**What should be built/improved:**
- `tests/regression/` directory.
- `test_public_api_surface.py` — asserts that `lingualdub.__all__` contains exactly the documented public symbols.
- `test_public_api_contracts.py` — for each major public class, tests that documented constructor arguments, default values, and method signatures match the implementation.
- Snapshots stored in `tests/regression/snapshots/`.

**Why it matters:**
Without regression tests on the public API, a refactor can accidentally rename a parameter or remove a method with no test catching it.

**Dependencies:** FND-001, REL-005

**Expected outcome:**
Renaming `Resource.language` to `Resource.lang_code` causes `test_public_api_contracts.py` to fail immediately.

**Tests required:**
The regression tests themselves are the deliverable.

**Verification required:**
Intentionally renaming one public symbol confirms the regression test catches it.

**Definition of Done:**
`tests/regression/` exists. Public API surface and contract tests present. Snapshot files committed. Intentional breakage test confirmed.

---

## Phase 6 — Production Quality

> Add observability, security hardening, and configuration completeness.

---

### PRO-001 — Implement Structured Logging

**Area:** Observability
**Phase:** 6
**Priority:** Critical

**Goal:**
Replace all ad-hoc logging calls with structured, machine-parseable log events carrying consistent contextual fields.

**What should be built/improved:**
- Adopt `structlog` (or compatible shim) for structured logging.
- Every log record includes: `timestamp`, `level`, `event`, `run_id`, `pipeline_name`, `stage_name`, `language`, `duration_ms`.
- Sensitive fields must never be logged — add `[REDACTED]` markers.
- Log lifecycle events: startup, shutdown, each pipeline execution, each stage entry/exit, errors.
- `FrameworkConfig` controls: log level, log format (`json` / `text`), sensitive field redaction toggle.

**Why it matters:**
Plain-text logs are difficult to parse in production. Structured logging enables log aggregation systems to query events by field.

**Dependencies:** FND-003, EXT-006

**Expected outcome:**
In `json` format mode, every log line is valid JSON with all required fields. Sensitive fields never appear in logs.

**Tests required:**
- Test that every lifecycle event produces a log record.
- Test that log records include required fields.
- Test that sensitive fields are redacted.
- Test that `log_level` config correctly filters records.

**Verification required:**
Log output parsed as JSON — no parse errors. Grep for sensitive values confirms absence.

**Definition of Done:**
Structured logging applied throughout framework. Schema documented. Sensitive field redaction implemented. Config-controlled level and format. Tests pass.

---

### PRO-002 — Implement Execution Metrics

**Area:** Observability
**Phase:** 6
**Priority:** High

**Goal:**
Expose framework execution metrics via a pluggable metrics interface that can integrate with Prometheus, StatsD, or custom backends.

**What should be built/improved:**
- `lingualdub/observability/metrics.py` with `MetricsBackend` protocol: `counter()`, `histogram()`, `gauge()`.
- `NoOpMetricsBackend` — default, zero overhead.
- `PrometheusMetricsBackend` — optional, requires `prometheus_client`.
- Framework instruments: pipeline execution count, stage latency histogram, error count by type, pool utilization gauge.
- Backend configurable via `FrameworkConfig.metrics_backend`.

**Why it matters:**
Without metrics, production operators cannot detect degradation or alert on error spikes.

**Dependencies:** PRO-001, FND-003, REL-002

**Expected outcome:**
After enabling `PrometheusMetricsBackend`, metrics endpoint exposes `lingualdub_pipeline_executions_total` and stage duration histograms.

**Tests required:**
- Test that `NoOpMetricsBackend` accepts all calls without error.
- Test that framework instruments emit correct metric names and labels.
- Test `PrometheusMetricsBackend` produces parseable Prometheus output.

**Verification required:**
Metrics emitted during a test pipeline execution match expected names and have positive values.

**Definition of Done:**
`observability/metrics.py` with protocol, NoOp, and Prometheus backends. Framework instrumented. Tests pass.

---

### PRO-003 — Implement Distributed Tracing Support

**Area:** Observability
**Phase:** 6
**Priority:** Medium

**Goal:**
Add OpenTelemetry trace instrumentation to pipeline executions so distributed systems can correlate LingualDub spans with upstream and downstream services.

**What should be built/improved:**
- `lingualdub/observability/tracing.py` with `TracingBackend` protocol.
- `OpenTelemetryTracingBackend` — optional, requires `opentelemetry-api`.
- `NoOpTracingBackend` — default.
- Framework creates a span per pipeline execution and a child span per stage.
- Trace/span IDs propagated into `Result.provenance`.

**Why it matters:**
For speech AI systems in microservice architectures, distributed tracing is required to understand latency across service boundaries.

**Dependencies:** PRO-001, EXT-005

**Expected outcome:**
A pipeline execution with OpenTelemetry enabled produces parent and child spans observable in Jaeger or Zipkin.

**Tests required:**
- Test that `NoOpTracingBackend` accepts all calls without error.
- Test that trace IDs appear in `Result.provenance`.
- Test that each stage creates a child span (verified with a capture backend).

**Verification required:**
Span hierarchy matches pipeline stage hierarchy in a test capture backend.

**Definition of Done:**
`observability/tracing.py` implemented. NoOp and OpenTelemetry backends. Spans created per execution and stage. Tests pass.

---

### PRO-004 — Implement Security Input Validation Hardening

**Area:** Security
**Phase:** 6
**Priority:** Critical

**Goal:**
Harden all framework entry points against malformed, oversized, or malicious inputs, with explicit trust boundaries, size limits, and path traversal prevention.

**What should be built/improved:**
- Define maximum allowed sizes for all user-provided inputs: segment text length, resource path length, metadata dict depth.
- Add path traversal prevention to all file path inputs: reject paths containing `..`.
- Add `validate_resource_path(path)` to `validation.py`.
- All config YAML/JSON loading must use safe loaders only (`yaml.safe_load`, never `yaml.load` without `Loader`).
- Add `SecurityConfig` to `FrameworkConfig`: `max_segment_length`, `max_metadata_depth`, `path_traversal_check_enabled`.
- Document trust boundaries in `docs/security.md`.

**Why it matters:**
Path traversal attacks via user-supplied resource paths could allow reading arbitrary files. Safe YAML loading prevents arbitrary code execution.

**Dependencies:** FND-003, FND-005

**Expected outcome:**
Passing `resource_path="../../../etc/passwd"` raises `ResourceError("Path traversal detected")`. A YAML config containing Python tags raises a parse error.

**Tests required:**
- Test path traversal detection for `..`, `~`, and absolute paths outside workspace.
- Test that safe YAML loader rejects Python object tags.
- Test that oversized segment text raises validation error.

**Verification required:**
A security review confirms no `yaml.load(...)` without `Loader=yaml.SafeLoader` in codebase.

**Definition of Done:**
All file path inputs validated. Safe YAML loading enforced. `docs/security.md` written. Tests pass.

---

### PRO-005 — Implement Secure Logging and Secret Protection

**Area:** Security / Observability
**Phase:** 6
**Priority:** High

**Goal:**
Ensure that secrets, voice data paths, personal identifiers, and consent records never appear in logs, metrics labels, or error messages.

**What should be built/improved:**
- `lingualdub/observability/redaction.py` with `RedactionFilter`:
  - Scans log record fields against a configurable list of sensitive field names.
  - Replaces values with `[REDACTED]`.
  - Applied automatically to all log handlers.
- Sensitive field names: `api_key`, `access_token`, `speaker_reference`, `voice_path`, `consent_record`, `email`.
- `FrameworkConfig.sensitive_fields: list[str]` — user can extend the list.

**Why it matters:**
Voice data paths and API keys appearing in logs are a privacy and security violation.

**Dependencies:** PRO-001, FND-003

**Expected outcome:**
A log record that would have contained `speaker_reference=/data/voice/alice.wav` instead contains `speaker_reference=[REDACTED]`.

**Tests required:**
- Test that sensitive field names are redacted from log records.
- Test that user-extended `sensitive_fields` are also redacted.
- Test that non-sensitive fields are not redacted.

**Verification required:**
Log capture in tests confirms zero occurrences of sensitive data values.

**Definition of Done:**
`RedactionFilter` implemented and auto-applied. Sensitive fields configurable. Tests pass.

---

### PRO-006 — Implement Dependency Security Scanning

**Area:** Security
**Phase:** 6
**Priority:** Medium

**Goal:**
Add automated dependency vulnerability scanning to the CI pipeline, with a policy for handling critical vulnerabilities.

**What should be built/improved:**
- Add `pip-audit` to the `[dev]` extra in `pyproject.toml`.
- Add `.github/workflows/security.yml`:
  - Runs on every push and pull request.
  - Runs `pip-audit --strict` against installed dependencies.
  - Fails the build on any critical or high severity CVE.
- Document the vulnerability response policy in `docs/security.md`.

**Why it matters:**
Machine learning frameworks depend on many third-party packages. Without automated scanning, known vulnerabilities go undetected until exploited.

**Dependencies:** PRO-004

**Expected outcome:**
A push that introduces a dependency with a known critical CVE fails the `security.yml` workflow.

**Tests required:**
The workflow is the test — verify it fails when a known-vulnerable package is temporarily added.

**Verification required:**
CI confirms `security.yml` workflow runs and passes on the main branch.

**Definition of Done:**
`security.yml` workflow exists. `pip-audit` in dev dependencies. Policy documented. Workflow passes on main branch.

---

## Phase 7 — Performance & Evolution

> Establish API compatibility guarantees, semantic versioning discipline, and performance measurement.

---

### PEV-001 — Define API Compatibility Policy

**Area:** API Stability & Evolution
**Phase:** 7
**Priority:** Critical

**Goal:**
Establish a documented, enforced policy for how the framework evolves its public API, what constitutes a breaking change, and how the versioning scheme reflects stability.

**What should be built/improved:**
- `COMPATIBILITY.md` documenting:
  - What is considered a breaking change: removed public symbol, changed constructor parameter, changed return type, changed exception type.
  - Semantic versioning rules: major = breaking, minor = additive, patch = bugfix.
  - Deprecation period: minimum one minor release before removal.
  - Internal (`_`-prefixed) symbols carry no compatibility guarantee.
- `CHANGELOG.md` maintained with every release including: Added, Changed, Deprecated, Removed, Fixed, Security sections.

**Why it matters:**
Without a published compatibility policy, users cannot safely upgrade.

**Dependencies:** FND-001, REL-006

**Expected outcome:**
`COMPATIBILITY.md` and `CHANGELOG.md` exist.

**Tests required:**
Process deliverable — the regression test suite (REL-006) serves as the technical enforcement.

**Verification required:**
Review confirms `COMPATIBILITY.md` covers breaking change definition, versioning scheme, and deprecation period.

**Definition of Done:**
`COMPATIBILITY.md` and `CHANGELOG.md` exist. Policy reviewed. Regression test suite is the technical enforcement.

---

### PEV-002 — Implement Deprecation Mechanism

**Area:** API Stability & Evolution
**Phase:** 7
**Priority:** High

**Goal:**
Implement a formal deprecation mechanism that warns users with a `DeprecationWarning` when they use deprecated API symbols, pointing them to the replacement.

**What should be built/improved:**
- `lingualdub/utils/deprecation.py`:
  - `deprecated(reason: str, replacement: str | None = None, since: str = "")` — decorator for functions, classes, and methods.
  - Emits `DeprecationWarning` with standardized message: `"[DEPRECATED since v{since}] {symbol} is deprecated. Use {replacement} instead."`
  - Warnings are suppressable via standard Python `warnings.filterwarnings`.
- Apply `@deprecated` to any symbols scheduled for removal in the next major release.

**Why it matters:**
Without formal deprecation warnings, users have no indication that an API is being removed until it's gone.

**Dependencies:** PEV-001, FND-001

**Expected outcome:**
Calling a deprecated function emits a `DeprecationWarning` with the message including the replacement symbol name.

**Tests required:**
- Test that calling a `@deprecated` function emits `DeprecationWarning`.
- Test that the warning message includes `since`, `symbol`, and `replacement`.
- Test that `warnings.filterwarnings("ignore")` suppresses the warning.

**Verification required:**
Every symbol marked for removal in `CHANGELOG.md` has `@deprecated` applied.

**Definition of Done:**
`utils/deprecation.py` implemented. `@deprecated` decorator works. Tests pass.

---

### PEV-003 — Establish Performance Benchmarks

**Area:** Performance
**Phase:** 7
**Priority:** High

**Goal:**
Create a benchmark suite that measures key framework operations and detects performance regressions.

**What should be built/improved:**
- `benchmarks/` directory with `pytest-benchmark` benchmark scripts.
- Benchmarks for:
  - `Registry.resolve()` at 100, 1000, 10000 registered components.
  - `Pipeline` assembly from 3, 5, 10 stages.
  - `MiddlewareChain.execute()` with 0, 3, 10 middleware.
  - `PipelineExecutor.run()` with dummy components (measures framework overhead only).
  - `DependencyContainer.resolve()` with 10-level deep dependency chain.
- Baseline results committed to `benchmarks/baselines/`.
- CI runs benchmarks on main branch only (not on every PR) to avoid noise.

**Why it matters:**
Without benchmarks, performance regressions are discovered by users in production.

**Dependencies:** EXT-005, EXE-003, REL-005

**Expected outcome:**
`pytest benchmarks/` produces a table showing mean/std for each benchmark.

**Tests required:**
- Each benchmark function must run without errors.
- Baseline files must be committed and readable.

**Verification required:**
Deliberately introducing an O(n²) loop causes the benchmark to fail comparison against baseline.

**Definition of Done:**
`benchmarks/` exists. At least 5 benchmark categories covered. Baselines committed. CI job configured. Tests pass.

---

### PEV-004 — Identify and Eliminate Startup Overhead

**Area:** Performance
**Phase:** 7
**Priority:** Medium

**Goal:**
Profile framework startup time and reduce cold startup to under 200ms for an empty framework (no plugins, no models loaded).

**What should be built/improved:**
- Use `cProfile` or `pyinstrument` to profile `import lingualdub; FrameworkLifecycle().startup()`.
- Identify: heavy imports at module level, redundant initialization work, unnecessary validation during startup.
- Defer heavy imports (torch, transformers) to first use (lazy import pattern).
- Add a startup timing log entry showing component initialization times.

**Why it matters:**
Slow startup is unacceptable for CLI tools and serverless deployments.

**Dependencies:** LCY-001, PEV-003

**Expected outcome:**
Cold framework startup (no plugins) completes in under 200ms. `import lingualdub` with no model components does not import torch.

**Tests required:**
- Test that `import lingualdub` does not import `torch` (use `sys.modules` inspection).
- Benchmark test: startup time is within 200ms.

**Verification required:**
Profile confirms no `torch` import at framework load time. Startup benchmark passes.

**Definition of Done:**
Startup under 200ms. `torch` not imported unless model component used. Startup timing in logs. Tests pass.

---

### PEV-005 — Implement Caching for Repeated Work

**Area:** Performance
**Phase:** 7
**Priority:** Medium

**Goal:**
Identify and cache the results of repeated expensive computations in the framework using functionally correct caching strategies.

**What should be built/improved:**
- Cache `Pipeline._validate_stage_compatibility()` results keyed on stage name/version tuples.
- Cache `MiddlewareChain.build(pipeline_name)` result — invalidated on middleware registration/removal.
- Cache `Registry.resolve()` for `SINGLETON` lifetime lookups after first resolution.
- All caches must be invalidated on registry or middleware changes.
- Add `FrameworkConfig.cache_enabled: bool = True` to allow disabling caches in tests.

**Why it matters:**
Re-computing compatibility checks and rebuilding middleware chains for every pipeline execution adds unnecessary latency.

**Dependencies:** PEV-003, EXT-007, FND-003

**Expected outcome:**
Second call to `MiddlewareChain.build("dubbing")` is at least 10x faster than first call.

**Tests required:**
- Test that cached results are consistent with uncached results.
- Test that cache is invalidated when middleware is registered or removed.
- Test that `cache_enabled=False` disables caching (results still correct).

**Verification required:**
Benchmark confirms at least 10x speedup for cached calls vs first call.

**Definition of Done:**
Caching implemented for three hot paths. Invalidation correct. Config-controlled. Benchmark speedup confirmed. Tests pass.

---

## Summary Table

| ID | Title | Phase | Priority |
|----|-------|-------|----------|
| FND-001 | Define Public/Private API Boundaries | 1 | Critical |
| FND-002 | Establish Framework Exception Hierarchy | 1 | Critical |
| FND-003 | Establish Framework Configuration System | 1 | Critical |
| FND-004 | Define Component Contract Protocol | 1 | High |
| FND-005 | Establish Input Validation Utilities | 1 | High |
| FND-006 | Establish Stable Result and Segment Contracts | 1 | High |
| FND-007 | Centralized Common Types and Aliases | 1 | High |
| FND-008 | Robust Serialization and Deserialization Contracts | 1 | High |
| FND-009 | Manifest Schema Enforcement & Scanner Validation | 1 | High |
| LCY-001 | Define Framework Lifecycle Model | 2 | Critical |
| LCY-002 | Implement Application Startup Hooks | 2 | High |
| LCY-003 | Implement Shutdown Hooks and Deterministic Teardown | 2 | High |
| LCY-004 | Implement Lifecycle Testing Utilities | 2 | Medium |
| EXE-001 | Define Dependency Contract | 3 | Critical |
| EXE-002 | Implement Dependency Registration | 3 | Critical |
| EXE-003 | Implement Dependency Resolution | 3 | Critical |
| EXE-004 | Implement Scoped Dependencies | 3 | High |
| EXE-005 | Implement Dependency Override for Testing | 3 | High |
| EXE-006 | Detect Circular Dependencies | 3 | High |
| EXE-007 | Add DI Test Suite and Testing Utilities | 3 | Medium |
| EXT-001 | Define Extension Point Contracts | 4 | Critical |
| EXT-002 | Implement Plugin Registration API | 4 | Critical |
| EXT-003 | Implement Plugin Lifecycle Hooks | 4 | High |
| EXT-004 | Implement Plugin Isolation and Failure Handling | 4 | High |
| EXT-005 | Implement Middleware Pipeline | 4 | High |
| EXT-006 | Implement Built-in Middleware | 4 | High |
| EXT-007 | Implement Middleware Registration and Ordering API | 4 | Medium |
| REL-001 | Define Resource Ownership Model | 5 | Critical |
| REL-002 | Implement Resource Pool | 5 | Medium |
| REL-003 | Implement Concurrency Safety for Registry | 5 | High |
| REL-004 | Implement Async/Sync Boundary Utilities | 5 | High |
| REL-005 | Implement Comprehensive Test Infrastructure | 5 | Critical |
| REL-006 | Implement Regression Test Suite for Public API | 5 | High |
| PRO-001 | Implement Structured Logging | 6 | Critical |
| PRO-002 | Implement Execution Metrics | 6 | High |
| PRO-003 | Implement Distributed Tracing Support | 6 | Medium |
| PRO-004 | Implement Security Input Validation Hardening | 6 | Critical |
| PRO-005 | Implement Secure Logging and Secret Protection | 6 | High |
| PRO-006 | Implement Dependency Security Scanning | 6 | Medium |
| PEV-001 | Define API Compatibility Policy | 7 | Critical |
| PEV-002 | Implement Deprecation Mechanism | 7 | High |
| PEV-003 | Establish Performance Benchmarks | 7 | High |
| PEV-004 | Identify and Eliminate Startup Overhead | 7 | Medium |
| PEV-005 | Implement Caching for Repeated Work | 7 | Medium |

---

## Dependency Graph

```text
FND-001 --> FND-002 --> FND-003 --> LCY-001 --> LCY-002 --> LCY-003 --> LCY-004
         |          |
         v          v
      FND-004     FND-005 --> FND-006 --> FND-008
         |          |
         v          v
      FND-007    FND-009
         |
         v
      EXE-001 --> EXE-002 --> EXE-003 --> EXE-004
                                      --> EXE-005
                                      --> EXE-006
                                      --> EXE-007
         |
         v
      EXT-001 --> EXT-002 --> EXT-003 --> EXT-004
                          --> EXT-005 --> EXT-006 --> EXT-007
                                     |
                                     v
                                 REL-001 --> REL-002
                                 REL-003
                                 REL-004
                                 REL-005 --> REL-006
                                     |
                                     v
                                 PRO-001 --> PRO-002 --> PRO-003
                                 PRO-004 --> PRO-005
                                 PRO-006
                                     |
                                     v
                                 PEV-001 --> PEV-002
                                 PEV-003 --> PEV-004 --> PEV-005
```

---

*Last updated: September 2026 — v0.1.0-dev*
