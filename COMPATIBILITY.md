# Compatibility Policy

This document defines how LingualDub evolves its public API, what constitutes a breaking change, and how versioning reflects stability (PEV-001).

## Public API

The public API is defined by:

- Every symbol listed in `lingualdub/PUBLIC_API.md` and exported via `lingualdub.__all__`.
- Every subpackage `__all__` (see `tests/core/test_public_api.py`).
- Regression snapshots in `tests/regression/snapshots/` enforce the contract.

Internal symbols prefixed with `_` (and private modules like `lingualdub.utils.resource_helpers`, `lingualdub.components.tts.shared`, `lingualdub.components.code_switch.lexicons`) carry **no compatibility guarantee** and may change without notice.

## What is a Breaking Change

The following are considered **breaking** and require a **major** version bump:

- Removing a public symbol (class, function, enum, method, attribute).
- Renaming a public symbol or constructor parameter (e.g. `Resource.language` → `Resource.lang_code`).
- Changing a public constructor's required parameters or default values in a way that existing call sites fail.
- Changing a public function's return type or raised exception type (e.g. `Resource.from_dict` raising `ValueError` instead of `SerializationError`).
- Narrowing accepted input types (e.g. requiring `str` where `str|Path` was accepted).

The following are **not breaking** (minor version):

- Adding a new optional parameter with a default (e.g. `Resource.ownership` added with default `USER_OWNED`).
- Adding a new public class/function/enum.
- Adding a new `__all__` entry with a new optional dependency.

Patch version is for backwards-compatible bug fixes only.

## Semantic Versioning

We follow [SemVer](https://semver.org/):

- **MAJOR** — breaking changes.
- **MINOR** — additive, backwards-compatible functionality.
- **PATCH** — backwards-compatible bug fixes.

Example: `0.1.0` → `0.2.0` adds `ResourceOwnership` (minor, additive). `1.0.0` → `2.0.0` would remove `Resource.language`.

## Deprecation Period

No public symbol is removed without a deprecation period of **at least one minor release**:

1. Symbol is marked with `@deprecated(reason, replacement, since)` from `lingualdub.utils.deprecation`.
2. `CHANGELOG.md` lists it under `Deprecated` with `since` version and replacement.
3. Calls emit `DeprecationWarning`: `"[DEPRECATED since v{since}] {symbol} is deprecated. Use {replacement} instead."`
4. Warnings are suppressable via `warnings.filterwarnings("ignore", category=DeprecationWarning)`.
5. After one minor release, symbol may be removed (major bump) and `CHANGELOG.md` lists under `Removed`.

## Changelog

`CHANGELOG.md` is maintained for every release with sections: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security` (Keep a Changelog format). Each release is tagged `v*` and CI publishes via `.github/workflows/release.yml`.

## Enforcement

- **Regression test suite** `tests/regression/` (`test_public_api_surface.py`, `test_public_api_contracts.py`) fails on any breaking change not reflected in snapshots.
- **Review**: Any PR that changes `lingualdub/__init__.py` `__all__` or `PUBLIC_API.md` requires explicit approval and snapshot update.
- **Policy review**: This file is reviewed on each major release.

## Examples

- `Resource(language="lug")` → `Resource(lang_code="lug")` is **breaking** (major).
- Adding `FrameworkConfig.log_format` with default `"json"` is **minor** (additive).
- Removing `Component.degrade` without deprecation is **breaking**.
- Changing `validate_resource_path` to raise `ResourceError` instead of `ConfigurationValidationError` is **breaking** (exception type is part of contract).

## Contact

For compatibility questions, file an issue with label `api-break` and reference this policy.
