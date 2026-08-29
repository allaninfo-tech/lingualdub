"""Tests for lingualdub.registry."""

import pytest
from lingualdub.registry import Registry
from lingualdub.registry.registry import ConflictPolicy, RegistryError


def test_register_and_resolve():
    reg = Registry()
    reg.register("component", "my_asr", object, version="1.0.0")
    impl = reg.resolve("component", "my_asr")
    assert impl is object


def test_resolve_specific_version():
    reg = Registry()
    reg.register("component", "my_asr", str, version="1.0.0")
    reg.register("component", "my_asr", int, version="2.0.0")
    assert reg.resolve("component", "my_asr", version="1.0.0") is str
    assert reg.resolve("component", "my_asr", version="2.0.0") is int


def test_resolve_latest():
    reg = Registry()
    reg.register("component", "my_asr", str, version="1.0.0")
    reg.register("component", "my_asr", int, version="2.0.0")
    assert reg.resolve("component", "my_asr") is int


def test_resolve_missing_raises():
    reg = Registry()
    with pytest.raises(RegistryError):
        reg.resolve("component", "nonexistent")


def test_explicit_conflict_policy():
    reg = Registry(conflict_policy=ConflictPolicy.EXPLICIT)
    reg.register("component", "my_asr", str, version="1.0.0")
    with pytest.raises(RegistryError):
        reg.register("component", "my_asr", int, version="2.0.0")


def test_list():
    reg = Registry()
    reg.register("language", "lug", object, version="1.0.0")
    reg.register("language", "nyn", object, version="1.0.0")
    keys = [k for k, _ in reg.list("language")]
    assert "lug" in keys
    assert "nyn" in keys
