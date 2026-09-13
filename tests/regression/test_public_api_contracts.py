# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Regression tests for public API contracts — REL-006.

For each major public class, the constructor parameter names, defaults, and
key method signatures are snapshotted. Renaming a parameter or removing a
method causes an immediate failure.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import lingualdub  # noqa: F401 — ensure top-level import works


def _load_snapshot() -> dict:
    snap = Path(__file__).parent / "snapshots" / "public_api_contracts.json"
    if not snap.exists():
        raise FileNotFoundError(f"Snapshot missing: {snap}. Generate it.")
    return json.loads(snap.read_text(encoding="utf-8"))


# Mapping from snapshot key to actual class — kept in sync with snapshot generation
TARGETS = {
    "Language": "lingualdub.core.language:Language",
    "Resource": "lingualdub.core.resource:Resource",
    "Segment": "lingualdub.core.segment:Segment",
    "Result": "lingualdub.core.result:Result",
    "Pipeline": "lingualdub.core.pipeline:Pipeline",
    "Component": "lingualdub.core.component:Component",
    "Registry": "lingualdub.registry.registry:Registry",
    "FrameworkConfig": "lingualdub.config:FrameworkConfig",
    "FrameworkLifecycle": "lingualdub.lifecycle:FrameworkLifecycle",
    "DependencyContainer": "lingualdub.di.container:DependencyContainer",
    "PipelineExecutor": "lingualdub.pipeline.executor:PipelineExecutor",
    "ResourceManager": "lingualdub.utils.resource_manager:ResourceManager",
}


def _resolve_target(dotted: str):  # type: ignore[no-untyped-def]
    mod_name, attr = dotted.split(":")
    import importlib

    mod = importlib.import_module(mod_name)
    return getattr(mod, attr)


def _param_names(cls):  # type: ignore[no-untyped-def]
    try:
        sig = inspect.signature(cls)
        return [name for name, p in sig.parameters.items() if name not in ("self", "cls")]
    except Exception:
        return []


def test_contracts_match_snapshot():
    snapshot = _load_snapshot()
    for name, dotted in TARGETS.items():
        if name not in snapshot:
            raise AssertionError(f"Snapshot missing entry for {name!r}; update snapshot.")
        expected = snapshot[name]
        cls = _resolve_target(dotted)
        actual_params = _param_names(cls)
        exp_params = expected.get("params", [])
        if actual_params != exp_params:
            raise AssertionError(
                f"Constructor params mismatch for {name} ({dotted}).\n"
                f"  Expected (snapshot): {exp_params!r}\n"
                f"  Actual (code):       {actual_params!r}\n"
                f"If intentional, update snapshot: tests/regression/snapshots/public_api_contracts.json"
            )
        # Check that defaults keys match (not exact repr of factories)
        try:
            sig = inspect.signature(cls)
            actual_defaults = {n for n, p in sig.parameters.items() if p.default is not inspect.Parameter.empty and n not in ("self", "cls")}
            exp_defaults = set(expected.get("defaults", {}).keys())
            if actual_defaults != exp_defaults:
                raise AssertionError(
                    f"Defaulted params mismatch for {name}.\n"
                    f"  Expected defaults keys: {sorted(exp_defaults)!r}\n"
                    f"  Actual defaults keys:   {sorted(actual_defaults)!r}"
                )
        except Exception as exc:
            # If signature inspection fails, report
            raise AssertionError(f"Could not inspect defaults for {name}: {exc}") from exc
        # Check method param snapshots where present
        for key, exp_m_params in list(expected.items()):
            if key.startswith("method_"):
                method = key[len("method_") :].rsplit("_params", 1)[0]
                obj = getattr(cls, method, None)
                if obj is None or not callable(obj):
                    raise AssertionError(f"Expected method {cls.__name__}.{method} missing (snapshot has {key!r})")
                sig = inspect.signature(obj)
                actual_m = [n for n in sig.parameters.keys() if n not in ("self", "cls")]
                if actual_m != exp_m_params:
                    raise AssertionError(
                        f"Method {cls.__name__}.{method} params mismatch.\n"
                        f"  Expected: {exp_m_params!r}\n"
                        f"  Actual:   {actual_m!r}"
                    )


def test_contract_renaming_is_detected_example():
    """Meta-test: intentionally renaming a param would be caught.

    We simulate by checking that Resource has 'language' not 'lang_code'.
    """
    snapshot = _load_snapshot()
    res_params = snapshot.get("Resource", {}).get("params", [])
    assert "language" in res_params, "Snapshot should contain 'language' for Resource"
    assert "lang_code" not in res_params, "Snapshot must not contain renamed 'lang_code' — renaming would break contract"
    # Also verify live code still has 'language'
    from lingualdub.core.resource import Resource

    assert "language" in _param_names(Resource)
