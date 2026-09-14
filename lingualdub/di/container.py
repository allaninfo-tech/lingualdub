# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Dependency container — registration, resolution, scopes, overrides and
circular detection.

The implementation satisfies EXE-002 .. EXE-006 in a single module:

* **Registration** — explicit ``register`` / ``register_instance`` with
  conflict detection.
* **Resolution** — ``resolve`` respecting ``SINGLETON``/``TRANSIENT``/``SCOPED``
  lifetimes and recursive construction via ``__init__`` parameter names.
* **Scopes** — ``create_scope()`` yields a :class:`DependencyScope` where
  ``SCOPED`` dependencies are singletons per scope and ``close()`` is called
  on exit.
* **Overrides** — ``override``/``restore``/``override_context`` for testing.
* **Circular detection** — resolution stack with chain reporting.

Thread-safety: registration and singleton caches are protected by a reentrant
lock; resolution stacks are per-call (not shared), so concurrent resolves are
safe as long as factories themselves are thread-safe.
"""

from __future__ import annotations

import inspect
import logging
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from lingualdub.di.contracts import Lifetime
from lingualdub.exceptions import LifecycleError, RegistrationConflictError, ResolutionError

logger = logging.getLogger(__name__)

__all__ = ["DependencyContainer", "DependencyScope"]


@dataclass
class _Registration:
    """Internal binding record."""

    name: str
    impl: Any
    lifetime: Lifetime


class DependencyScope:
    """Scoped resolution context for ``SCOPED`` lifetime.

    Usage:
        container = DependencyContainer()
        container.register("ctx", ExecutionContext, lifetime=Lifetime.SCOPED)
        with container.create_scope() as scope:
            a = scope.resolve("ctx")
            b = scope.resolve("ctx")
            assert a is b  # same within scope

    Scoped instances that expose a ``close()`` method are closed
    (best-effort, logged) on ``__exit__``.

    Nested scopes are not supported and raise :class:`LifecycleError` on
    ``__enter__`` if another scope is already active on the same container.

    Attributes:
        container: Parent container.
        instances: Live scoped instances (for debugging).
    """

    def __init__(self, container: DependencyContainer) -> None:
        self._container: DependencyContainer = container
        self._instances: dict[str, Any] = {}
        self._entered: bool = False

    @property
    def instances(self) -> dict[str, Any]:
        """Copy of current scoped instances."""
        return dict(self._instances)

    def __enter__(self) -> DependencyScope:
        if self._container._active_scope is not None:
            raise LifecycleError(
                "Nested scopes are not supported — an active scope already exists for this container.",
                code="SCOPE_NESTED_001",
                context={"active_scope": repr(self._container._active_scope)},
            )
        self._container._active_scope = self
        self._entered = True
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
        # Best-effort close of scoped instances that implement close()
        # Ownership-aware: only FRAMEWORK_OWNED resources are auto-cleaned;
        # USER_OWNED/SHARED and non-Resource scoped objects are still closed
        # via their own close() which internally respects ownership.
        for name, inst in list(self._instances.items()):
            # Ownership-aware skip for Resource instances
            try:
                from lingualdub.core.resource import ResourceOwnership

                ownership = getattr(inst, "ownership", None)
                if (
                    isinstance(ownership, ResourceOwnership)
                    and ownership != ResourceOwnership.FRAMEWORK_OWNED
                ):
                    # USER_OWNED / SHARED — framework does not own cleanup
                    continue
            except Exception:
                pass
            close = getattr(inst, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # noqa: BLE001 — must not abort teardown
                    logger.warning(
                        "Scoped instance %r close() failed for dependency %r",
                        type(inst).__name__,
                        name,
                        exc_info=True,
                    )
        self._instances.clear()
        # Only clear if we are still the active scope (defensive if nested error)
        if self._container._active_scope is self:
            self._container._active_scope = None
        self._entered = False
        return False  # do not suppress exceptions

    def resolve(self, name: str) -> Any:
        """Resolve ``name`` within this scope.

        Delegates to the parent container with this scope as the active
        context, so ``SCOPED`` lifetime returns the per-scope singleton.

        Args:
            name: Registered dependency name.

        Returns:
            Resolved instance.

        Raises:
            ResolutionError: If not registered or construction fails.
        """
        from lingualdub.utils.validation import require_non_empty_string

        require_non_empty_string(name, "name")
        # Ensure this scope is the active one; if user calls scope.resolve()
        # outside the ``with`` block we still allow it but ensure the
        # container sees this scope.  If another scope is active, this is an
        # error (should have been entered correctly).
        # We temporarily set active if not already set and we are not nested.
        was_active = self._container._active_scope
        if was_active is None:
            # Allow resolve outside ``with`` as transient scoped (not cached beyond call).
            # We still create a stack and resolve with this scope as context,
            # but we do not set _active_scope globally.
            _stack: list[str] = []
            return self._container._resolve_internal(name, _stack, self)
        if was_active is not self:
            raise LifecycleError(
                "Cannot resolve via a scope that is not the active scope.",
                code="SCOPE_INACTIVE_001",
                context={"requested_scope": id(self), "active_scope": id(was_active)},
            )
        _stack2: list[str] = []
        return self._container._resolve_internal(name, _stack2, self)


class DependencyContainer:
    """Explicit dependency container with lifetime-aware resolution.

    Example:
        container = DependencyContainer()
        container.register("registry", Registry, lifetime=Lifetime.SINGLETON)
        container.register("executor", PipelineExecutor, lifetime=Lifetime.TRANSIENT)
        # PipelineExecutor.__init__(self, registry) will be auto-wired
        executor = container.resolve("executor")

    Registration is explicit and auditable via :meth:`list_registered`.
    """

    def __init__(self) -> None:
        self._registrations: dict[str, _Registration] = {}
        self._singletons: dict[str, Any] = {}
        self._overrides: dict[str, list[Any]] = {}
        self._active_scope: DependencyScope | None = None
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Registration — EXE-002
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        implementation_or_factory: Any,
        lifetime: Lifetime = Lifetime.SINGLETON,
        *,
        override: bool = False,
    ) -> None:
        """Register a service.

        Args:
            name: Unique dependency name.
            implementation_or_factory: Class or factory callable that constructs
                the service.  Factories are called with auto-resolved dependencies
                derived from their ``__init__``/``__call__`` parameter names.
            lifetime: Lifetime of constructed instances.
            override: If ``True``, replaces an existing registration.  Otherwise
                duplicate names raise :class:`RegistrationConflictError`.

        Raises:
            ConfigurationValidationError: If ``name`` is not a non-empty string.
            RegistrationConflictError: If ``name`` already registered and
                ``override`` is ``False``.
            ValueError: If ``lifetime`` is not a ``Lifetime``.
        """
        from lingualdub.utils.validation import require_non_empty_string

        require_non_empty_string(name, "name")
        if not isinstance(lifetime, Lifetime):
            raise ValueError(  # justified: DI registration contract — lifetime must be Lifetime enum
                f"lifetime must be a Lifetime, got {type(lifetime).__name__}: {lifetime!r}."
            )
        if implementation_or_factory is None:
            raise ValueError(  # justified: DI registration requires non-None factory
                f"implementation_or_factory for {name!r} must not be None."
            )
        # ``implementation_or_factory`` may be a class, function, or any callable.
        # We allow any non-None value; construction failures are reported at
        # resolve time as ResolutionError, per EXE-003.
        # However non-callable non-class values should be registered via
        # ``register_instance`` — we treat them as conflict but allow with
        # override? To keep API forgiving we accept any.
        with self._lock:
            if name in self._registrations and not override:
                raise RegistrationConflictError(
                    f"Dependency {name!r} is already registered.",
                    kind="dependency",
                    key=name,
                    code="DI_CONFLICT_001",
                    context={"name": name, "lifetime": lifetime.value},
                )
            # If overriding, clear singleton cache so new impl takes effect
            if name in self._registrations and override:
                self._singletons.pop(name, None)
                # Also remove from any active scope cache (best-effort)
                if self._active_scope is not None:
                    self._active_scope._instances.pop(name, None)
            self._registrations[name] = _Registration(
                name=name, impl=implementation_or_factory, lifetime=lifetime
            )

    def register_instance(
        self,
        name: str,
        instance: Any,
        *,
        override: bool = False,
    ) -> None:
        """Register a pre-built singleton instance.

        Args:
            name: Unique dependency name.
            instance: Already constructed instance to return for every resolve.
            override: If ``True``, replaces an existing registration.

        Raises:
            ConfigurationValidationError: If ``name`` invalid.
            RegistrationConflictError: If duplicate without ``override``.
            ValueError: If ``instance`` is ``None``.
        """
        from lingualdub.utils.validation import require_non_empty_string

        require_non_empty_string(name, "name")
        if instance is None:
            raise ValueError(  # justified: DI register_instance requires non-None instance
                f"register_instance for {name!r} requires a non-None instance."
            )

        with self._lock:
            if name in self._registrations and not override:
                raise RegistrationConflictError(
                    f"Dependency {name!r} is already registered.",
                    kind="dependency",
                    key=name,
                    code="DI_CONFLICT_001",
                    context={"name": name},
                )
            # Register as SINGLETON with direct impl = instance type? But store
            # instance in singletons cache.  Keep impl as the instance's class
            # for introspection, but resolve returns the exact instance.
            # To avoid confusing _construct path, store a marker impl and
            # pre-populate singleton cache; resolve will return cached.
            self._registrations[name] = _Registration(
                name=name, impl=type(instance), lifetime=Lifetime.SINGLETON
            )
            # Store the exact instance (not via construction)
            self._singletons[name] = instance
            # Clear any override stack? No — instance is the authoritative,
            # but overrides temporarily hide it.
            # If override active, we keep it; restore will reveal this instance.

    def list_registered(self) -> list[str]:
        """Return sorted list of registered dependency names."""
        with self._lock:
            return sorted(self._registrations.keys())

    # ------------------------------------------------------------------
    # Resolution — EXE-003 (and EXE-006 circular detection)
    # ------------------------------------------------------------------

    def resolve(self, name: str) -> Any:
        """Retrieve or construct a registered service.

        Resolution respects the registration's ``Lifetime``:

        * ``SINGLETON`` — constructed once, cached at container.
        * ``SCOPED`` — if an active scope exists, cached per scope; otherwise
          constructed fresh each call (transient-like) without global caching.
        * ``TRANSIENT`` — fresh instance each call.

        Recursive construction: if the implementation's ``__init__`` has parameters
        whose names match registered dependencies, those dependencies are resolved
        recursively and injected as keyword arguments.

        Circular dependencies are detected via a resolution stack and raise
        :class:`ResolutionError` with a chain message ``"A → B → A"``.

        Args:
            name: Registered dependency name.

        Returns:
            Resolved instance.

        Raises:
            ConfigurationValidationError: If ``name`` invalid.
            ResolutionError: If not registered, construction fails, or a
                circular dependency is detected (overflow beyond Python
                recursion is avoided).
        """
        from lingualdub.utils.validation import require_non_empty_string

        require_non_empty_string(name, "name")

        # Overrides take precedence even before registration check for error
        # reporting? But EXE-005 says overriding unregistered name raises
        # ResolutionError at override time, not here. At resolve time, if
        # overrides exist for this name, we return the fake regardless of
        # whether name was ever registered? However we enforce at override().
        # For safety, if name in overrides, return override even if not
        # registered (allows overriding before registration? but spec says not).
        # We still check registration after overrides for missing case.
        with self._lock:
            # Fast-path: singletons and overrides without stack
            if name in self._overrides and self._overrides[name]:
                return self._overrides[name][-1]
            reg = self._registrations.get(name)
            if reg is None:
                raise ResolutionError(
                    f"No registration found for dependency {name!r}.",
                    kind="dependency",
                    key=name,
                    code="DI_RESOLVE_001",
                    context={"name": name, "registered": self.list_registered()},
                )
            if reg.lifetime == Lifetime.SINGLETON and name in self._singletons:
                return self._singletons[name]
            if (
                reg.lifetime == Lifetime.SCOPED
                and self._active_scope is not None
                and name in self._active_scope._instances
            ):
                return self._active_scope._instances[name]

        # Need construction — create per-call stack
        stack: list[str] = []
        return self._resolve_internal(name, stack, self._active_scope)

    # Internal recursive helper (shared by container and scope)
    def _resolve_internal(
        self,
        name: str,
        stack: list[str],
        scope: DependencyScope | None,
    ) -> Any:
        """Recursive resolution with stack and scope awareness.

        Args:
            name: Dependency to resolve.
            stack: Current resolution chain (mutable, caller owns).
            scope: Active scope for SCOPED lifetime, or None.

        Returns:
            Resolved instance.

        Raises:
            ResolutionError: On missing registration, construction failure,
                or circular dependency.
        """
        # Overrides win immediately (no circular check for fakes)
        if name in self._overrides and self._overrides[name]:
            return self._overrides[name][-1]

        reg = self._registrations.get(name)
        if reg is None:
            raise ResolutionError(
                f"No registration found for dependency {name!r}.",
                kind="dependency",
                key=name,
                code="DI_RESOLVE_001",
                context={"name": name, "chain": list(stack)},
            )

        # Check caches before circular detection — already constructed
        # singletons/scoped instances don't need stack tracking.
        if reg.lifetime == Lifetime.SINGLETON and name in self._singletons:
            return self._singletons[name]
        if reg.lifetime == Lifetime.SCOPED and scope is not None and name in scope._instances:
            return scope._instances[name]

        # Circular detection — if name already in current call chain
        if name in stack:
            idx = stack.index(name)
            chain = stack[idx:] + [name]
            raise ResolutionError(
                f"Circular dependency detected: {' → '.join(chain)}",
                kind="dependency",
                key=name,
                code="DI_CIRCULAR_001",
                context={"chain": chain, "stack": list(stack)},
            )

        stack.append(name)
        try:
            instance = self._construct(name, reg, stack, scope)
            # Cache per lifetime
            if reg.lifetime == Lifetime.SINGLETON:
                with self._lock:
                    # Double-checked locking: another thread may have constructed
                    if name not in self._singletons:
                        self._singletons[name] = instance
                    else:
                        instance = self._singletons[name]
            elif reg.lifetime == Lifetime.SCOPED and scope is not None:
                scope._instances[name] = instance
            # TRANSIENT and SCOPED without scope: no caching
            return instance
        finally:
            stack.pop()

    def _construct(
        self,
        name: str,
        reg: _Registration,
        stack: list[str],
        scope: DependencyScope | None,
    ) -> Any:
        """Construct the instance for ``reg``, recursively resolving deps.

        Args:
            name: Dependency name (for error messages).
            reg: Registration record.
            stack: Current resolution stack.
            scope: Active scope.

        Returns:
            New instance.

        Raises:
            ResolutionError: If construction fails.
        """
        impl = reg.impl

        # Special case: if this registration came from register_instance, the
        # singleton cache would have already been hit. If we are here, it
        # means cache was cleared (override) or we are constructing anew.
        # For register_instance we stored ``type(instance)`` as impl but lost
        # the original instance. In that case we treat impl as the class of the
        # original — constructing it may not equal the original instance, but
        # this path only happens when singleton missing, so we construct fresh.
        # That's acceptable; register_instance's intent is to provide a singleton,
        # which we cached. If cache was overridden, we don't have original.
        # So we just construct via normal path.

        is_cls = inspect.isclass(impl)

        # Determine signature target
        # For classes, use __init__; for callables, use the object itself
        # For callable instances (with __call__), inspect the instance's __call__
        target: Any
        if is_cls:
            # ``__init__`` may be inherited from object — handle absence gracefully
            target = getattr(impl, "__init__", None)
            if target is None:
                try:
                    return impl()  # type: ignore[call-arg]
                except Exception as exc:
                    raise ResolutionError(
                        f"Failed to construct dependency {name!r}: {exc}",
                        kind="dependency",
                        key=name,
                        code="DI_CONSTRUCT_001",
                        context={"name": name},
                    ) from exc
        else:
            # Not a class — function, lambda, or callable instance (__call__)
            target = impl

        try:
            sig = inspect.signature(target)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            # Cannot introspect (e.g., built-in) — attempt no-arg construct
            try:
                return impl() if is_cls else impl()  # type: ignore[call-arg]
            except Exception as exc:
                raise ResolutionError(
                    f"Failed to construct dependency {name!r}: {exc}",
                    kind="dependency",
                    key=name,
                    code="DI_CONSTRUCT_001",
                    context={"name": name},
                ) from exc

        # Build kwargs: resolve dependencies by parameter name
        kwargs: dict[str, Any] = {}
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            # If parameter name matches a registration, inject it
            if param_name in self._registrations:
                # Resolve recursively
                try:
                    dep = self._resolve_internal(param_name, stack, scope)
                except ResolutionError:
                    raise
                except Exception as exc:  # defensive
                    raise ResolutionError(
                        f"Failed to resolve dependency {param_name!r} for {name!r}: {exc}",
                        kind="dependency",
                        key=param_name,
                        code="DI_RESOLVE_002",
                        context={"parent": name, "dependency": param_name},
                    ) from exc
                kwargs[param_name] = dep
            elif param.default is not inspect.Parameter.empty:
                # Has default — do not inject, let default apply
                continue
            else:
                # Required param without registration — will cause construction
                # to fail; let the impl call raise TypeError and we wrap it.
                # But we could also check if param annotation matches a registration
                # by type name? Spec says only by name, so we leave as missing.
                continue

        # Attempt construction
        try:
            if is_cls:
                return impl(**kwargs)  # type: ignore[call-arg]
            # Callable factory
            # Try with kwargs; if it fails due to unexpected kwargs (factory
            # takes no deps), retry without kwargs for zero-arg factories that
            # were registered without dependencies.
            try:
                return impl(**kwargs)  # type: ignore[call-arg]
            except TypeError as te:
                # If kwargs empty, this is already the failure; otherwise try
                # without kwargs to support factories that don't declare deps
                if kwargs and "unexpected keyword argument" in str(te):
                    # Retry without kwargs if the error was about unexpected kw
                    # This handles factories that legitimately take no args
                    # but we attempted to inject. In that case fail with clearer
                    # message rather than silently ignoring.
                    # Instead treat as construct failure with dependency info
                    raise ResolutionError(
                        f"Failed to construct dependency {name!r}: {te} (injected dependencies {list(kwargs.keys())})",
                        kind="dependency",
                        key=name,
                        code="DI_CONSTRUCT_001",
                        context={"name": name, "injected": list(kwargs.keys())},
                    ) from te
                raise
        except ResolutionError:
            raise
        except Exception as exc:
            raise ResolutionError(
                f"Failed to construct dependency {name!r}: {exc}",
                kind="dependency",
                key=name,
                code="DI_CONSTRUCT_001",
                context={"name": name},
            ) from exc

    # ------------------------------------------------------------------
    # Scopes — EXE-004
    # ------------------------------------------------------------------

    def create_scope(self) -> DependencyScope:
        """Create a new dependency scope.

        Returns:
            A :class:`DependencyScope` context manager.

        Example:
            with container.create_scope() as scope:
                ctx = scope.resolve("execution_context")
        """
        return DependencyScope(self)

    # ------------------------------------------------------------------
    # Overrides — EXE-005
    # ------------------------------------------------------------------

    def override(self, name: str, fake_instance: Any) -> None:
        """Temporarily replace a registration with a fake instance.

        Args:
            name: Registered dependency name to override.
            fake_instance: Fake or mock to return for subsequent resolves.

        Raises:
            ConfigurationValidationError: If ``name`` invalid.
            ResolutionError: If ``name`` is not registered.
        """
        from lingualdub.utils.validation import require_non_empty_string

        require_non_empty_string(name, "name")
        if fake_instance is None:
            raise ValueError(  # justified: test override requires non-None fake
                f"fake_instance for {name!r} must not be None."
            )
        with self._lock:
            if name not in self._registrations:
                raise ResolutionError(
                    f"Cannot override unregistered dependency {name!r}.",
                    kind="dependency",
                    key=name,
                    code="DI_OVERRIDE_001",
                    context={"name": name},
                )
            self._overrides.setdefault(name, []).append(fake_instance)

    def restore(self, name: str) -> None:
        """Restore the original registration after an override.

        Pops the most recent override for ``name``.  Nested overrides
        correctly restore to the outer override, not the original.

        Args:
            name: Dependency name to restore.

        Raises:
            ResolutionError: If no active override for ``name``.
        """
        from lingualdub.utils.validation import require_non_empty_string

        require_non_empty_string(name, "name")
        with self._lock:
            stack = self._overrides.get(name)
            if not stack:
                raise ResolutionError(
                    f"No active override to restore for dependency {name!r}.",
                    kind="dependency",
                    key=name,
                    code="DI_OVERRIDE_002",
                    context={"name": name},
                )
            stack.pop()
            if not stack:
                self._overrides.pop(name, None)

    @contextmanager
    def override_context(self, name: str, fake_instance: Any):  # type: ignore[no-untyped-def]
        """Context manager that overrides a dependency and auto-restores.

        Example:
            with container.override_context("registry", FakeRegistry()):
                executor = container.resolve("executor")  # uses fake

        Args:
            name: Dependency name.
            fake_instance: Fake to use within the context.

        Yields:
            The ``fake_instance``.

        Raises:
            ResolutionError: If ``name`` not registered.
        """
        self.override(name, fake_instance)
        try:
            yield fake_instance
        finally:
            # Use restore which handles stack correctly even if exception
            try:
                self.restore(name)
            except ResolutionError:
                # Should not happen, but log
                logger.warning("Failed to restore override for %r", name, exc_info=True)

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def is_registered(self, name: str) -> bool:
        """Return True if ``name`` is registered."""
        with self._lock:
            return name in self._registrations

    def clear(self) -> None:
        """Remove all registrations and cached singletons (testing utility).

        Clears registrations, singletons, and overrides. Does not affect
        active scopes (caller must ensure no scope is active).
        """
        with self._lock:
            self._registrations.clear()
            self._singletons.clear()
            self._overrides.clear()

    def __repr__(self) -> str:
        return f"DependencyContainer(registered={self.list_registered()})"
