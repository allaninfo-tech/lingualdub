# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Regression tests for public API surface — REL-006.

Ensures ``lingualdub.__all__`` does not change without an explicit snapshot update.
Renaming or removing a public symbol will cause this test to fail.
"""

from __future__ import annotations

import json
from pathlib import Path

import lingualdub


def _load_snapshot() -> dict:
    snap = Path(__file__).parent / "snapshots" / "public_api_surface.json"
    if not snap.exists():
        raise FileNotFoundError(f"Snapshot missing: {snap}. Run snapshot generation.")
    return json.loads(snap.read_text(encoding="utf-8"))


def test_public_api_surface_matches_snapshot():
    snapshot = _load_snapshot()
    expected = snapshot["__all__"]
    actual = sorted(lingualdub.__all__)
    # Compare as sets first for clearer diff, then order
    if actual != sorted(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise AssertionError(
            f"Public API surface mismatch.\n"
            f"  Missing from code (in snapshot but not in __all__): {missing}\n"
            f"  Extra in code (in __all__ but not in snapshot): {extra}\n"
            f"  Expected ({len(expected)}): {expected}\n"
            f"  Actual ({len(actual)}): {actual}\n"
            f"To accept an intentional change, update snapshot: tests/regression/snapshots/public_api_surface.json"
        )


def test_public_api_snapshot_is_sorted():
    snapshot = _load_snapshot()
    expected = snapshot["__all__"]
    assert expected == sorted(expected), "Snapshot __all__ should be sorted for determinism"


def test_public_api_version_matches_snapshot():
    snapshot = _load_snapshot()
    assert snapshot.get("version") == lingualdub.__version__, (
        f"Version mismatch snapshot {snapshot.get('version')!r} vs code {lingualdub.__version__!r}. "
        "Update snapshot when bumping version."
    )


def test_all_symbols_importable():
    # Duplicate of core test but kept as regression gate
    missing = [name for name in lingualdub.__all__ if not hasattr(lingualdub, name)]
    assert missing == [], f"Snapshot symbols not importable: {missing}"
