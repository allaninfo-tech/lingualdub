# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the centralized exception hierarchy (lingualdub/exceptions.py).

Verifies:
1. Every exception is importable from lingualdub (top-level).
2. Every exception is a subclass of the expected parent.
3. Each exception can be constructed with valid arguments.
4. message, code, context attributes are accessible.
5. Legacy exception names still work and sit in the hierarchy.
"""

from __future__ import annotations

import lingualdub
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
    RegistryError,
    ResolutionError,
    ResourceError,
    ResourceLoadError,
    ResourceNotFoundError,
    ShutdownError,
    StageCompatibilityError,
    StageExecutionError,
)

# ---------------------------------------------------------------------------
# Importable from top-level lingualdub namespace
# ---------------------------------------------------------------------------


class TestTopLevelImportability:
    EXCEPTION_NAMES = [
        "LingualDubError",
        "ConfigurationError",
        "ConfigurationValidationError",
        "LifecycleError",
        "InitializationError",
        "ShutdownError",
        "PipelineError",
        "StageCompatibilityError",
        "StageExecutionError",
        "RegistryError",
        "RegistrationConflictError",
        "ResolutionError",
        "ComponentError",
        "ComponentContractError",
        "ResourceError",
        "ResourceNotFoundError",
        "ResourceLoadError",
        "ConsentViolationError",
        "InternalError",
        # Legacy / backward-compat names
        "PipelineExecutionError",
        "ManifestError",
        "ChecksumError",
        "ProvenanceMismatchError",
    ]

    def test_all_exceptions_importable_from_lingualdub(self) -> None:
        missing = [n for n in self.EXCEPTION_NAMES if not hasattr(lingualdub, n)]
        assert missing == [], f"Exceptions not importable from lingualdub: {missing}"


# ---------------------------------------------------------------------------
# Hierarchy (subclass relationships)
# ---------------------------------------------------------------------------


class TestHierarchy:
    def test_base_is_exception(self) -> None:
        assert issubclass(LingualDubError, Exception)

    def test_configuration_error(self) -> None:
        assert issubclass(ConfigurationError, LingualDubError)

    def test_configuration_validation_error(self) -> None:
        assert issubclass(ConfigurationValidationError, ConfigurationError)

    def test_lifecycle_error(self) -> None:
        assert issubclass(LifecycleError, LingualDubError)

    def test_initialization_error(self) -> None:
        assert issubclass(InitializationError, LifecycleError)

    def test_shutdown_error(self) -> None:
        assert issubclass(ShutdownError, LifecycleError)

    def test_pipeline_error(self) -> None:
        assert issubclass(PipelineError, LingualDubError)

    def test_stage_compatibility_error(self) -> None:
        assert issubclass(StageCompatibilityError, PipelineError)

    def test_stage_execution_error(self) -> None:
        assert issubclass(StageExecutionError, PipelineError)

    def test_registry_error(self) -> None:
        assert issubclass(RegistryError, LingualDubError)

    def test_registration_conflict_error(self) -> None:
        assert issubclass(RegistrationConflictError, RegistryError)

    def test_resolution_error(self) -> None:
        assert issubclass(ResolutionError, RegistryError)

    def test_component_error(self) -> None:
        assert issubclass(ComponentError, LingualDubError)

    def test_component_contract_error(self) -> None:
        assert issubclass(ComponentContractError, ComponentError)

    def test_resource_error(self) -> None:
        assert issubclass(ResourceError, LingualDubError)

    def test_resource_not_found_error(self) -> None:
        assert issubclass(ResourceNotFoundError, ResourceError)

    def test_resource_load_error(self) -> None:
        assert issubclass(ResourceLoadError, ResourceError)

    def test_consent_violation_error(self) -> None:
        assert issubclass(ConsentViolationError, ResourceError)

    def test_internal_error(self) -> None:
        assert issubclass(InternalError, LingualDubError)


# ---------------------------------------------------------------------------
# Legacy exception names remain in the hierarchy
# ---------------------------------------------------------------------------


class TestLegacyExceptionHierarchy:
    def test_pipeline_execution_error_is_stage_execution_error(self) -> None:
        assert issubclass(lingualdub.PipelineExecutionError, StageExecutionError)

    def test_manifest_error_is_registry_error(self) -> None:
        assert issubclass(lingualdub.ManifestError, RegistryError)

    def test_checksum_error_is_resource_load_error(self) -> None:
        assert issubclass(lingualdub.ChecksumError, ResourceLoadError)

    def test_resource_not_found_is_resource_error(self) -> None:
        from lingualdub.utils.resource_manager import ResourceNotFoundError as RNF

        assert issubclass(RNF, ResourceError)

    def test_provenance_mismatch_is_component_contract_error(self) -> None:
        assert issubclass(lingualdub.ProvenanceMismatchError, ComponentContractError)


# ---------------------------------------------------------------------------
# message / code / context attributes
# ---------------------------------------------------------------------------


class TestExceptionAttributes:
    def test_base_message(self) -> None:
        exc = LingualDubError("something went wrong")
        assert exc.message == "something went wrong"
        assert str(exc) == "something went wrong"

    def test_base_code_default_none(self) -> None:
        exc = LingualDubError("msg")
        assert exc.code is None

    def test_base_context_default_empty(self) -> None:
        exc = LingualDubError("msg")
        assert exc.context == {}

    def test_base_with_code_and_context(self) -> None:
        exc = LingualDubError("msg", code="ERR_001", context={"key": "value"})
        assert exc.code == "ERR_001"
        assert exc.context == {"key": "value"}

    def test_configuration_validation_error_field(self) -> None:
        exc = ConfigurationValidationError("bad value", field="log_level")
        assert exc.field == "log_level"
        assert exc.context["field"] == "log_level"

    def test_initialization_error_component(self) -> None:
        exc = InitializationError("failed", component="WhisperASR")
        assert exc.component == "WhisperASR"
        assert exc.context["component"] == "WhisperASR"

    def test_stage_compatibility_error_upstream_downstream(self) -> None:
        exc = StageCompatibilityError("incompatible", upstream="asr", downstream="tts")
        assert exc.upstream == "asr"
        assert exc.downstream == "tts"

    def test_stage_execution_error_stage(self) -> None:
        exc = StageExecutionError("stage blew up", stage="translation")
        assert exc.stage == "translation"

    def test_registration_conflict_error_kind_key(self) -> None:
        exc = RegistrationConflictError("conflict", kind="component", key="my_asr")
        assert exc.kind == "component"
        assert exc.key == "my_asr"

    def test_resolution_error_kind_key(self) -> None:
        exc = ResolutionError("not found", kind="component", key="missing_asr")
        assert exc.kind == "component"
        assert exc.key == "missing_asr"

    def test_component_contract_error_component(self) -> None:
        exc = ComponentContractError("violated", component="DummyASR")
        assert exc.component == "DummyASR"

    def test_resource_not_found_error_resource_id(self) -> None:
        exc = ResourceNotFoundError("missing", resource_id="model_weights_v1")
        assert exc.resource_id == "model_weights_v1"

    def test_resource_load_error_resource_id(self) -> None:
        exc = ResourceLoadError("checksum mismatch", resource_id="weights.bin")
        assert exc.resource_id == "weights.bin"

    def test_consent_violation_error_resource_id(self) -> None:
        exc = ConsentViolationError("consent denied", resource_id="audio.wav")
        assert exc.resource_id == "audio.wav"

    def test_internal_error_catchable_as_lingualdub_error(self) -> None:
        try:
            raise InternalError("unexpected state")
        except LingualDubError as exc:
            assert exc.message == "unexpected state"


# ---------------------------------------------------------------------------
# Catchability at multiple hierarchy levels
# ---------------------------------------------------------------------------


class TestCatchability:
    def test_catch_as_base(self) -> None:
        with __import__("pytest").raises(LingualDubError):
            raise StageExecutionError("boom", stage="asr")

    def test_catch_as_pipeline_error(self) -> None:
        with __import__("pytest").raises(PipelineError):
            raise StageCompatibilityError("incompatible")

    def test_catch_as_registry_error(self) -> None:
        with __import__("pytest").raises(RegistryError):
            raise ResolutionError("not found")

    def test_catch_as_resource_error(self) -> None:
        with __import__("pytest").raises(ResourceError):
            raise ConsentViolationError("denied")
