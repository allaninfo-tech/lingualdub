# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Core abstractions for LingualDub.

This module exposes the five foundational objects of the framework:
Language, Resource, Component, Pipeline, Result — and the shared
Segment representation that connects them.
"""

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.language import Language
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource, ResourceKind, ResourceOwnership
from lingualdub.core.result import Result, ResultStatus
from lingualdub.core.segment import Segment

__all__ = [
    "Language",
    "Resource",
    "ResourceKind",
    "ResourceOwnership",
    "Component",
    "ComponentTask",
    "FailureMode",
    "Segment",
    "Result",
    "ResultStatus",
    "Pipeline",
]
