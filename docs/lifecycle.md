# Lifecycle

Framework lifecycle is a deterministic state machine controlling startup, execution, and teardown.

## States

```
UNINITIALIZED → CONFIGURING → CONFIGURED → INITIALIZING → READY → RUNNING → SHUTTING_DOWN → STOPPED
```

| State | Responsibility |
|---|---|
| `UNINITIALIZED` | Fresh instance, no config loaded |
| `CONFIGURING` | `FrameworkConfig` validation (`load_config()`), env var ingestion |
| `CONFIGURED` | Config frozen (`validate()`), registry not yet populated |
| `INITIALIZING` | Component registration, `ManifestScanner` scan, resource acquisition, `register_startup_hook` ordering |
| `READY` | Pipeline assembly allowed (`Pipeline` compatibility checks) |
| `RUNNING` | `PipelineExecutor.run()` allowed; also returns to `READY` after run |
| `SHUTTING_DOWN` | Teardown in progress (`shutdown()` → `run_shutdown_hooks` reverse startup order) |
| `STOPPED` | Terminal; `atexit` handler ensures this is reached |

Illegal transitions raise `LifecycleError` (`LIFECYCLE_001`) with `history` context. `ensure(*allowed)` guards operations.

## Startup Hooks (LCY-002)

```python
from lingualdub.lifecycle import FrameworkLifecycle, startup_hook

lc = FrameworkLifecycle()

@lc.startup_hook("init_registry", depends_on=["init_config"])
def init_registry(): ...

lc.register_startup_hook("init_config", lambda: ..., depends_on=None)
lc.run_startup_hooks()  # topological order (Kahn), deterministic tie-break by registration order
```

* `depends_on` declares ordering; missing dep → `LIFECYCLE_004`, cycle → `LIFECYCLE_005` with `A → B → A` chain.
* Failure wraps in `InitializationError(component=name)`, stops sequence.

Module-level `@startup_hook(name, depends_on)` attaches `_lingualdub_startup_hook` metadata for later registration.

## Shutdown Hooks (LCY-003)

```python
@lc.shutdown_hook("cleanup_tmp")
def cleanup(): ...

lc.shutdown()  # SHUTTING_DOWN → STOPPED, idempotent, handles partial init
```

* Runs `run_shutdown_hooks()` in **reverse startup execution order** (topological execution, not registration), best-effort (`WARNING` log, continue).
* `atexit` handler `_handle_atexit` calls `shutdown()` on interpreter exit; respects `sys.is_finalizing()`.
* Multiple `FrameworkLifecycle` instances each register `atexit`; internal execution order tracking avoids duplicate teardown.

## Testing Utilities (LCY-004)

See `docs/testing.md` — `TestFramework`, `LifecycleCapture`, `assert_lifecycle_sequence`.
