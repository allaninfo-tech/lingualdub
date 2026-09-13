# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""Benchmarks for Registry.resolve() — PEV-003."""

from __future__ import annotations

import pytest

from lingualdub.registry.registry import Registry


@pytest.mark.parametrize("size", [100, 1000, 10000])
def test_bench_registry_resolve(benchmark, size):
    """Benchmark Registry.resolve at 100/1000/10000 entries."""

    def setup():
        reg = Registry()
        for i in range(size):
            reg.register("component", f"comp_{i}", object(), version="1.0.0")
        return reg

    reg = setup()

    def resolve():
        reg.resolve("component", f"comp_{size // 2}")

    benchmark(resolve)


def test_bench_registry_resolve_100(benchmark):
    reg = Registry()
    for i in range(100):
        reg.register("component", f"comp_{i}", object(), version="1.0.0")
    benchmark(lambda: reg.resolve("component", "comp_50"))


def test_bench_registry_resolve_1000(benchmark):
    reg = Registry()
    for i in range(1000):
        reg.register("component", f"comp_{i}", object(), version="1.0.0")
    benchmark(lambda: reg.resolve("component", "comp_500"))


def test_bench_registry_resolve_10000(benchmark):
    reg = Registry()
    for i in range(10000):
        reg.register("component", f"comp_{i}", object(), version="1.0.0")
    benchmark(lambda: reg.resolve("component", "comp_5000"))
