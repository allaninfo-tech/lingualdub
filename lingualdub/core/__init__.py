"""
Core abstractions for LingualDub.

This module exposes the five foundational objects of the framework:
Language, Resource, Component, Pipeline, Result — and the shared
Segment representation that connects them.
"""

from lingualdub.core.language import Language
from lingualdub.core.resource import Resource
from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.segment import Segment
from lingualdub.core.result import Result, ResultStatus
from lingualdub.core.pipeline import Pipeline

__all__ = [
    "Language",
    "Resource",
    "Component",
    "ComponentTask",
    "FailureMode",
    "Segment",
    "Result",
    "ResultStatus",
    "Pipeline",
]
