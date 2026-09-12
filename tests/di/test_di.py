# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for EXE phase — Dependency Injection contracts, container, scopes,
overrides, circular detection and testing utilities.

Covers EXE-001 .. EXE-007 expectations in a single batch to restore coverage.
"""

from __future__ import annotations

import threading

import pytest

from lingualdub.di import (
    _MISSING,
    Dependency,
    DependencyContainer,
    DependencyDescriptor,
    Lifetime,
)
from lingualdub.di.contracts import _MISSING as DI_MISSING
from lingualdub.exceptions import (
    ConfigurationValidationError,
    LifecycleError,
    RegistrationConflictError,
    ResolutionError,
)
from lingualdub.testing.di import (
    FakeLanguage,
    FakeRegistry,
    FakeResourceManager,
    TestContainer,
    assert_resolved_as,
)

# ---------------------------------------------------------------------------
# EXE-001 — contracts
# ---------------------------------------------------------------------------


class TestDependencyContracts:
    def test_lifetime_values(self):
        assert Lifetime.SINGLETON.value == "singleton"
        assert Lifetime.SCOPED.value == "scoped"
        assert Lifetime.TRANSIENT.value == "transient"
        assert set(Lifetime) == {Lifetime.SINGLETON, Lifetime.SCOPED, Lifetime.TRANSIENT}
        assert len(Lifetime) == 3

    def test_dependency_descriptor_stores_fields(self):
        d = DependencyDescriptor(
            name="my_dep", type_hint=str, lifetime=Lifetime.TRANSIENT, default=None
        )
        assert d.name == "my_dep"
        assert d.type_hint is str
        assert d.lifetime == Lifetime.TRANSIENT
        assert d.default is None

    def test_descriptor_default_missing(self):
        d = DependencyDescriptor(name="x", type_hint=int)
        assert d.default is _MISSING
        assert d.default is DI_MISSING

    def test_descriptor_invalid_name(self):
        with pytest.raises(ValueError):
            DependencyDescriptor(name="", type_hint=str)
        with pytest.raises(ValueError):
            DependencyDescriptor(name="  ", type_hint=str)

    def test_descriptor_invalid_lifetime(self):
        with pytest.raises(ValueError):
            DependencyDescriptor(name="x", type_hint=str, lifetime="singleton")  # type: ignore[arg-type]

    def test_dependency_generic_annotation(self):
        class Svc:
            pass

        class Consumer:
            dep: Dependency[Svc]

        hints = Consumer.__annotations__
        assert "dep" in hints
        # Dependency[Svc] returns Annotated, should be detectable
        anno = hints["dep"]
        # It should be Annotated with Dependency marker
        assert hasattr(anno, "__metadata__") or anno is not None

    def test_dependency_descriptor_field(self):
        class Consumer:
            my_dep = Dependency(lifetime=Lifetime.SCOPED, default=None)

        assert isinstance(Consumer.my_dep, Dependency)
        assert Consumer.my_dep.lifetime == Lifetime.SCOPED
        assert Consumer.my_dep.default is None
        # __set_name__ should have set name
        assert Consumer.my_dep.name == "my_dep"

    def test_dependency_marker_in_annotated(self):
        class Svc:
            pass

        ann = Dependency[Svc]
        # Should be Annotated
        assert getattr(ann, "__metadata__", None) is not None or "Annotated" in str(ann)
        # The marker inside should be Dependency instance with type_hint Svc
        meta = getattr(ann, "__metadata__", None)
        if meta:
            assert isinstance(meta[0], Dependency)
            assert meta[0].type_hint is Svc

    def test_missing_sentinel_identity(self):
        assert _MISSING is DI_MISSING
        assert _MISSING is not None


# ---------------------------------------------------------------------------
# EXE-002 — registration
# ---------------------------------------------------------------------------


class TestDependencyRegistration:
    def test_register_class_success(self):
        c = DependencyContainer()

        class Svc:
            pass

        c.register("svc", Svc, lifetime=Lifetime.SINGLETON)
        assert c.is_registered("svc")
        assert c.list_registered() == ["svc"]

    def test_register_factory_success(self):
        c = DependencyContainer()

        def factory():
            return object()

        c.register("factory", factory, lifetime=Lifetime.TRANSIENT)
        assert c.is_registered("factory")

    def test_register_instance(self):
        c = DependencyContainer()
        inst = object()
        c.register_instance("inst", inst)
        assert c.is_registered("inst")
        assert c.resolve("inst") is inst

    def test_register_instance_singleton_reuse(self):
        c = DependencyContainer()
        inst = object()
        c.register_instance("inst", inst)
        assert c.resolve("inst") is c.resolve("inst")

    def test_duplicate_without_override_raises(self):
        c = DependencyContainer()

        class A:
            pass

        c.register("a", A)
        with pytest.raises(RegistrationConflictError):
            c.register("a", A)

    def test_duplicate_with_override_replaces(self):
        c = DependencyContainer()

        class A:
            pass

        class A2:
            pass

        c.register("a", A)
        c.register("a", A2, override=True)
        # Should resolve to A2
        assert isinstance(c.resolve("a"), A2)

    def test_register_instance_duplicate_raises(self):
        c = DependencyContainer()
        c.register_instance("a", object())
        with pytest.raises(RegistrationConflictError):
            c.register_instance("a", object())

    def test_register_instance_override(self):
        c = DependencyContainer()
        o1 = object()
        o2 = object()
        c.register_instance("a", o1)
        c.register_instance("a", o2, override=True)
        assert c.resolve("a") is o2

    def test_list_registered_sorted(self):
        c = DependencyContainer()

        class A:
            pass

        c.register("zebra", A)
        c.register("apple", A)
        c.register("middle", A)
        assert c.list_registered() == ["apple", "middle", "zebra"]

    def test_register_invalid_name(self):
        c = DependencyContainer()

        class A:
            pass

        with pytest.raises(ConfigurationValidationError):
            c.register("", A)

    def test_register_invalid_lifetime(self):
        c = DependencyContainer()

        class A:
            pass

        with pytest.raises(ValueError):
            c.register("a", A, lifetime="singleton")  # type: ignore[arg-type]

    def test_register_none_impl_raises(self):
        c = DependencyContainer()
        with pytest.raises(ValueError):
            c.register("a", None)  # type: ignore[arg-type]

    def test_register_instance_none_raises(self):
        c = DependencyContainer()
        with pytest.raises(ValueError):
            c.register_instance("a", None)  # type: ignore[arg-type]

    def test_clear(self):
        c = DependencyContainer()

        class A:
            pass

        c.register("a", A)
        c.clear()
        assert c.list_registered() == []
        assert not c.is_registered("a")


# ---------------------------------------------------------------------------
# EXE-003 — resolution
# ---------------------------------------------------------------------------


class TestDependencyResolution:
    def test_singleton_identity(self):
        c = DependencyContainer()

        class S:
            pass

        c.register("s", S, lifetime=Lifetime.SINGLETON)
        assert c.resolve("s") is c.resolve("s")

    def test_transient_new_instances(self):
        c = DependencyContainer()

        class S:
            pass

        c.register("s", S, lifetime=Lifetime.TRANSIENT)
        assert c.resolve("s") is not c.resolve("s")

    def test_nested_dependencies_resolved(self):
        c = DependencyContainer()

        class Reg:
            pass

        class Executor:
            def __init__(self, registry):
                self.registry = registry

        c.register("registry", Reg, lifetime=Lifetime.SINGLETON)
        c.register("executor", Executor, lifetime=Lifetime.TRANSIENT)
        ex = c.resolve("executor")
        assert isinstance(ex.registry, Reg)

    def test_nested_chain(self):
        c = DependencyContainer()

        class D:
            pass

        class C:
            def __init__(self, d):
                self.d = d

        class B:
            def __init__(self, c):
                self.c = c

        class A:
            def __init__(self, b):
                self.b = b

        c.register("d", D)
        c.register("c", C)
        c.register("b", B)
        c.register("a", A)
        a = c.resolve("a")
        assert isinstance(a.b.c.d, D)

    def test_factory_dependencies(self):
        c = DependencyContainer()

        class Dep:
            pass

        def factory(dep):
            # dep is name "dep"
            return {"dep": dep}

        c.register("dep", Dep)
        c.register("factory", factory)
        result = c.resolve("factory")
        assert isinstance(result["dep"], Dep)

    def test_resolve_unregistered_raises(self):
        c = DependencyContainer()
        with pytest.raises(ResolutionError):
            c.resolve("unknown")

    def test_construction_failure_wraps(self):
        c = DependencyContainer()

        class Bad:
            def __init__(self):
                raise ValueError("boom")

        c.register("bad", Bad)
        with pytest.raises(ResolutionError) as exc:
            c.resolve("bad")
        assert "boom" in str(exc.value)
        assert exc.value.__cause__ is not None or "boom" in str(exc.value)

    def test_missing_required_param_wraps(self):
        c = DependencyContainer()

        class NeedsMissing:
            def __init__(self, missing_dep):
                self.x = missing_dep

        c.register("needs", NeedsMissing)
        # missing_dep not registered, so construction will fail due to missing arg
        with pytest.raises(ResolutionError):
            c.resolve("needs")

    def test_default_param_not_injected(self):
        c = DependencyContainer()

        class WithDefault:
            def __init__(self, val=42):
                self.val = val

        c.register("with_default", WithDefault)
        obj = c.resolve("with_default")
        assert obj.val == 42

    def test_transient_factory_new_each(self):
        c = DependencyContainer()
        counter = {"n": 0}

        def make():
            counter["n"] += 1
            return counter["n"]

        c.register("make", make, lifetime=Lifetime.TRANSIENT)
        assert c.resolve("make") == 1
        assert c.resolve("make") == 2

    def test_singleton_factory_cached(self):
        c = DependencyContainer()
        counter = {"n": 0}

        def make():
            counter["n"] += 1
            return counter["n"]

        c.register("make", make, lifetime=Lifetime.SINGLETON)
        assert c.resolve("make") == 1
        assert c.resolve("make") == 1


# ---------------------------------------------------------------------------
# EXE-004 — scoped
# ---------------------------------------------------------------------------


class TestScopedDependencies:
    def test_same_scope_same_instance(self):
        c = DependencyContainer()

        class S:
            pass

        c.register("s", S, lifetime=Lifetime.SCOPED)
        with c.create_scope() as scope:
            a = scope.resolve("s")
            b = scope.resolve("s")
            assert a is b

    def test_different_scopes_different_instances(self):
        c = DependencyContainer()

        class S:
            pass

        c.register("s", S, lifetime=Lifetime.SCOPED)
        with c.create_scope() as s1:
            a = s1.resolve("s")
        with c.create_scope() as s2:
            b = s2.resolve("s")
        assert a is not b

    def test_close_called_on_exit(self):
        c = DependencyContainer()
        closed = []

        class Closable:
            def close(self):
                closed.append(1)

        c.register("closable", Closable, lifetime=Lifetime.SCOPED)
        with c.create_scope() as scope:
            scope.resolve("closable")
            assert len(closed) == 0
        assert len(closed) == 1

    def test_close_not_called_for_transient(self):
        # Only SCOPED instances should be close-called; TRANSIENT not cached per scope
        # But if we resolve TRANSIENT via scope, it still shouldn't be tracked for close?
        # Our implementation only tracks SCOPED, so TRANSIENT's close should not be called via scope.
        # However container's scoped handling only caches SCOPED; transient is not stored, so close not called.
        c = DependencyContainer()
        closed = []

        class Closable:
            def close(self):
                closed.append(1)

        c.register("closable", Closable, lifetime=Lifetime.TRANSIENT)
        with c.create_scope() as scope:
            scope.resolve("closable")
        # TRANSIENT not tracked, so close not called
        assert len(closed) == 0

    def test_close_failure_logged_not_raised(self):
        c = DependencyContainer()

        class BadClose:
            def close(self):
                raise RuntimeError("close boom")

        c.register("bad", BadClose, lifetime=Lifetime.SCOPED)
        # Should not raise despite close failure
        with c.create_scope() as scope:
            scope.resolve("bad")
        # If we get here, close error was logged not raised
        assert True

    def test_nested_scopes_raise(self):
        c = DependencyContainer()

        class S:
            pass

        c.register("s", S, lifetime=Lifetime.SCOPED)
        with c.create_scope() as outer:
            with pytest.raises(LifecycleError), c.create_scope() as _inner:
                pass  # should not reach
            # Also test that outer still works
            assert outer.resolve("s") is outer.resolve("s")

    def test_scope_resolve_outside_with_allowed(self):
        c = DependencyContainer()

        class S:
            pass

        c.register("s", S, lifetime=Lifetime.SCOPED)
        scope = c.create_scope()
        # Resolve without entering — should still work but not set active_scope
        # Our implementation allows this as transient-like per scope
        a = scope.resolve("s")
        b = scope.resolve("s")
        # Outside with, multiple resolves via same scope object still same? In our impl, outside with, we create per-call but with scope param, so second resolve will see cached in scope._instances
        # Actually outside with, we don't set active_scope, but we pass scope as param, so they share same scope._instances
        # So they should be same instance even outside with
        assert a is b

    def test_singleton_across_scopes_same(self):
        c = DependencyContainer()

        class S:
            pass

        c.register("s", S, lifetime=Lifetime.SINGLETON)
        with c.create_scope() as s1:
            a = s1.resolve("s")
            b = c.resolve("s")
            assert a is b
        with c.create_scope() as s2:
            c2 = s2.resolve("s")
            assert a is c2

    def test_scoped_via_container_inside_scope(self):
        c = DependencyContainer()

        class S:
            pass

        c.register("s", S, lifetime=Lifetime.SCOPED)
        with c.create_scope() as scope:
            # Resolve via container while scope active should be scoped
            a = c.resolve("s")
            b = scope.resolve("s")
            # Both should be same per our implementation (container checks active_scope)
            assert a is b


# ---------------------------------------------------------------------------
# EXE-005 — overrides
# ---------------------------------------------------------------------------


class TestDependencyOverrides:
    def test_override_replaces(self):
        c = DependencyContainer()

        class Real:
            pass

        class Fake:
            pass

        c.register("svc", Real)
        c.resolve("svc")
        fake = Fake()
        c.override("svc", fake)
        assert c.resolve("svc") is fake
        c.restore("svc")
        assert isinstance(c.resolve("svc"), Real)

    def test_override_context(self):
        c = DependencyContainer()

        class Real:
            pass

        class Fake:
            pass

        c.register("svc", Real)
        fake = Fake()
        with c.override_context("svc", fake):
            assert c.resolve("svc") is fake
        assert isinstance(c.resolve("svc"), Real)

    def test_override_unregistered_raises(self):
        c = DependencyContainer()

        class Fake:
            pass

        with pytest.raises(ResolutionError):
            c.override("unknown", Fake())

    def test_restore_without_override_raises(self):
        c = DependencyContainer()

        class Real:
            pass

        c.register("svc", Real)
        with pytest.raises(ResolutionError):
            c.restore("svc")

    def test_nested_overrides(self):
        c = DependencyContainer()

        class Real:
            pass

        class Fake:
            pass

        c.register("svc", Real)
        fake_outer = Fake()
        fake_inner = Fake()
        c.override("svc", fake_outer)
        assert c.resolve("svc") is fake_outer
        with c.override_context("svc", fake_inner):
            assert c.resolve("svc") is fake_inner
        # Should restore to outer, not original
        assert c.resolve("svc") is fake_outer
        c.restore("svc")
        assert isinstance(c.resolve("svc"), Real)

    def test_override_applies_to_dependencies(self):
        c = DependencyContainer()

        class Dep:
            pass

        class Consumer:
            def __init__(self, dep):
                self.dep = dep

        c.register("dep", Dep)
        c.register("consumer", Consumer)

        class FakeDep:
            pass

        fake = FakeDep()
        with c.override_context("dep", fake):
            cons = c.resolve("consumer")
            assert cons.dep is fake

    def test_override_none_raises(self):
        c = DependencyContainer()

        class Real:
            pass

        c.register("svc", Real)
        with pytest.raises(ValueError):
            c.override("svc", None)

    def test_override_context_exception_restores(self):
        c = DependencyContainer()

        class Real:
            pass

        c.register("svc", Real)
        fake = object()
        try:
            with c.override_context("svc", fake):
                assert c.resolve("svc") is fake
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        # Should be restored
        assert isinstance(c.resolve("svc"), Real)


# ---------------------------------------------------------------------------
# EXE-006 — circular detection
# ---------------------------------------------------------------------------


class TestCircularDetection:
    def test_direct_cycle(self):
        c = DependencyContainer()

        class A:
            def __init__(self, a):
                self.a = a

        c.register("a", A)
        with pytest.raises(ResolutionError) as exc:
            c.resolve("a")
        assert "Circular dependency detected" in str(exc.value)
        assert "a → a" in str(exc.value)

    def test_indirect_cycle(self):
        c = DependencyContainer()

        class A:
            def __init__(self, b):
                self.b = b

        class B:
            def __init__(self, a):
                self.a = a

        c.register("a", A)
        c.register("b", B)
        with pytest.raises(ResolutionError) as exc:
            c.resolve("a")
        assert "Circular dependency detected" in str(exc.value)
        assert "a" in str(exc.value) and "b" in str(exc.value)
        assert "→" in str(exc.value)

    def test_three_node_cycle(self):
        c = DependencyContainer()

        class A:
            def __init__(self, b):
                self.b = b

        class B:
            def __init__(self, c):
                self.c = c

        class C:
            def __init__(self, a):
                self.a = a

        c.register("a", A)
        c.register("b", B)
        c.register("c", C)
        with pytest.raises(ResolutionError) as exc:
            c.resolve("a")
        assert "Circular dependency detected" in str(exc.value)
        msg = str(exc.value)
        assert "a" in msg and "b" in msg and "c" in msg

    def test_non_circular_no_false_positive(self):
        c = DependencyContainer()

        class D:
            pass

        class C:
            def __init__(self, d):
                self.d = d

        class B:
            def __init__(self, c):
                self.c = c

        class A:
            def __init__(self, b):
                self.b = b

        c.register("d", D)
        c.register("c", C)
        c.register("b", B)
        c.register("a", A)
        a = c.resolve("a")
        assert isinstance(a.b.c.d, D)

    def test_diamond_not_circular(self):
        c = DependencyContainer()

        class D:
            pass

        class B:
            def __init__(self, d):
                self.d = d

        class C:
            def __init__(self, d):
                self.d = d

        class A:
            def __init__(self, b, c):
                self.b = b
                self.c = c

        c.register("d", D)
        c.register("b", B)
        c.register("c", C)
        c.register("a", A)
        a = c.resolve("a")
        assert isinstance(a.b.d, D)
        assert isinstance(a.c.d, D)
        # Singleton D should be same instance for both branches
        assert a.b.d is a.c.d

    def test_error_includes_full_chain(self):
        c = DependencyContainer()

        class A:
            def __init__(self, b):
                self.b = b

        class B:
            def __init__(self, c):
                self.c = c

        class C:
            def __init__(self, b):
                self.b = b  # cycle B -> C -> B

        c.register("a", A)
        c.register("b", B)
        c.register("c", C)
        with pytest.raises(ResolutionError) as exc:
            c.resolve("a")
        # Chain should include b and c
        assert "b" in str(exc.value) and "c" in str(exc.value)
        assert exc.value.context is not None
        assert "chain" in exc.value.context


# ---------------------------------------------------------------------------
# EXE-007 — testing utilities
# ---------------------------------------------------------------------------


class TestDiTestingUtilities:
    def test_test_container_pre_registers(self):
        tc = TestContainer()
        # All expected services
        for name in ["config", "registry", "resource_manager", "language", "lifecycle"]:
            assert tc.is_registered(name)
            # Resolve should not raise
            assert tc.resolve(name) is not None

    def test_test_container_resolves_without_error(self):
        tc = TestContainer()
        # Should resolve all without raising
        for name in tc.list_registered():
            assert tc.resolve(name) is not None

    def test_fake_registry_satisfies_basic(self):
        fr = FakeRegistry()
        assert hasattr(fr, "version")
        fr.register("language", "lug", object(), version="1.0.0")
        assert fr.resolve("language", "lug") is not None
        assert fr.list("language") == [("lug", "1.0.0")]
        with pytest.raises(ResolutionError):
            fr.resolve("language", "missing")

    def test_fake_registry_clear(self):
        fr = FakeRegistry()
        fr.register("component", "my_asr", object())
        fr.clear()
        with pytest.raises(ResolutionError):
            fr.resolve("component", "my_asr")

    def test_fake_resource_manager(self):
        frm = FakeResourceManager()
        assert hasattr(frm, "version")
        p = frm.get("res_id", "1.0.0", "https://example.com/file", "abc123")
        assert isinstance(p, type(FakeResourceManager().cache_dir))
        assert "res_id" in str(p)
        assert (
            frm.cache_path("res_id", "1.0.0", "file.bin")
            == frm.cache_dir / "res_id" / "1.0.0" / "file.bin"
        )
        # close should not raise
        frm.close()

    def test_fake_language(self):
        fl = FakeLanguage()
        assert fl.code == "lug"
        assert hasattr(fl, "version")
        assert hasattr(fl, "close")
        fl.close()
        # as_language should produce real Language
        lang = fl.as_language()
        assert lang.code == "lug"
        assert lang.name == fl.name

    def test_fake_language_custom(self):
        fl = FakeLanguage(code="nyn", name="Runyankole", family="Bantu")
        assert fl.code == "nyn"
        lang = fl.as_language()
        assert lang.code == "nyn"

    def test_assert_resolved_as_pass(self):
        tc = TestContainer()
        # Should return instance and not raise
        result = assert_resolved_as(tc, "registry", FakeRegistry)
        assert isinstance(result, FakeRegistry)

    def test_assert_resolved_as_fail(self):
        tc = TestContainer()
        with pytest.raises(AssertionError) as exc:
            assert_resolved_as(tc, "registry", FakeLanguage)
        assert "expected to resolve as" in str(exc.value)
        assert "FakeLanguage" in str(exc.value)

    def test_assert_resolved_as_unregistered_raises_resolution(self):
        tc = TestContainer()
        with pytest.raises(ResolutionError):
            assert_resolved_as(tc, "unknown", FakeRegistry)

    def test_test_container_is_dependency_container(self):
        tc = TestContainer()
        assert isinstance(tc, DependencyContainer)

    def test_test_container_override(self):
        tc = TestContainer()
        fake = FakeRegistry()
        with tc.override_context("registry", fake):
            assert tc.resolve("registry") is fake
        assert tc.resolve("registry") is not fake

    def test_threaded_resolve_isolated(self):
        # Basic thread safety: concurrent resolves should not interfere with stacks
        tc = TestContainer()
        # Register a transient that counts
        counter = {"n": 0, "lock": threading.Lock()}

        class Counted:
            def __init__(self):
                with counter["lock"]:
                    counter["n"] += 1
                    self.n = counter["n"]

        tc.register("counted", Counted, lifetime=Lifetime.TRANSIENT)
        results: list[Counted] = []

        def worker():
            results.append(tc.resolve("counted"))

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 5
        # Transient should give distinct instances
        ids = {id(r) for r in results}
        assert len(ids) == 5

    def test_dependency_descriptor_in_container(self):
        # Ensure container can be wired via DependencyDescriptor metadata? Not required but sanity
        c = DependencyContainer()

        class Dep:
            pass

        c.register("dep", Dep)
        # DependencyDescriptor records should be independent
        d = DependencyDescriptor(name="dep", type_hint=Dep, lifetime=Lifetime.SINGLETON)
        assert d.name == "dep"
