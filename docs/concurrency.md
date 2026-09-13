# Concurrency Model (REL-004)

## Primary Execution Model: Synchronous

LingualDub's core execution model is **synchronous and blocking**. `PipelineExecutor.run()` runs each stage in order on the calling thread and blocks until all stages complete. This matches the typical research script (`lingualdub experiment run`) and keeps component authoring simple (no `async`/`await` inside `Component.run()`).

### What blocks

- **Model loading**: `ResourceManager.get()` may download (http/https) and verify SHA256; `PipelineExecutor` triggers component constructors that may load `torch`/`transformers` weights.
- **File I/O**: Reading `Resource.path`, writing `Result.artifacts`, forced-alignment dictionary lookup.
- **Network**: `ResourceManager` URL fetch, optional `pip`/`HF` hub calls inside lazy adapters.

All of the above happen on the thread that calls `executor.run()`.

### Registry Thread-Safety

`Registry` is safe for concurrent reads/writes (`threading.RLock`) (`lingualdub/registry/registry.py`). Reads (`resolve`, `list`) and writes (`register`) are mutually exclusive, but multiple concurrent reads serialize under the same lock — safe but not lock-free. `ManifestScanner.scan()` should run during startup (single-threaded) before concurrent resolves.

### DI Container Thread-Safety

`DependencyContainer` uses `threading.RLock` for registrations and singleton caches. Circular detection stacks are per-call.

### ResourcePool Thread-Safety

`ResourcePool` (`lingualdub/resources/pool.py`) uses `Condition` + `RLock` so `acquire`/`release` are thread-safe and never hand the same live instance to two acquirers.

## Recommended Patterns for Async Code

Do **not** call `executor.run()` directly from inside an `async` event loop — that blocks the loop.

### Pattern 1 — `run_pipeline_async` helper

```python
import asyncio
from lingualdub.async_utils import run_pipeline_async
from lingualdub.pipeline.executor import PipelineExecutor


async def handle_request(audio_resource):
    executor = PipelineExecutor(pipeline)  # may be created per-request or shared
    result = await run_pipeline_async(executor, audio_resource)
    return result
```

Internally `run_pipeline_async` is `await asyncio.to_thread(executor.run, input)`, so the blocking work runs in a worker thread from the default executor.

### Pattern 2 — `AsyncPipelineExecutor` wrapper

```python
from lingualdub.async_utils import AsyncPipelineExecutor

aexec = AsyncPipelineExecutor(PipelineExecutor(pipeline))


async def handle(request):
    result = await aexec.run(request.resource)
    return result
```

Both forms propagate exceptions correctly (`await` raises whatever `executor.run` raised).

### Pattern 3 — Sync service with thread pool / Process pool

If you need true parallelism (e.g. multiple GPU pipelines), create one `ResourcePool` per model and run each `run_pipeline_async` concurrently:

```python
results = await asyncio.gather(
    run_pipeline_async(exec_a, res_a),
    run_pipeline_async(exec_b, res_b),
)
```

### Blocking detection test

```python
import time, asyncio
from lingualdub.async_utils import run_pipeline_async


async def test_not_blocks_loop():
    loop = asyncio.get_running_loop()
    start = loop.time()
    task = asyncio.create_task(run_pipeline_async(executor, resource))
    # prove loop still ticks
    await asyncio.sleep(0.05)
    assert loop.time() - start < 0.2
    result = await task
    assert result.is_usable
```

## What still blocks the loop (do not do)

- `Registry.register()` inside a request handler that holds the Registry lock for long periods.
- `ResourceManager.get()` with a slow download — prefer warmup at startup via `pool = ResourcePool(..., min_idle=1)`.
- Creating a `torch` model inside `Component.run()` rather than in `Component.__init__` — move load to construction or `ResourcePool`.

## Future

A true `asyncio`-native executor (DAG, streaming segments) is out of scope for REL-004. The thin `to_thread` wrapper satisfies the spec: no event-loop blocking.
