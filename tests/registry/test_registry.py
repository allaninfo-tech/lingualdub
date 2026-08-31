"""Tests for lingualdub.registry.registry."""

import pytest
from lingualdub.registry.registry import Registry, ConflictPolicy, RegistryError


def test_registry_register_and_resolve():
    reg = Registry()
    reg.register("component", "my_asr", object, version="1.0.0")
    resolved = reg.resolve("component", "my_asr")
    assert resolved is object


def test_registry_resolve_latest():
    reg = Registry()
    reg.register("component", "my_asr", str, version="1.0.0")
    reg.register("component", "my_asr", int, version="2.0.0")
    resolved = reg.resolve("component", "my_asr")
    assert resolved is int


def test_registry_resolve_by_version():
    reg = Registry()
    reg.register("component", "my_asr", str, version="1.0.0")
    reg.register("component", "my_asr", int, version="2.0.0")
    assert reg.resolve("component", "my_asr", version="1.0.0") is str
    assert reg.resolve("component", "my_asr", version="2.0.0") is int


def test_registry_resolve_missing_raises():
    reg = Registry()
    with pytest.raises(RegistryError):
        reg.resolve("component", "nonexistent")


def test_registry_resolve_wrong_version_raises():
    reg = Registry()
    reg.register("component", "my_asr", str, version="1.0.0")
    with pytest.raises(RegistryError):
        reg.resolve("component", "my_asr", version="9.9.9")


def test_registry_list():
    reg = Registry()
    reg.register("component", "asr", str, version="1.0.0")
    reg.register("component", "tts", int, version="2.0.0")
    entries = reg.list("component")
    keys = [k for k, _ in entries]
    assert "asr" in keys
    assert "tts" in keys
    assert entries == sorted(entries)


def test_registry_list_empty():
    reg = Registry()
    assert reg.list("component") == []


def test_registry_conflict_namespaced_keeps_both():
    reg = Registry(conflict_policy=ConflictPolicy.NAMESPACED)
    reg.register("component", "asr", str, version="1.0.0")
    reg.register("component", "asr", int, version="1.0.0")
    # Both entries exist; resolve returns the last registered
    resolved = reg.resolve("component", "asr")
    assert resolved is int


def test_registry_conflict_explicit_raises():
    reg = Registry(conflict_policy=ConflictPolicy.EXPLICIT)
    reg.register("component", "asr", str, version="1.0.0")
    with pytest.raises(RegistryError):
        reg.register("component", "asr", int, version="2.0.0")


def test_registry_multiple_kinds():
    reg = Registry()
    reg.register("language", "lug", {"name": "Luganda"}, version="1.0.0")
    reg.register("component", "asr", str, version="1.0.0")
    assert reg.resolve("language", "lug") == {"name": "Luganda"}
    assert reg.resolve("component", "asr") is str


def test_registry_repr():
    reg = Registry()
    reg.register("component", "asr", str, version="1.0.0")
    r = repr(reg)
    assert "namespaced" in r
    assert "asr" in r


def test_registry_conflict_highest_version_wins():
    reg = Registry(conflict_policy=ConflictPolicy.HIGHEST_VERSION)
    reg.register("component", "asr", str, version="1.0.0")
    reg.register("component", "asr", int, version="2.0.0")
    # int (2.0.0) is higher, should be returned
    assert reg.resolve("component", "asr") is int


def test_registry_conflict_highest_version_lower_ignored():
    reg = Registry(conflict_policy=ConflictPolicy.HIGHEST_VERSION)
    reg.register("component", "asr", int, version="2.0.0")
    reg.register("component", "asr", str, version="1.0.0")
    # str (1.0.0) is lower; int (2.0.0) must stay
    assert reg.resolve("component", "asr") is int
