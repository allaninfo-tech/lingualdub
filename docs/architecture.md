# Architecture

LingualDub is organised around five interoperable core objects and a registry
that connects them without requiring changes to framework internals when new
languages, models, or methods are introduced.

## Layer Overview

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
```

## Core Objects

| Object | Module | Responsibility |
|---|---|---|
| `Language` | `lingualdub.core.language` | Language metadata and resource profile |
| `Resource` | `lingualdub.core.resource` | Data asset with provenance and versioning |
| `Component` | `lingualdub.core.component` | Replaceable processing unit with contracts |
| `Segment` | `lingualdub.core.segment` | Atomic unit of speech/text data |
| `Result` | `lingualdub.core.result` | Structured output with status and provenance |
| `Pipeline` | `lingualdub.core.pipeline` | Composed workflow with failure handling |
| `Registry` | `lingualdub.registry` | Discovery and resolution of all registered objects |

## Separation of Concerns

| Layer | Package | What it owns |
|---|---|---|
| Abstractions | `lingualdub/core/` | Contracts and data structures only |
| Execution | `lingualdub/pipeline/` | Running a pipeline and managing stage failures |
| Extension | `lingualdub/components/` | Component base classes per task category |
| Registration | `lingualdub/languages/` | First-party language and resource profiles |
| Utilities | `lingualdub/utils/` | Provenance, artifact paths, shared helpers |
| Research | `research/` | Open research modules; not part of the core runtime |
| Docs | `docs/` | Architecture, guides, and per-module documentation |
| Tests | `tests/` | Test suite mirroring the package structure |
| Configs | `configs/` | Pipeline configuration templates |

## Capability Checking

Components declare `requires` and `provides` capability tokens. The `Pipeline`
validates compatibility across all stages at assembly time — before execution —
so mismatched stage connections fail immediately with a clear error rather than
silently at runtime.

## Failure Handling

Each stage can be configured with one of three failure modes:

- **ABORT** — stop the pipeline and surface the error.
- **SKIP** — omit the stage's contribution and mark `Result.status` as `PARTIAL`.
- **DEGRADE** — invoke the component's `degrade()` path if defined and mark as `DEGRADED`.

`Result.status` and `Result.warnings` make the quality of every output explicit.

## Registry and Extensions

The Registry holds all registered Language, Resource, and Component objects.
Extensions register through a manifest file; the Registry scans installed
manifests at startup. Every entry is versioned so provenance is traceable.

## Development Lifecycle

```
Profile language + resources → Select / register components → Compose pipeline
    → Run baseline → Adapt / generate data → Evaluate
    → Save artifacts → Register results → Iterate
```

Saved artifacts re-enter the loop as registered resources and components —
making the loop a real mechanism rather than a return to square one.
