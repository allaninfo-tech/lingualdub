# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Adaptation components.

This package contains the base interface for adaptation components and any
built-in implementations shipped with the framework. Third-party adaptation
implementations are registered through the extension manifest system
and do not need to live in this package.
"""

from lingualdub.components.adaptation.base import AdaptationComponent

__all__: list[str] = [
    "AdaptationComponent",
]
