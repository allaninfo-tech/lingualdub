# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Eval components.

This package contains the base interface for eval components and any
built-in implementations shipped with the framework. Third-party eval
implementations are registered through the extension manifest system
and do not need to live in this package.
"""

from lingualdub.components.eval.av_sync import AVSyncEvaluator
from lingualdub.components.eval.base import EvaluatorComponent

__all__: list[str] = [
    "EvaluatorComponent",
    "AVSyncEvaluator",
]
