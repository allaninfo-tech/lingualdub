# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
DI testing utilities — EXE-007.

Provides:

* :class:`FakeRegistry` — minimal in-memory registry fake.
* :class:`FakeResourceManager` — fake manager that returns deterministic paths
  without network or checksum verification.
* :class:`FakeLanguage` — lightweight language stub.
* :class:`TestContainer` — :class:`DependencyContainer` pre-populated with
  fakes for all framework services.
* :func:`assert_resolved_as` — assertion helper.

These utilities make DI tests ergonomic without constructing the full
framework dependency tree.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from lingualdub.core.language import Language
from lingualdub.di.container import DependencyContainer
from lingualdub.di.contracts import Lifetime

__all__ = [
    "FakeRegistry",
    "FakeResourceManager",
    "FakeLanguage",
    "TestContainer",
    "assert_resolved_as",
    "FakeResource",
]


class FakeRegistry:
    """Minimal fake for :class:`lingualdub.registry.Registry`.

    Stores registrations in-memory without conflict policies. Satisfies the
    subset of the Registry surface used in DI tests: ``register``,
    ``resolve`` and ``list``.

    The fake also exposes ``version`` so it satisfies
    :class:`lingualdub.core.protocols.RegistrableProtocol`.

    Attributes:
        version: Fake version string.
    """

    version: str = "0.0.0.fake"

    def __init__(self) -> None:
        # Use same internal shape as real Registry for debugging: {kind: {key: (impl, version)}}
        self._store: dict[tuple[str, str], tuple[Any, str]] = {}

    def register(
        self,
        kind: str,
        key: str,
        impl: Any,
        version: str = "0.0.0",
        metadata: dict | None = None,  # noqa: ARG002 — parity with real Registry
    ) -> None:
        """Register ``impl`` under ``(kind, key)``."""
        self._store[(kind, key)] = (impl, version)

    def resolve(self, kind: str, key: str, version: str | None = None) -> Any:  # noqa: ARG002
        """Resolve by ``(kind, key)``; ``version`` is ignored for fake."""
        try:
            impl, _ = self._store[(kind, key)]
        except KeyError as exc:
            from lingualdub.exceptions import ResolutionError

            raise ResolutionError(
                f"No fake registration for ({kind!r}, {key!r}).",
                kind=kind,
                key=key,
                code="FAKE_REGISTRY_001",
            ) from exc
        return impl

    def list(self, kind: str) -> list[tuple[str, str]]:
        """List ``(key, version)`` for a kind."""
        result: list[tuple[str, str]] = []
        for (k, key), (_, ver) in self._store.items():
            if k == kind:
                result.append((key, ver))
        return sorted(result)

    def clear(self) -> None:
        """Remove all fake registrations."""
        self._store.clear()

    def __repr__(self) -> str:
        return f"FakeRegistry(entries={len(self._store)})"


class FakeResourceManager:
    """Fake for :class:`lingualdub.utils.resource_manager.ResourceManager`.

    Does not perform downloads or checksum verification.  ``get`` and
    ``cache_path`` return deterministic ``Path`` values under a temporary
    directory.

    Attributes:
        version: Fake version for protocol parity.
        cache_dir: Root directory for fake cache paths.
    """

    version: str = "0.0.0.fake"

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        if cache_dir is not None:
            self.cache_dir = Path(cache_dir)
        else:
            # Use a temporary dir that persists for the life of the process
            self.cache_dir = Path(tempfile.gettempdir()) / "lingualdub_fake_cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(
        self,
        resource_id: str,
        version: str,
        url: str,  # noqa: ARG002 — not used for fake
        checksum: str,  # noqa: ARG002 — not used for fake
        filename: str | None = None,
    ) -> Path:
        """Return fake cache path without downloading.

        Args:
            resource_id: Resource identifier.
            version: Version string.
            url: Ignored for fake.
            checksum: Ignored for fake.
            filename: Optional filename; defaults to ``resource_id``.

        Returns:
            Deterministic fake Path.
        """
        fname = filename or f"{resource_id}.bin"
        return self.cache_dir / resource_id / version / fname

    def cache_path(self, resource_id: str, version: str, filename: str) -> Path:
        """Return expected cache path."""
        return self.cache_dir / resource_id / version / filename

    def close(self) -> None:
        """No-op close for scope-cleanup testing."""

    def __repr__(self) -> str:
        return f"FakeResourceManager(cache_dir={str(self.cache_dir)!r})"


class FakeLanguage:
    """Minimal fake for :class:`lingualdub.core.language.Language`.

    This fake intentionally does **not** inherit from :class:`Language` to avoid
    triggering validation, but it exposes the same public attributes so tests
    can use it wherever a language profile is needed.  A helper
    :meth:`as_language` converts it to a real :class:`Language` instance.

    Attributes:
        code: Language code (e.g. ``"lug"``).
        name: Human-readable name.
        family: Language family.
        version: Fake version string.
    """

    version: str = "0.0.0.fake"

    def __init__(
        self,
        code: str = "lug",
        name: str = "Fake Luganda",
        family: str = "Bantu (Great Lakes)",
        resource_profile: str = "speech-scarce",
    ) -> None:
        self.code: str = code
        self.name: str = name
        self.family: str = family
        self.resource_profile: str = resource_profile
        self.supported_tasks: list[str] = []
        self.related_languages: list[str] = []
        self.resources: list[str] = []
        self.compatible_components: list[str] = []
        self.metadata: dict[str, Any] = {}

    def as_language(self) -> Language:
        """Convert fake to a real :class:`Language` instance (validated)."""
        return Language(
            code=self.code,
            name=self.name,
            family=self.family,
            resource_profile=self.resource_profile,
            supported_tasks=list(self.supported_tasks),
            related_languages=list(self.related_languages),
            resources=list(self.resources),
            compatible_components=list(self.compatible_components),
            metadata=dict(self.metadata),
        )

    def close(self) -> None:
        """No-op close for scope-cleanup testing."""

    def __repr__(self) -> str:
        return f"FakeLanguage(code={self.code!r}, family={self.family!r})"


class TestContainer(DependencyContainer):
    """Pre-populated container for DI tests — EXE-007.

    Extends :class:`DependencyContainer` and registers fakes for all common
    framework services so tests can immediately ``resolve`` without manual
    wiring.

    Pre-registered services (all ``SINGLETON`` unless noted):

    * ``config`` — real :class:`FrameworkConfig` via :func:`load_config` with
      defaults.
    * ``registry`` — :class:`FakeRegistry`
    * ``resource_manager`` — :class:`FakeResourceManager`
    * ``language`` — :class:`FakeLanguage` (``lug``)
    * ``lifecycle`` — :class:`FrameworkLifecycle`
    * ``resource`` — :class:`FakeLanguage` as placeholder for generic resource

    Example:
        container = TestContainer()
        registry = container.resolve("registry")
        assert isinstance(registry, FakeRegistry)

    Tests may override any service via ``override`` / ``override_context``:

        with container.override_context("registry", MyFake()):
            ...

    Attributes:
        (inherited from DependencyContainer)
    """

    __test__ = False

    def __init__(self, *, auto_register: bool = True) -> None:
        super().__init__()
        if not auto_register:
            return

        # Import lazily to avoid circular imports at module import time
        from lingualdub.config import FrameworkConfig
        from lingualdub.lifecycle import FrameworkLifecycle

        # FrameworkConfig — use direct construction + validate to avoid env coupling
        try:
            cfg = FrameworkConfig()
            cfg.validate()
        except Exception:
            # Fallback to defaults without validation if needed
            cfg = FrameworkConfig()

        # Fakes
        fake_registry = FakeRegistry()
        fake_rm = FakeResourceManager()
        fake_lang = FakeLanguage()
        lifecycle = FrameworkLifecycle()

        # Register all with override=False; failures shouldn't happen on fresh container
        self.register_instance("config", cfg)
        # Also alias "framework_config" for convenience
        import contextlib

        with contextlib.suppress(Exception):
            self.register(
                "framework_config", lambda config=cfg: config, lifetime=Lifetime.SINGLETON
            )

        self.register_instance("registry", fake_registry)
        self.register_instance("resource_manager", fake_rm)
        self.register_instance("language", fake_lang)
        self.register_instance("lifecycle", lifecycle)
        # Additional aliases that some components might resolve by different names
        # These are factories returning the same singleton fakes, so they don't
        # create new entries beyond the primary ones.
        # We register them as TRANSIENT factories that delegate to primary,
        # but we guard against duplicate.
        for alias, target in [
            ("fake_registry", fake_registry),
            ("fake_resource_manager", fake_rm),
            ("fake_language", fake_lang),
        ]:
            with contextlib.suppress(Exception):
                self.register_instance(alias, target)


def assert_resolved_as(container: DependencyContainer, name: str, expected_type: type) -> Any:
    """Assert that ``container.resolve(name)`` returns an instance of ``expected_type``.

    Args:
        container: Container (or scope) with ``resolve``.
        name: Dependency name to resolve.
        expected_type: Expected type (class or tuple of classes).

    Returns:
        The resolved instance (for chaining).

    Raises:
        AssertionError: If the resolved instance is not of the expected type.
        ResolutionError: If ``name`` is not registered.
    """
    # Support both DependencyContainer and DependencyScope which expose resolve()
    resolved = container.resolve(name)  # type: ignore[operator]
    if not isinstance(resolved, expected_type):
        raise AssertionError(
            f"Dependency {name!r} expected to resolve as {expected_type.__name__!r}, "
            f"got {type(resolved).__name__!r}: {resolved!r}."
        )
    return resolved


# Backwards compatibility — some callers may expect ``FakeResource``
# but the correct name per roadmap is ``FakeResourceManager``.
FakeResource = FakeResourceManager
