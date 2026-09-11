# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
LingualDub — Low-Resource Speech AI Framework.

A composable, registry-based framework for building, adapting, composing,
and evaluating speech-AI systems for low-resource languages.
"""

from lingualdub.config import FrameworkConfig, load_config
from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.language import Language
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.protocols import ComponentProtocol, EvaluatorProtocol, RegistrableProtocol
from lingualdub.core.resource import Resource, ResourceKind
from lingualdub.core.result import Result, ResultStatus
from lingualdub.core.segment import Segment
from lingualdub.exceptions import (
    ComponentContractError,
    ComponentError,
    ConfigurationError,
    ConfigurationValidationError,
    ConsentViolationError,
    InitializationError,
    InternalError,
    LifecycleError,
    LingualDubError,
    PipelineError,
    RegistrationConflictError,
    ResolutionError,
    ResourceError,
    ResourceLoadError,
    ShutdownError,
    StageCompatibilityError,
    StageExecutionError,
)
from lingualdub.pipeline.config_loader import ConfigLoader
from lingualdub.pipeline.executor import PipelineExecutionError, PipelineExecutor
from lingualdub.registry.manifest import ManifestError, ManifestScanner
from lingualdub.registry.registry import ConflictPolicy, Registry, RegistryError
from lingualdub.types import (
    AudioTensor,
    LanguageCode,
    MetadataDict,
    PathLike,
    ProvenanceDict,
    TimestampInterval,
)
from lingualdub.utils.comparison import ProvenanceMismatchError, compare_runs
from lingualdub.utils.provenance import make_provenance, make_run_id
from lingualdub.utils.resource_manager import (
    ChecksumError,
    ResourceManager,
    ResourceNotFoundError,
)

__version__ = "0.1.0"

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
    # Protocols (structural contracts)
    "ComponentProtocol",
    "EvaluatorProtocol",
    "RegistrableProtocol",
    # Centralized Types
    "LanguageCode",
    "MetadataDict",
    "ProvenanceDict",
    "PathLike",
    "AudioTensor",
    "TimestampInterval",
    # Configuration
    "FrameworkConfig",
    "load_config",
    # Pipeline & Execution
    "PipelineExecutor",
    "PipelineExecutionError",
    "ConfigLoader",
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
    "compare_runs",
    "ProvenanceMismatchError",
    # Exception Hierarchy
    "LingualDubError",
    "ConfigurationError",
    "ConfigurationValidationError",
    "LifecycleError",
    "InitializationError",
    "ShutdownError",
    "PipelineError",
    "StageCompatibilityError",
    "StageExecutionError",
    "RegistrationConflictError",
    "ResolutionError",
    "ComponentError",
    "ComponentContractError",
    "ResourceError",
    "ResourceLoadError",
    "ConsentViolationError",
    "InternalError",
]
