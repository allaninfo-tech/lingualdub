# Lifecycle

The framework lifecycle is a deterministic state machine that orders startup, execution, and teardown.

## States

```
UNINITIALIZED → CONFIGURING → CONFIGURED → INITIALIZING → READY → RUNNING → SHUTTING_DOWN → STOPPED
```

| State | What occurs | Responsible |
|---|---|---|
| `CONFIGURING` | `FrameworkConfig.validate()` | config validation |
| `CONFIGURED` | config frozen | — |
| `INITIALIZING` | `Registry` population, `ManifestScanner`, `ResourceManager` acquisition | component registration |
| `READY` | pipeline assembly allowed (`Pipeline` creation) | registry resolution |
| `RUNNING` | `PipelineExecutor.run()` allowed | execution |
| `SHUTTING_DOWN` | teardown hooks, resource release | cleanup |
| `STOPPED` | no further work | — |

`READY ↔ RUNNING` may bounce (multiple runs without re-init).

## Failure & Cleanup

* Illegal transition → `LifecycleError(code=LIFECYCLE_001)` with `from/to/history`
* Operation in wrong state → `LifecycleError(code=LIFECYCLE_002)` with `allowed`
* Failures at `INITIALIZING` prevent `READY`; `SHUTTING_DOWN` is best-effort (remaining hooks still run, see LCY-003)

## Usage

```python
from lingualdub.lifecycle import FrameworkLifecycle, LifecycleState

lc = FrameworkLifecycle()
lc.transition(LifecycleState.CONFIGURING)
# ... validate config
lc.transition(LifecycleState.CONFIGURED)
lc.ensure(LifecycleState.CONFIGURED)  # guard
```

See `lingualdub/lifecycle.py` for `FrameworkLifecycle` implementation.
