# M10 Research — Lifecycle & Initialization (LCY-001…LCY-004)

> **Goal:** Provide empirical research for the next milestone after M9 v0.1.0.  
> **Scope:** IMPROVEMENT.md Phase 2 (LCY). M0–M9 are ✅ closed (see `docs/milestones.md:223`).  
> **Principle:** Deep codebase analysis before implementation; every gap discovered becomes a task.

---

## 1. Current Empirical State

### What exists
* `FrameworkConfig` (`lingualdub/config.py:196`) validated + frozen, no state machine
* `Registry` (`registry/registry.py:64`) ad-hoc instantiation in `cli.get_default_registry():35` with `HIGHEST_VERSION` + hardcoded `register()` + `ManifestScanner.scan()` — no ordered stages
* `PipelineExecutor` (`pipeline/executor.py:37`) runs linearly, no lifecycle guard (`state == RUNNING` check)
* Exceptions `LifecycleError / InitializationError / ShutdownError` (`exceptions.py:168`) defined but never raised
* No `lingualdub/lifecycle.py`, no `docs/lifecycle.md`, no `FrameworkLifecycle`, no hooks, no `atexit`

### What is missing (gaps discovered via grep)
* `grep -r "Lifecycle" lingualdub --include="*.py"` → only definitions in `exceptions.py` + re-export in `__init__.py` — zero usage
* `grep -r "atexit" .` → zero
* `grep -r "shutdown\|startup_hook" .` → zero
* `Config` reads env vars at `load_config():352` but no lifecycle stage `CONFIGURING → CONFIGURED`
* `ResourceManager` cache dir resolved via `config._get_cache_dir_env()` but no deterministic teardown
* Tests are global-state shared: `tests/conftest.py` uses fixtures but no isolated `TestFramework` context

---

## 2. Why LCY is the correct next milestone

**Dependency order (`IMPROVEMENT.md:17`):**
```
Phase1 FND ✅ → Phase2 LCY → Phase3 EXE (DI) → Phase4 EXT (Plugins/Middleware)
```
* FND is done (PUBLIC_API, exceptions, config, protocols, validation, Result/Segment, types, serialization, manifest)
* EXE/EXT require lifecycle to order `CONFIGURING → INITIALIZING → READY → RUNNING → SHUTTING_DOWN`
* REL/PRO/PEV depend on lifecycle for ownership, pooling, metrics
* Post-M9, the framework is usable but not production-lifecycle safe (no startup ordering, no deterministic teardown, no test isolation)

**Risk if skipped:**
* Race conditions on concurrent `Registry` + `ResourceManager` init (see `resource_manager.py:68` per-instance lock, not lifecycle-scoped)
* Pipeline execution while `INITIALIZING` silently succeeds instead of `LifecycleError`
* Resource leaks — no `close()` contract tied to scope exit

---

## 3. Insights that fit into this milestone (beyond spec)

Discovered via deep analysis, to be added as tasks:

* **Config → Lifecycle coupling:** `FrameworkConfig.validate()` freezes but does not transition lifecycle; LCY-001 should own it
* **Registry as lifecycle-owned singleton:** Current `get_default_registry()` duplicates registrations + manifest scan without lifecycle guard; should be moved into `FrameworkLifecycle` startup hook
* **Pre-existing `ResourceKind.VIDEO` and consent:** Voice resources already enforce `consent_basis`; lifecycle should ensure `consent_enforcement` config is read before any voice component registers
* **Existing `PipelineExecutor` provenance bug already fixed:** Use as pattern for lifecycle-tagged provenance (`lifecycle_state` in `Result.provenance`)
* **Test isolation gap:** `tests/stress/test_stress.py:311` + `tests/integration/*` share global registry; `LCY-004` will provide `TestFramework` isolation

---

## 4. Proposed M10 Breakdown — 4 Manageable Iterations

> **Discipline:** One iteration at a time — `Understand → Implement → Test → Verify → Commit → Push → STOP`

### Iteration M10.1 — LCY-001 Lifecycle Model

* **Build:** `lingualdub/lifecycle.py` with `LifecycleState` enum `UNINITIALIZED → CONFIGURING → CONFIGURED → INITIALIZING → READY → RUNNING → SHUTTING_DOWN → STOPPED`, `FrameworkLifecycle` class with `.state`, validated transitions, `LifecycleError` on illegal move
* **Docs:** `docs/lifecycle.md` stages, responsibilities, failure/cleanup per stage
* **Tests:** `tests/lifecycle/test_lifecycle_state.py` — legal/illegal transitions, correct state query
* **Verification:** `python -c "from lingualdub.lifecycle import FrameworkLifecycle"` + `mypy lingualdub/lifecycle.py` + `pytest tests/lifecycle`
* **Git:** commit `feat(lifecycle): define FrameworkLifecycle state machine` after tests pass

### Iteration M10.2 — LCY-002 Startup Hooks

* **Build:** `register_startup_hook(name, hook, depends_on)`, topological sort, `@startup_hook` decorator, `InitializationError` wrapping, cycle detection → `LifecycleError`
* **Integration:** Move `FrameworkConfig.load_config()` + `Registry` creation + `ManifestScanner` into hooks
* **Tests:** `tests/lifecycle/test_startup_hooks.py` — order (no deps, linear, diamond), failing hook stops + `InitializationError`, circular → `LifecycleError`
* **Verification:** `pytest` + manual `FrameworkLifecycle().startup()` ordering test
* **Git:** commit `feat(lifecycle): startup hook registry with dependency ordering`

### Iteration M10.3 — LCY-003 Shutdown Hooks & Teardown

* **Build:** `register_shutdown_hook(name, hook)`, reverse-order execution, best-effort (log + continue), `shutdown()` → `SHUTTING_DOWN → STOPPED`, `atexit` registration, partial-init cleanup (`shutdown()` before `startup()` completes)
* **Tests:** `tests/lifecycle/test_shutdown_hooks.py` — reverse order, failing hook logs not abort, `shutdown()` before `startup()` safe, `atexit` present
* **Verification:** `pytest` + manual `atexit` check
* **Git:** commit `feat(lifecycle): deterministic shutdown with atexit`

### Iteration M10.4 — LCY-004 Testing Utilities

* **Build:** `lingualdub/testing/lifecycle.py` with `TestFramework` context manager (isolated instance per test), `LifecycleCapture`, `assert_lifecycle_sequence`
* **Docs:** `docs/testing.md` update
* **Tests:** `tests/lifecycle/test_testing_utils.py` — isolated instances, capture records, parallel contexts not sharing state, existing tests migrate to use `TestFramework` optionally
* **Verification:** `pytest -n auto` parallel isolation, `ruff` + `mypy`
* **Git:** commit `feat(lifecycle): testing utilities for deterministic lifecycle tests`

---

## 5. Success Criteria (M10 Done When)

* `docs/lifecycle.md` matches implementation
* `FrameworkLifecycle` state machine enforces legal transitions, raises `LifecycleError` on illegal
* Startup hooks respect dependencies, cycle → `LifecycleError`, failure → `InitializationError`
* Shutdown hooks run reverse order, failing hook logged not fatal, `atexit` registered, partial teardown safe
* `TestFramework` provides isolated instance, `LifecycleCapture` records, parallel tests not interfering
* All `LCY-001…004` checklist items in `IMPROVEMENT.md` checked
* `pytest` ≥73% coverage, `ruff check` 0, `mypy lingualdub/lifecycle.py` 0, CI green

---

## 6. Out of Scope (for M10)

* DI container (EXE-001…007) — Phase 3, depends on LCY
* Plugin/Middleware (EXT-001…007) — Phase 4
* Resource ownership/pool (REL-001…) — Phase 5
* Metrics/tracing (PRO) — Phase 6

---

*Research completed: 2026-09-12. Next: begin M10.1 implementation after user approval.*
