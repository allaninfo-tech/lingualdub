# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Registry implementation.

The Registry holds all registered Language, Resource, and Component objects,
resolved by (kind, key, version). It scans extension manifests at startup
and applies a conflict resolution policy when multiple extensions register
the same (kind, key) pair.

Thread-safety
-------------
The Registry is safe for concurrent reads from multiple threads. All write
operations (``register``) and read operations (``resolve``, ``list``) are
protected by a single ``threading.RLock`` so callers may register new
components while pipeline threads are resolving existing ones. Iteration
over the store is atomic under the lock; callers receive a snapshot copy.
Plugins may therefore safely call ``register`` during startup while other
threads call ``resolve``/``list``. The ``conflict_policy`` attribute is
also guarded by the same lock.

For maximal throughput, the lock is re-entrant (``RLock``) so a thread
holding the lock may re-enter ``resolve`` from within a ``register``
callback.
"""

from __future__ import annotations

import builtins
import contextlib
import threading
from collections import defaultdict
from enum import Enum
from typing import Any

from lingualdub.core.protocols import ComponentProtocol, RegistrableProtocol
from lingualdub.exceptions import RegistrationConflictError as _BaseRegistrationConflictError
from lingualdub.exceptions import RegistryError as _BaseRegistryError
from lingualdub.exceptions import ResolutionError as _BaseResolutionError


def _version_tuple(version_str: str) -> tuple:
    """Convert a version string like '1.2.3' to a comparable tuple of ints, stripping pre-release."""
    try:
        core = version_str.split("-")[0].split("+")[0]
        parts = core.split(".")
        # Require 2-3 numeric parts, else fallback to (0,)
        if len(parts) < 2 or len(parts) > 3:
            return (0,)
        return tuple(int(x) for x in parts)
    except ValueError:
        return (0,)


def _is_cache_enabled() -> bool:
    try:
        from lingualdub.config import is_cache_enabled

        return bool(is_cache_enabled())
    except Exception:
        return True


class ConflictPolicy(str, Enum):
    """
    Policy governing resolution when two extensions register the same (kind, key).

    NAMESPACED      — both registrations are kept under namespaced keys
                      (e.g. "sunbird:asr" and "whisper:asr"). Default.
    HIGHEST_VERSION — the highest declared version wins automatically.
    EXPLICIT        — an explicit override is required; ambiguity raises an error.
    """

    NAMESPACED = "namespaced"
    HIGHEST_VERSION = "highest_version"
    EXPLICIT = "explicit"


# Canonical re-export — single source of truth remains ``lingualdub.exceptions``
RegistryError = _BaseRegistryError
RegistrationConflictError = _BaseRegistrationConflictError
ResolutionError = _BaseResolutionError


class Registry:
    """
    Central registry for languages, resources, components, and evaluators.

    Usage:
        registry = Registry()
        registry.register("component", "my_asr", MyASRClass, version="1.0.0")
        asr = registry.resolve("component", "my_asr")

    Attributes:
        conflict_policy: How to handle (kind, key) conflicts between extensions.
    """

    def __init__(self, conflict_policy: ConflictPolicy = ConflictPolicy.NAMESPACED) -> None:
        self.conflict_policy = conflict_policy
        # Stored as: { kind: { key: [ (version, impl, metadata) ] } }
        self._store: dict[str, dict[str, list[tuple[str, Any, dict]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._lock = threading.RLock()
        self._resolve_cache: dict[tuple, Any] = {}

    def register(
        self,
        kind: str,
        key: str,
        impl: ComponentProtocol | RegistrableProtocol | Any,
        version: str = "0.0.0",
        metadata: dict | None = None,
    ) -> None:
        """
        Register an implementation under a (kind, key) pair.

        Args:
            kind: Category of the registration ("language", "resource",
                  "component", "evaluator").
            key: Unique key within this kind (e.g. "lug", "lug_speech_v2",
                 "whisper_asr").
            impl: The object or class to register.
            version: Version string for this registration.
            metadata: Optional dict of additional metadata.
        """
        from lingualdub.utils.validation import require_non_empty_string, validate_version_string

        require_non_empty_string(kind, "kind")
        require_non_empty_string(key, "key")
        validate_version_string(version)
        if metadata is not None and not isinstance(metadata, dict):
            raise RegistryError(
                f"metadata must be a dict, got {type(metadata).__name__}: {metadata!r}."
            )
        metadata = metadata or {}
        # Copy metadata to break external refs
        metadata = dict(metadata)
        with self._lock:
            entries = self._store[kind][key]

            if entries and self.conflict_policy == ConflictPolicy.EXPLICIT:
                raise RegistryError(
                    f"Conflict: ({kind!r}, {key!r}) is already registered and "
                    f"conflict_policy is EXPLICIT. Use an override to replace it."
                )

            if entries and self.conflict_policy == ConflictPolicy.HIGHEST_VERSION:
                # Compare against highest stored version, not just last inserted
                max_version = max((v for v, _, _ in entries), key=_version_tuple)
                if _version_tuple(version) > _version_tuple(max_version):
                    entries.clear()
                elif _version_tuple(version) == _version_tuple(max_version):
                    # Same version but possibly different impl — keep both for history but don't discard silently
                    # If exact version string already exists, reject duplicate silently with warning
                    if any(v == version for v, _, _ in entries):
                        import logging

                        logging.getLogger(__name__).warning(
                            "Duplicate registration for (%r, %r) version %r discarded (HIGHEST_VERSION)",
                            kind,
                            key,
                            version,
                        )
                        return
                else:
                    # New version is not higher — discard it, keep existing.
                    import logging

                    logging.getLogger(__name__).debug(
                        "Registration for (%r, %r) version %r discarded, keeping %r (HIGHEST_VERSION)",
                        kind,
                        key,
                        version,
                        max_version,
                    )
                    return

            entries.append((version, impl, metadata))
            # Invalidate cache on mutation (PEV-005)
            try:
                if _is_cache_enabled():
                    # Clear any cached resolves for this kind/key
                    self._resolve_cache.pop((kind, key, None), None)
                    self._resolve_cache.pop((kind, key, version), None)
                    # For HIGHEST_VERSION, any version None cache may be stale, clear all None
                    # Simplest: clear all if HIGHEST_VERSION
                    if self.conflict_policy == ConflictPolicy.HIGHEST_VERSION:
                        self._resolve_cache.clear()
            except Exception:
                pass

    def resolve(
        self, kind: str, key: str, version: str | None = None
    ) -> ComponentProtocol | RegistrableProtocol | Any:
        """
        Resolve a registration by (kind, key) and optionally version.

        Args:
            kind: Category of the registration.
            key: Key to look up.
            version: Exact version to retrieve. If None, returns the latest entry.

        Returns:
            The registered implementation.

        Raises:
            RegistryError: If no matching registration is found.
        """
        # PEV-005 cache check (versioned and unversioned when enabled)
        if _is_cache_enabled():
            cache_key = (kind, key, version)
            with self._lock:
                if cache_key in self._resolve_cache:
                    return self._resolve_cache[cache_key]
        with self._lock:
            entries = self._store.get(kind, {}).get(key)
            if not entries:
                raise RegistryError(f"No registration found for ({kind!r}, {key!r}).")

            if version is None:
                # Return the highest version (not insertion-latest) for HIGHEST_VERSION policy
                if self.conflict_policy == ConflictPolicy.HIGHEST_VERSION:
                    best = max(entries, key=lambda x: _version_tuple(x[0]))
                    result = best[1]
                else:
                    result = entries[-1][1]
                if _is_cache_enabled():
                    with contextlib.suppress(Exception):
                        self._resolve_cache[(kind, key, None)] = result
                return result

            for v, impl, _ in entries:
                if v == version:
                    if _is_cache_enabled():
                        with contextlib.suppress(Exception):
                            self._resolve_cache[(kind, key, version)] = impl
                    return impl

            raise RegistryError(
                f"No registration found for ({kind!r}, {key!r}) at version {version!r}."
            )

    def list(self, kind: str) -> builtins.list[tuple[str, str]]:
        """
        List all registered keys and latest versions for a given kind.

        Returns:
            A list of (key, latest_version) tuples.
        """
        with self._lock:
            result = []
            for key, entries in list(self._store.get(kind, {}).items()):
                if entries:
                    if self.conflict_policy == ConflictPolicy.HIGHEST_VERSION:
                        best_version = max((v for v, _, _ in entries), key=_version_tuple)
                        result.append((key, best_version))
                    else:
                        result.append((key, entries[-1][0]))
            return sorted(result)

    def __repr__(self) -> str:
        summary = {kind: list(keys.keys()) for kind, keys in self._store.items()}
        return f"Registry(policy={self.conflict_policy.value!r}, entries={summary})"
