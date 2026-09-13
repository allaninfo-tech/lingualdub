# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""Benchmarks for DependencyContainer — PEV-003."""

from __future__ import annotations

import pytest

from lingualdub.di import DependencyContainer, Lifetime


def _build_deep_chain(n: int = 10) -> DependencyContainer:
    container = DependencyContainer()

    # Create chain: level_0 depends on level_1, etc.
    for i in range(n):
        name = f"level_{i}"
        next_name = f"level_{i + 1}" if i + 1 < n else None

        if next_name is None:
            # Leaf — no deps

            class Leaf:
                def __init__(self):  # noqa: B027
                    pass

            container.register(name, Leaf, lifetime=Lifetime.TRANSIENT)
        else:

            def make_factory(dep_name: str):  # type: ignore[no-untyped-def]
                class Node:
                    def __init__(self, **kwargs):  # noqa: B027
                        # kwargs will contain dep_name if registered
                        self.dep = kwargs.get(dep_name)

                # Set __init__ signature to include dep_name
                # Use exec to create proper signature dynamically
                # Simpler: create factory that manually resolves
                # Instead, use closure and inspect will see dep_name param
                Node.__init__ = eval(
                    f"lambda self, {dep_name}=None: setattr(self, 'dep', {dep_name})"
                )  # type: ignore[assignment]
                return Node

            # For simplicity, register a factory that depends on next level via parameter name
            # Use a dummy class with correct param name via exec
            code = f"""
class Level{i}:
    def __init__(self, {next_name}=None):
        self.dep = {next_name}
"""
            ns: dict = {}
            exec(code, {}, ns)
            LevelCls = ns[f"Level{i}"]
            container.register(name, LevelCls, lifetime=Lifetime.TRANSIENT)

    return container


def test_bench_di_deep_10(benchmark):
    container = _build_deep_chain(10)
    benchmark(lambda: container.resolve("level_0"))


@pytest.mark.parametrize("depth", [5, 10, 15])
def test_bench_di_chain(benchmark, depth):
    container = _build_deep_chain(depth)
    benchmark(lambda: container.resolve("level_0"))
