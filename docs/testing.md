# Testing Guide

This document describes the official testing utilities in `lingualdub.testing` (LCY-004, EXE-007, REL-005).

## Overview

`lingualdub.testing` provides isolated, deterministic helpers so tests get fresh framework instances without shared global state:

- `TestFramework` / `LifecycleCapture` / `assert_lifecycle_sequence` — lifecycle isolation (LCY-004)
- `TestContainer` / `FakeRegistry` / `FakeResourceManager` / `FakeLanguage` / `assert_resolved_as` — DI fakes (EXE-007)
- `LanguageBuilder` / `ResourceBuilder` / `SegmentBuilder` / `ResultBuilder` — fluent builders for domain objects (REL-005)
- `FakeASR` / `FakeTranslation` / `FakeTTS` / `FakeAlignment` / `FakeEvaluator` — deterministic fakes satisfying `ComponentProtocol` (REL-005)
- `assert_result_complete` / `assert_result_failed` / `assert_result_has_segment` / `assert_result_has_language` / `assert_resource_valid` — matchers (REL-005)
- `PipelineTestHarness` — end-to-end pipeline runner (REL-005)
- `FakeClock` — deterministic clock (REL-005)

All are re-exported from `lingualdub.testing`:

```python
from lingualdub.testing import PipelineTestHarness, ResultBuilder, FakeASR, assert_result_complete
```

## Builders

Builders produce valid instances with sensible defaults; override only what matters:

```python
from lingualdub.testing.builders import SegmentBuilder, ResultBuilder
from lingualdub.core.result import ResultStatus

seg = (
    SegmentBuilder()
    .with_text("Oli otya")
    .with_language("lug")
    .with_start(0.0)
    .with_end(1.4)
    .build()
)
result = (
    ResultBuilder()
    .with_segments([seg])
    .with_source_language("lug")
    .with_status(ResultStatus.COMPLETE)
    .build()
)

# Resource with FRAMEWORK_OWNED for scoped-cleanup tests
from lingualdub.testing.builders import ResourceBuilder
from lingualdub.core.resource import ResourceOwnership

r = (
    ResourceBuilder()
    .with_id("tmp")
    .with_ownership(ResourceOwnership.FRAMEWORK_OWNED)
    .with_path("/tmp/x.bin")
    .build()
)
```

### LanguageBuilder

```python
from lingualdub.testing.builders import LanguageBuilder

lang = LanguageBuilder().with_code("nyn").with_name("Runyankole").build()
```

## Fakes

Each fake is a concrete `Component` satisfying the protocol for DI tests:

```python
from lingualdub.testing.fakes import FakeASR, FakeTranslation, FakeTTS

asr = FakeASR(text="hello world", language="lug")
result = asr.run(resource)  # deterministic, no ML
assert result.segments[0].text == "hello world"
assert result.segments[0].language == "lug"
```

| Fake | Task | Requires | Provides |
|---|---|---|---|
| `FakeASR` | ASR | [] | transcription, word_timestamps |
| `FakeTranslation` | TRANSLATION | transcription | translation |
| `FakeTTS` | TTS | translation | audio |
| `FakeAlignment` | ALIGNMENT | transcription | aligned_timestamps |
| `FakeEvaluator` | EVAL | [] | metrics |

All support `degrade()` where applicable and are `runtime_checkable` for `isinstance(obj, ComponentProtocol)`.

## Matchers

```python
from lingualdub.testing.matchers import assert_result_complete, assert_result_has_segment

assert_result_complete(result)
seg = assert_result_has_segment(result, "hello", language="lug")
```

- `assert_result_complete(result)` — status COMPLETE and usable
- `assert_result_failed(result)` — status FAILED and not usable
- `assert_result_partial(result)` / `assert_result_degraded(result)`
- `assert_result_has_segment(result, text, language=None)` — returns matching segment or raises
- `assert_result_has_language(result, language)`
- `assert_resource_valid(resource)` — validates via round-trip

## PipelineTestHarness

Run a pipeline in under 20 lines without manual registry wiring:

```python
from lingualdub.testing.pipeline import PipelineTestHarness
from lingualdub.testing.fakes import FakeASR, FakeTranslation, FakeTTS
from lingualdub.testing.builders import ResourceBuilder
from lingualdub.testing.matchers import assert_result_complete

harness = PipelineTestHarness(source_language="lug", target_language="eng")
harness.with_components(FakeASR(), FakeTranslation(), FakeTTS())
result = harness.run(ResourceBuilder().build())
assert_result_complete(result)
```

Or from declarative config:

```python
result = harness.run_with_config(
    {
        "source_language": "lug",
        "target_language": "eng",
        "stages": ["fake_asr", "fake_translator", "fake_tts"],
    },
    ResourceBuilder().build(),
)
```

`PipelineTestHarness` owns a private `Registry`; `with_components` registers both for direct `run` and for `run_with_config`.

## FakeClock

Deterministic time control:

```python
from lingualdub.testing.clock import FakeClock

clock = FakeClock(start=0.0)
assert clock.time() == 0.0
clock.advance(1.5)
assert clock.now() == 1.5
clock.sleep(0.5)
assert clock.time() == 2.0
assert clock.sleeps == [0.5]

# Monkeypatch time.time/monotonic:
with clock:
    import time

    assert time.time() == 2.0
    clock.advance(10)
    assert time.monotonic() == 12.0
# auto-restored outside context
```

## Lifecycle Utilities (LCY-004)

See lifecycle section below (original LCY-004 docs preserved).

### TestFramework

Context manager that creates a fresh `FrameworkLifecycle` for each test and tears it down (`shutdown() → STOPPED`) on exit, even if the test raises.

```python
from lingualdub.testing.lifecycle import TestFramework, assert_lifecycle_sequence
from lingualdub.lifecycle import LifecycleState


def test_startup_flow():
    with TestFramework() as fw:
        assert fw.lifecycle.state == LifecycleState.UNINITIALIZED
        fw.lifecycle.transition(LifecycleState.CONFIGURING)
        fw.lifecycle.transition(LifecycleState.CONFIGURED)
        assert_lifecycle_sequence(
            fw.capture,
            [LifecycleState.UNINITIALIZED, LifecycleState.CONFIGURING, LifecycleState.CONFIGURED],
        )
    assert fw.lifecycle.state == LifecycleState.STOPPED
```

### LifecycleCapture

Helper that records every state transition in order, including forced transitions performed by `shutdown()` for partial-init handling.

### assert_lifecycle_sequence

Assertion helper with detailed diff on mismatch.

## Coverage

`lingualdub/testing/` itself has 100% branch coverage targeted — builders/fakes/matchers/harness/clock are each unit-tested in `tests/testing/`.

## See Also

- `lingualdub/testing/builders.py`
- `lingualdub/testing/fakes.py`
- `lingualdub/testing/matchers.py`
- `lingualdub/testing/pipeline.py`
- `lingualdub/testing/clock.py`
- `lingualdub/lifecycle.py` — `FrameworkLifecycle`, `LifecycleState`
- `tests/lifecycle/test_lifecycle_state.py`
