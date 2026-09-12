# Testing Guide — Lifecycle Utilities (LCY-004)

This document describes how to test against the LingualDub lifecycle using the
official testing utilities in `lingualdub.testing.lifecycle`.

## Overview

Lifecycle tests are fragile when they share global state. The testing utilities
provide isolated, deterministic helpers so each test gets a fresh framework
instance and can assert on state transitions without interference.

- `TestFramework` — isolated `FrameworkLifecycle` per test (context manager, auto-teardown)
- `LifecycleCapture` — records all state transitions in order
- `assert_lifecycle_sequence` — assertion helper

All three are re-exported from `lingualdub.testing`:

```python
from lingualdub.testing import TestFramework, LifecycleCapture, assert_lifecycle_sequence
from lingualdub.testing.lifecycle import TestFramework  # also works
```

## TestFramework

Context manager that creates a fresh `FrameworkLifecycle` for each test and
tears it down (`shutdown() → STOPPED`) on exit, even if the test raises.

```python
from lingualdub.testing.lifecycle import TestFramework, assert_lifecycle_sequence
from lingualdub.lifecycle import LifecycleState

def test_startup_flow():
    with TestFramework() as fw:
        # fw.lifecycle is isolated — no sharing with other tests
        # fw.capture is a LifecycleCapture attached to fw.lifecycle
        assert fw.lifecycle.state == LifecycleState.UNINITIALIZED

        fw.lifecycle.transition(LifecycleState.CONFIGURING)
        fw.lifecycle.transition(LifecycleState.CONFIGURED)
        fw.lifecycle.transition(LifecycleState.INITIALIZING)
        fw.lifecycle.transition(LifecycleState.READY)

        assert fw.state == LifecycleState.READY  # shortcut to lifecycle.state
        assert_lifecycle_sequence(
            fw.capture,
            [
                LifecycleState.UNINITIALIZED,
                LifecycleState.CONFIGURING,
                LifecycleState.CONFIGURED,
                LifecycleState.INITIALIZING,
                LifecycleState.READY,
            ],
        )
    # After exit, fw.lifecycle is STOPPED (deterministic teardown)
    assert fw.lifecycle.state == LifecycleState.STOPPED
```

### Isolation

Two concurrent `TestFramework` contexts do not share state (hooks, history, capture):

```python
def test_isolation():
    with TestFramework() as fw1:
        with TestFramework() as fw2:
            assert fw1.lifecycle is not fw2.lifecycle
            fw1.lifecycle.transition(LifecycleState.CONFIGURING)
            fw2.lifecycle.transition(LifecycleState.CONFIGURING)
            fw2.lifecycle.transition(LifecycleState.CONFIGURED)

            assert len(fw1.history) == 2
            assert len(fw2.history) == 3
            assert fw1.capture.sequence != fw2.capture.sequence
```

### Partial Initialization

`TestFramework` handles partial initialization — calling `shutdown()` before
`startup()` completes is safe and deterministic:

```python
def test_partial_init():
    with TestFramework() as fw:
        fw.lifecycle.transition(LifecycleState.CONFIGURING)
        # exit without completing init — teardown still reaches STOPPED
    assert fw.lifecycle.state == LifecycleState.STOPPED
```

### Direct Usage Without Context Manager

`TestFramework` can also be used manually, but the context manager ensures
teardown:

```python
fw = TestFramework()
try:
    fw.lifecycle.transition(LifecycleState.CONFIGURING)
finally:
    fw.lifecycle.shutdown()
```

## LifecycleCapture

Helper that records every state transition in order, including forced
transitions performed by `shutdown()` for partial-init handling.

```python
from lingualdub.lifecycle import FrameworkLifecycle, LifecycleState
from lingualdub.testing.lifecycle import LifecycleCapture, assert_lifecycle_sequence

lc = FrameworkLifecycle()
capture = LifecycleCapture(lc)

lc.transition(LifecycleState.CONFIGURING)
lc.transition(LifecycleState.CONFIGURED)

assert capture.sequence == [
    LifecycleState.UNINITIALIZED,
    LifecycleState.CONFIGURING,
    LifecycleState.CONFIGURED,
]
# capture.history is an alias for sequence
```

`LifecycleCapture` wraps `transition`, `shutdown`, and `_handle_atexit` to
capture both normal and forced transitions. Use `capture.clear()` to reset
(keeps current history as seed) or `capture.detach()` to restore original
methods.

Passing a `FrameworkLifecycle` directly to `assert_lifecycle_sequence` also
works — it will read `lifecycle.history`.

## assert_lifecycle_sequence

Assertion helper with detailed diff on mismatch:

```python
from lingualdub.testing.lifecycle import LifecycleCapture, assert_lifecycle_sequence

# All of these forms work:
assert_lifecycle_sequence(capture, [LifecycleState.UNINITIALIZED, LifecycleState.CONFIGURING])
assert_lifecycle_sequence(fw.capture, expected)
assert_lifecycle_sequence(lifecycle, expected)  # reads lifecycle.history
assert_lifecycle_sequence([LifecycleState.UNINITIALIZED], expected)  # raw list
```

On failure, raises `AssertionError` with:

```
Lifecycle sequence mismatch.
  Expected: uninitialized → configuring → configured
  Actual:   uninitialized → ready
```

## Integration with Startup/Shutdown Hooks

`TestFramework` provides isolated hook registries:

```python
def test_hooks_isolated():
    with TestFramework() as fw1:
        fw1.lifecycle.register_startup_hook("a", lambda: None)
        with TestFramework() as fw2:
            assert fw2.lifecycle.list_startup_hooks() == []  # not shared
            assert fw1.lifecycle.list_startup_hooks() == ["a"]
```

Shutdown hooks are torn down in reverse order via `lifecycle.shutdown()` during
`TestFramework` exit.

## Parallel Execution

Tests using `TestFramework` are safe to run in parallel (`pytest -n auto` or
`pytest-xdist`) because no global state is shared. Each context owns its
lifecycle, capture, and hook registries.

## See Also

- `lingualdub/lifecycle.py` — `FrameworkLifecycle`, `LifecycleState`, `startup_hook`, `shutdown_hook`
- `lingualdub/testing/lifecycle.py` — implementation of `TestFramework`, `LifecycleCapture`, `assert_lifecycle_sequence`
- `tests/lifecycle/test_lifecycle_state.py` — state machine tests
