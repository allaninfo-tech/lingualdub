# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""Dependency injection package — contracts and container."""

from lingualdub.di.container import DependencyContainer, DependencyScope
from lingualdub.di.contracts import _MISSING, Dependency, DependencyDescriptor, Lifetime

__all__ = [
    "DependencyContainer",
    "DependencyScope",
    "DependencyDescriptor",
    "Lifetime",
    "Dependency",
    "_MISSING",
]
