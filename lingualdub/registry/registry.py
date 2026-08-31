"""
Registry implementation.

The Registry holds all registered Language, Resource, and Component objects,
resolved by (kind, key, version). It scans extension manifests at startup
and applies a conflict resolution policy when multiple extensions register
the same (kind, key) pair.
"""

from __future__ import annotations
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


def _version_tuple(version_str: str) -> tuple:
    """Convert a version string like '1.2.3' to a comparable tuple of ints."""
    try:
        return tuple(int(x) for x in version_str.split("."))
    except ValueError:
        return (0,)


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


class RegistryError(Exception):
    """Raised when a registry operation cannot be completed."""


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
        self._store: Dict[str, Dict[str, List[Tuple[str, Any, dict]]]] = defaultdict(
            lambda: defaultdict(list)
        )

    def register(
        self,
        kind: str,
        key: str,
        impl: Any,
        version: str = "0.0.0",
        metadata: Optional[dict] = None,
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
        metadata = metadata or {}
        entries = self._store[kind][key]

        if entries and self.conflict_policy == ConflictPolicy.EXPLICIT:
            raise RegistryError(
                f"Conflict: ({kind!r}, {key!r}) is already registered and "
                f"conflict_policy is EXPLICIT. Use an override to replace it."
            )

        if entries and self.conflict_policy == ConflictPolicy.HIGHEST_VERSION:
            # Keep only the highest version; replace existing only if new version is strictly higher.
            existing_version = entries[-1][0]
            if _version_tuple(version) > _version_tuple(existing_version):
                entries.clear()
            else:
                # New version is not higher — discard it, keep existing.
                return

        entries.append((version, impl, metadata))

    def resolve(self, kind: str, key: str, version: Optional[str] = None) -> Any:
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
        entries = self._store.get(kind, {}).get(key)
        if not entries:
            raise RegistryError(f"No registration found for ({kind!r}, {key!r}).")

        if version is None:
            # Return the most recently registered entry (latest by insertion order).
            return entries[-1][1]

        for v, impl, _ in entries:
            if v == version:
                return impl

        raise RegistryError(
            f"No registration found for ({kind!r}, {key!r}) at version {version!r}."
        )

    def list(self, kind: str) -> List[Tuple[str, str]]:
        """
        List all registered keys and latest versions for a given kind.

        Returns:
            A list of (key, latest_version) tuples.
        """
        result = []
        for key, entries in self._store.get(kind, {}).items():
            if entries:
                result.append((key, entries[-1][0]))
        return sorted(result)

    def __repr__(self) -> str:
        summary = {kind: list(keys.keys()) for kind, keys in self._store.items()}
        return f"Registry(policy={self.conflict_policy.value!r}, entries={summary})"
