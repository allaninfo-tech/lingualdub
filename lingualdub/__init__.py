"""
LingualDub — Low-Resource Speech AI Framework.

A composable, registry-based framework for building, adapting, composing,
and evaluating speech-AI systems for low-resource languages.
"""

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.language import Language
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result, ResultStatus
from lingualdub.core.segment import Segment
from lingualdub.pipeline.executor import PipelineExecutionError, PipelineExecutor
from lingualdub.registry.manifest import ManifestError, ManifestScanner
from lingualdub.registry.registry import ConflictPolicy, Registry, RegistryError
from lingualdub.utils.provenance import make_provenance, make_run_id
from lingualdub.utils.resource_manager import (
    ChecksumError,
    ResourceManager,
    ResourceNotFoundError,
)

__version__ = "0.1.0-dev"

__all__ = [
    "__version__",
    # Core Abstractions
    "Language",
    "Resource",
    "ResourceKind",
    "Component",
    "ComponentTask",
    "FailureMode",
    "Pipeline",
    "Result",
    "ResultStatus",
    "Segment",
    # Pipeline & Execution
    "PipelineExecutor",
    "PipelineExecutionError",
    # Registry & Discovery
    "Registry",
    "RegistryError",
    "ConflictPolicy",
    "ManifestScanner",
    "ManifestError",
    # Utilities
    "ResourceManager",
    "ChecksumError",
    "ResourceNotFoundError",
    "make_run_id",
    "make_provenance",
]
