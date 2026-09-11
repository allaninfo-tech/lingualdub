# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for explicit public API boundaries.

Verifies that:
1. ``lingualdub.__all__`` is non-empty and consistent with actual exports.
2. Every symbol declared in ``__all__`` can be imported without error.
3. ``lingualdub/PUBLIC_API.md`` exists and is non-empty.
4. Every subpackage with an ``__all__`` exposes only what it declares.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import lingualdub

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SUBPACKAGES = [
    "lingualdub.components",
    "lingualdub.components.adaptation",
    "lingualdub.components.asr",
    "lingualdub.components.eval",
    "lingualdub.components.speaker",
    "lingualdub.components.translation",
    "lingualdub.components.tts",
    "lingualdub.core",
    "lingualdub.languages",
    "lingualdub.pipeline",
    "lingualdub.registry",
    "lingualdub.utils",
]


# ---------------------------------------------------------------------------
# Top-level package
# ---------------------------------------------------------------------------


class TestTopLevelPackage:
    def test_all_is_defined(self) -> None:
        assert hasattr(lingualdub, "__all__"), "lingualdub must define __all__"

    def test_all_is_non_empty(self) -> None:
        assert len(lingualdub.__all__) > 0, "lingualdub.__all__ must not be empty"

    def test_all_symbols_are_importable(self) -> None:
        missing = [name for name in lingualdub.__all__ if not hasattr(lingualdub, name)]
        assert missing == [], f"Symbols in __all__ not accessible on lingualdub: {missing}"

    def test_no_private_symbols_in_all(self) -> None:
        # Dunder names (e.g. __version__) are conventional public package
        # metadata and are explicitly allowed in __all__.
        private = [
            name
            for name in lingualdub.__all__
            if name.startswith("_") and not (name.startswith("__") and name.endswith("__"))
        ]
        assert private == [], f"Private symbols must not appear in __all__: {private}"


# ---------------------------------------------------------------------------
# PUBLIC_API.md
# ---------------------------------------------------------------------------


class TestPublicApiDoc:
    def test_public_api_md_exists(self) -> None:
        pkg_dir = Path(lingualdub.__file__).parent
        doc = pkg_dir / "PUBLIC_API.md"
        assert doc.exists(), "lingualdub/PUBLIC_API.md must exist"

    def test_public_api_md_non_empty(self) -> None:
        pkg_dir = Path(lingualdub.__file__).parent
        doc = pkg_dir / "PUBLIC_API.md"
        assert doc.stat().st_size > 0, "lingualdub/PUBLIC_API.md must not be empty"


# ---------------------------------------------------------------------------
# Subpackage __all__ consistency
# ---------------------------------------------------------------------------


class TestSubpackageAllConsistency:
    def test_subpackages_define_all(self) -> None:
        missing_all = []
        for pkg in SUBPACKAGES:
            mod = importlib.import_module(pkg)
            if not hasattr(mod, "__all__"):
                missing_all.append(pkg)
        assert missing_all == [], f"Subpackages missing __all__: {missing_all}"

    def test_subpackage_all_symbols_accessible(self) -> None:
        failures: list[str] = []
        for pkg in SUBPACKAGES:
            mod = importlib.import_module(pkg)
            declared = getattr(mod, "__all__", [])
            for sym in declared:
                if not hasattr(mod, sym):
                    failures.append(f"{pkg}.{sym}")
        assert failures == [], f"Declared __all__ symbols not accessible: {failures}"

    def test_subpackage_all_no_private_symbols(self) -> None:
        private: list[str] = []
        for pkg in SUBPACKAGES:
            mod = importlib.import_module(pkg)
            declared = getattr(mod, "__all__", [])
            for sym in declared:
                if sym.startswith("_"):
                    private.append(f"{pkg}.{sym}")
        assert private == [], f"Private symbols in __all__: {private}"
