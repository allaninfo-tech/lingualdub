# Resource Ownership Model

This document defines ownership semantics for `lingualdub.core.resource.Resource` (REL-001).

## Ownership Categories

| Category | Value | Meaning | Cleanup Responsibility |
|---|---|---|---|
| `FRAMEWORK_OWNED` | `framework_owned` | Created and owned by the framework; e.g. temporary downloads, cached model weights via `ResourceManager`, pipeline artifacts. | **Framework** — deterministically cleaned up on `DependencyScope` exit (`scope.__exit__` calls `resource.close()`). `ResourceManager` also removes file at `path` best-effort. |
| `USER_OWNED` | `user_owned` | Supplied by caller (user-provided audio, external datasets, persistent checkpoints). | **User** — framework never deletes. `resource.close()` is a no-op for this ownership. This is the **default** (`Resource(..., ownership=ResourceOwnership.USER_OWNED)`). |
| `SHARED` | `shared` | Shared across scopes/caller — e.g. reference-counted or manually coordinated resources. | **Coordination** — framework does not auto-delete; caller/provider must coordinate `close()` externally. `resource.close()` is a no-op. |

## Enum

```python
from lingualdub.core.resource import ResourceOwnership, Resource

r = Resource(
    id="tmp_ckpt",
    kind=ResourceKind.CHECKPOINT,
    language="eng",
    version="1.0.0",
    provenance={},
    ownership=ResourceOwnership.FRAMEWORK_OWNED,
    path="/tmp/cache/model.bin",
)
r.close()  # deletes file

r2 = Resource(
    id="user_audio",
    kind=ResourceKind.SPEECH,
    language="lug",
    version="1.0.0",
    provenance={},
    ownership=ResourceOwnership.USER_OWNED,
    path="data/samples/sample_lug.wav",
)
r2.close()  # no-op
```

## Serialization

`ownership` is serialized to `to_dict()["ownership"]` as string (`framework_owned` etc.) and round-trips via `from_dict`. Missing key defaults to `user_owned` for backward compatibility.

## Scoped Teardown

`DependencyScope.__exit__` inspects `instance.ownership` when present. Only `FRAMEWORK_OWNED` instances have `close()` invoked automatically. All other scoped objects with `close()` (e.g. `FakeResourceManager`, custom providers) are still closed unless they explicitly carry a non-framework ownership.

`Resource.close()` itself also checks ownership and is idempotent (`_closed` flag).

## ResourceManager

`ResourceManager` respects ownership only for framework-managed cache paths. It does NOT delete `USER_OWNED`/`SHARED` paths even if `cleanup()` is called. Temporary files under `cache_dir/resource_id/version/` that were created as `FRAMEWORK_OWNED` are cleaned via `Resource.close()`.

## Migration

Existing resources without `ownership` deserialize as `USER_OWNED`. To opt into auto-cleanup, set `ownership=ResourceOwnership.FRAMEWORK_OWNED` and ensure the resource is resolved inside a `with container.create_scope() as scope:` block with `lifetime=SCOPED`.

## Testing

- `FRAMEWORK_OWNED` resource resolved inside a scope is cleaned exactly once on scope exit (`resource.is_closed == True`, file removed if existed).
- `USER_OWNED` / `SHARED` resources remain `is_closed == False` and file untouched after scope exit.
