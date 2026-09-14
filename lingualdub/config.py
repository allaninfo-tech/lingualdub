# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Framework configuration — centralized, validated, immutable after validation.

Provides :class:`FrameworkConfig` and :func:`load_config` with precedence:

    defaults → environment variables → explicit ``overrides``

Environment overrides use the ``LINGUALDUB_*`` naming convention.
After :meth:`FrameworkConfig.validate` is called the instance is frozen;
any subsequent mutation raises :class:`dataclasses.FrozenInstanceError`.

Example::

    from lingualdub.config import load_config

    cfg = load_config()  # reads env vars, validated and frozen
    cfg = load_config({"log_level": "DEBUG", "consent_enforcement": False})
"""

from __future__ import annotations

import contextlib
import os
from dataclasses import FrozenInstanceError, dataclass, field
from pathlib import Path
from typing import Any

from lingualdub.core.component import FailureMode
from lingualdub.exceptions import ConfigurationValidationError
from lingualdub.registry.registry import ConflictPolicy

__all__ = ["FrameworkConfig", "SecurityConfig", "load_config", "is_cache_enabled"]

# Global cache enabled flag for PEV-005 — updated on validate/load_config
_global_cache_enabled: bool = True

# Global security config for PRO-004 — updated on validate/load_config
_global_security_config: SecurityConfig | None = None


def get_security_config() -> SecurityConfig | None:
    """Return effective global :class:`SecurityConfig` if validated, else ``None``."""
    return _global_security_config


def is_cache_enabled() -> bool:
    """Return whether framework caches are enabled (PEV-005).

    Controlled by ``FrameworkConfig.cache_enabled``. Defaults to ``True``.
    """
    return _global_cache_enabled


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL"}
# Normalise WARN -> WARNING
_LOG_LEVEL_ALIASES: dict[str, str] = {"WARN": "WARNING"}

_ALLOWED_LOG_FORMATS = {"json", "text"}
_ALLOWED_METRICS_BACKENDS = {"noop", "prometheus", "statsd", "custom"}

_DEFAULT_SENSITIVE_FIELDS = [
    "api_key",
    "access_token",
    "speaker_reference",
    "voice_path",
    "consent_record",
    "email",
]

_ENV_MAP: dict[str, str] = {
    "LINGUALDUB_LOG_LEVEL": "log_level",
    "LINGUALDUB_LOG_FORMAT": "log_format",
    "LINGUALDUB_DEFAULT_FAILURE_MODE": "default_failure_mode",
    "LINGUALDUB_REGISTRY_CONFLICT_POLICY": "registry_conflict_policy",
    "LINGUALDUB_CACHE_DIR": "cache_dir",
    "LINGUALDUB_CONSENT_ENFORCEMENT": "consent_enforcement",
    "LINGUALDUB_CACHE_ENABLED": "cache_enabled",
    "LINGUALDUB_LOG_REDACTION_ENABLED": "log_redaction_enabled",
    "LINGUALDUB_METRICS_BACKEND": "metrics_backend",
    "LINGUALDUB_MAX_SEGMENT_LENGTH": "max_segment_length",
    "LINGUALDUB_MAX_METADATA_DEPTH": "max_metadata_depth",
    "LINGUALDUB_PATH_TRAVERSAL_CHECK_ENABLED": "path_traversal_check_enabled",
}

_TRUTHY = {"1", "true", "yes", "on", "enabled"}
_FALSY = {"0", "false", "no", "off", "disabled"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if value == 1:
            return True
        if value == 0:
            return False
        raise ConfigurationValidationError(
            f"Field {field_name!r} expects a boolean, got {value!r}. "
            "Use true/false, 1/0, yes/no, on/off.",
            field=field_name,
        )
    if isinstance(value, str):
        low = value.strip().lower()
        if low in _TRUTHY:
            return True
        if low in _FALSY:
            return False
        raise ConfigurationValidationError(
            f"Field {field_name!r} expects a boolean string, got {value!r}. "
            f"Allowed truthy: {sorted(_TRUTHY)}, falsy: {sorted(_FALSY)}.",
            field=field_name,
        )
    raise ConfigurationValidationError(
        f"Field {field_name!r} expects a boolean, got {type(value).__name__}: {value!r}.",
        field=field_name,
    )


def _coerce_failure_mode(value: Any, field_name: str) -> FailureMode:
    if isinstance(value, FailureMode):
        return value
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if not cleaned:
            raise ConfigurationValidationError(
                f"Field {field_name!r} must be a non-empty string.",
                field=field_name,
            )
        try:
            return FailureMode(cleaned)
        except ValueError:
            raise ConfigurationValidationError(
                f"Invalid {field_name!r} {value!r}: must be one of "
                f"{[e.value for e in FailureMode]}.",
                field=field_name,
            ) from None
    raise ConfigurationValidationError(
        f"Field {field_name!r} must be a FailureMode or string, got {type(value).__name__}: {value!r}.",
        field=field_name,
    )


def _coerce_conflict_policy(value: Any, field_name: str) -> ConflictPolicy:
    if isinstance(value, ConflictPolicy):
        return value
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if not cleaned:
            raise ConfigurationValidationError(
                f"Field {field_name!r} must be a non-empty string.",
                field=field_name,
            )
        try:
            return ConflictPolicy(cleaned)
        except ValueError:
            raise ConfigurationValidationError(
                f"Invalid {field_name!r} {value!r}: must be one of "
                f"{[e.value for e in ConflictPolicy]}.",
                field=field_name,
            ) from None
    raise ConfigurationValidationError(
        f"Field {field_name!r} must be a ConflictPolicy or string, got {type(value).__name__}: {value!r}.",
        field=field_name,
    )


def _coerce_cache_dir(value: Any, field_name: str) -> Path:
    if value is None:
        raise ConfigurationValidationError(
            f"Field {field_name!r} must not be None.",
            field=field_name,
        )
    if isinstance(value, Path):
        # Path('') yields '.' — treat as empty
        if not str(value).strip() or str(value).strip() == ".":
            # Allow '.'? but empty string becomes '.' — reject original empty
            # If value was Path('') then str is '.' but original was empty — reject
            # We detect by checking if original string was empty, but Path loses that.
            # Instead we treat '.' as valid if explicitly passed, but not as fallback for empty.
            # For safety, allow '.' but reject empty string case handled above.
            pass
        return value
    if isinstance(value, str):
        if not value.strip():
            raise ConfigurationValidationError(
                f"Field {field_name!r} must be a non-empty path string.",
                field=field_name,
            )
        return Path(value.strip())
    if isinstance(value, os.PathLike):  # type: ignore[arg-type]
        return Path(value)  # type: ignore[arg-type]
    raise ConfigurationValidationError(
        f"Field {field_name!r} must be a path string or Path, got {type(value).__name__}: {value!r}.",
        field=field_name,
    )


def _coerce_log_level(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ConfigurationValidationError(
            f"Field {field_name!r} must be a string, got {type(value).__name__}: {value!r}.",
            field=field_name,
        )
    cleaned = value.strip().upper()
    if not cleaned:
        raise ConfigurationValidationError(
            f"Field {field_name!r} must be a non-empty string.",
            field=field_name,
        )
    if cleaned not in _ALLOWED_LOG_LEVELS:
        raise ConfigurationValidationError(
            f"Invalid {field_name!r} {value!r}: must be one of {sorted(_ALLOWED_LOG_LEVELS)}.",
            field=field_name,
        )
    # normalise WARN -> WARNING
    return _LOG_LEVEL_ALIASES.get(cleaned, cleaned)


def _coerce_log_format(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ConfigurationValidationError(
            f"Field {field_name!r} must be a string, got {type(value).__name__}: {value!r}.",
            field=field_name,
        )
    cleaned = value.strip().lower()
    if not cleaned:
        raise ConfigurationValidationError(
            f"Field {field_name!r} must be a non-empty string.",
            field=field_name,
        )
    if cleaned not in _ALLOWED_LOG_FORMATS:
        raise ConfigurationValidationError(
            f"Invalid {field_name!r} {value!r}: must be one of {sorted(_ALLOWED_LOG_FORMATS)}.",
            field=field_name,
        )
    return cleaned


def _coerce_metrics_backend(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ConfigurationValidationError(
            f"Field {field_name!r} must be a string, got {type(value).__name__}: {value!r}.",
            field=field_name,
        )
    cleaned = value.strip().lower()
    if not cleaned:
        raise ConfigurationValidationError(
            f"Field {field_name!r} must be a non-empty string.",
            field=field_name,
        )
    if cleaned not in _ALLOWED_METRICS_BACKENDS:
        raise ConfigurationValidationError(
            f"Invalid {field_name!r} {value!r}: must be one of {sorted(_ALLOWED_METRICS_BACKENDS)}.",
            field=field_name,
        )
    return cleaned


def _coerce_positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ConfigurationValidationError(
            f"Field {field_name!r} must be a positive int, got bool: {value!r}.",
            field=field_name,
        )
    if isinstance(value, int):
        if value <= 0:
            raise ConfigurationValidationError(
                f"Field {field_name!r} must be > 0, got {value!r}.",
                field=field_name,
            )
        return value
    if isinstance(value, str):
        if not value.strip():
            raise ConfigurationValidationError(
                f"Field {field_name!r} must be a non-empty positive int string.",
                field=field_name,
            )
        try:
            iv = int(value.strip())
        except ValueError:
            raise ConfigurationValidationError(
                f"Field {field_name!r} must be a positive int, got {value!r}.",
                field=field_name,
            ) from None
        if iv <= 0:
            raise ConfigurationValidationError(
                f"Field {field_name!r} must be > 0, got {iv!r}.",
                field=field_name,
            )
        return iv
    raise ConfigurationValidationError(
        f"Field {field_name!r} must be a positive int, got {type(value).__name__}: {value!r}.",
        field=field_name,
    )


def _coerce_metadata_depth(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ConfigurationValidationError(
            f"Field {field_name!r} must be a non-negative int, got bool: {value!r}.",
            field=field_name,
        )
    if isinstance(value, int):
        if value < 0:
            raise ConfigurationValidationError(
                f"Field {field_name!r} must be >= 0, got {value!r}.",
                field=field_name,
            )
        return value
    if isinstance(value, str):
        if not value.strip():
            raise ConfigurationValidationError(
                f"Field {field_name!r} must be a non-empty int string.",
                field=field_name,
            )
        try:
            iv = int(value.strip())
        except ValueError:
            raise ConfigurationValidationError(
                f"Field {field_name!r} must be an int, got {value!r}.",
                field=field_name,
            ) from None
        if iv < 0:
            raise ConfigurationValidationError(
                f"Field {field_name!r} must be >= 0, got {iv!r}.",
                field=field_name,
            )
        return iv
    raise ConfigurationValidationError(
        f"Field {field_name!r} must be an int, got {type(value).__name__}: {value!r}.",
        field=field_name,
    )


def _coerce_sensitive_fields(value: Any, field_name: str) -> list[str]:
    if isinstance(value, str):
        # Comma-separated string from env var
        if not value.strip():
            return []
        parts = [p.strip() for p in value.split(",")]
        value = [p for p in parts if p]
    if not isinstance(value, list):
        raise ConfigurationValidationError(
            f"Field {field_name!r} must be a list of strings, got {type(value).__name__}: {value!r}.",
            field=field_name,
        )
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise ConfigurationValidationError(
                f"Field {field_name!r}[{i}] must be a string, got {type(item).__name__}: {item!r}.",
                field=f"{field_name}[{i}]",
            )
        if not item.strip():
            raise ConfigurationValidationError(
                f"Field {field_name!r}[{i}] must be non-empty.",
                field=f"{field_name}[{i}]",
            )
    return list(value)


# ---------------------------------------------------------------------------
# SecurityConfig
# ---------------------------------------------------------------------------


@dataclass
class SecurityConfig:
    """Security-related limits and toggles (PRO-004).

    Attributes:
        max_segment_length: Maximum allowed characters for ``Segment.text``.
        max_metadata_depth: Maximum nesting depth for ``metadata`` dicts.
        path_traversal_check_enabled: Whether to enforce path traversal checks.
    """

    max_segment_length: int = 5000
    max_metadata_depth: int = 10
    path_traversal_check_enabled: bool = True

    def validate(self) -> None:
        _coerce_positive_int(self.max_segment_length, "max_segment_length")
        _coerce_metadata_depth(self.max_metadata_depth, "max_metadata_depth")
        _parse_bool(self.path_traversal_check_enabled, "path_traversal_check_enabled")


# ---------------------------------------------------------------------------
# FrameworkConfig
# ---------------------------------------------------------------------------


@dataclass
class FrameworkConfig:
    """
    Centralised framework configuration.

    Attributes:
        log_level: Logging verbosity. One of ``DEBUG``, ``INFO``, ``WARNING``,
            ``ERROR``, ``CRITICAL`` (``WARN`` is accepted as alias for ``WARNING``).
        log_format: Log output format — ``json`` (structured) or ``text``.
        default_failure_mode: Default pipeline failure handling when a stage
            does not declare its own ``on_failure``. One of ``FailureMode`` values.
        registry_conflict_policy: How the :class:`Registry` handles duplicate
            ``(kind, key)`` registrations. One of ``ConflictPolicy`` values.
        cache_dir: Local filesystem directory used by :class:`ResourceManager`
            to cache downloaded resources. Defaults to ``~/.cache/lingualdub``.
            Overridable via ``LINGUALDUB_CACHE_DIR``.
        consent_enforcement: When ``True`` (default), voice-related components
            require ``provenance.consent_basis``. When ``False``, consent checks
            are disabled (useful for non-voice benchmarks).
        cache_enabled: When ``False``, disables framework caches for
            ``Pipeline._validate_stage_compatibility`` and ``MiddlewareChain``
            (PEV-005).
        log_redaction_enabled: When ``True`` (default), sensitive field values
            are replaced with ``[REDACTED]`` in logs.
        sensitive_fields: List of field names considered sensitive for
            redaction. Extensible by user (PRO-005).
        metrics_backend: Metrics backend name — ``noop`` (default), ``prometheus``, etc.
        max_segment_length: Maximum allowed ``Segment.text`` length (PRO-004).
        max_metadata_depth: Maximum nesting depth for metadata dicts (PRO-004).
        path_traversal_check_enabled: Whether to enforce path traversal validation (PRO-004).
    """

    log_level: str = "INFO"
    log_format: str = "json"
    default_failure_mode: FailureMode = FailureMode.ABORT
    registry_conflict_policy: ConflictPolicy = ConflictPolicy.NAMESPACED
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "lingualdub")
    consent_enforcement: bool = True
    cache_enabled: bool = True
    log_redaction_enabled: bool = True
    sensitive_fields: list[str] = field(default_factory=lambda: list(_DEFAULT_SENSITIVE_FIELDS))
    metrics_backend: str = "noop"
    max_segment_length: int = 5000
    max_metadata_depth: int = 10
    path_traversal_check_enabled: bool = True

    # internal — not part of constructor after init
    _frozen: bool = field(default=False, init=False, repr=False, compare=False)

    def __setattr__(self, name: str, value: Any) -> None:
        # Enforce immutability after validate() has frozen the instance.
        # Use __dict__ directly to avoid recursion during __init__.
        if self.__dict__.get("_frozen", False):
            raise FrozenInstanceError(f"cannot assign to field {name!r} of frozen FrameworkConfig")
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        if self.__dict__.get("_frozen", False):
            raise FrozenInstanceError(f"cannot delete field {name!r} of frozen FrameworkConfig")
        super().__delattr__(name)

    @property
    def security_config(self) -> SecurityConfig:
        """Return a :class:`SecurityConfig` view of security-related fields."""
        return SecurityConfig(
            max_segment_length=self.max_segment_length,
            max_metadata_depth=self.max_metadata_depth,
            path_traversal_check_enabled=self.path_traversal_check_enabled,
        )

    def validate(self) -> None:
        """
        Validate all fields and freeze the instance.

        Raises:
            ConfigurationValidationError: If any field is invalid.
            FrozenInstanceError: If the instance is already frozen (re-validation
                is a no-op — the second call will raise frozen error if mutation
                is attempted, but validate() itself is idempotent when already frozen).

        After successful validation the instance becomes immutable; any further
        attribute assignment raises :class:`dataclasses.FrozenInstanceError`.
        """
        # Allow re-validation on a frozen instance by temporarily bypassing freeze
        # for internal normalisation, then re-freeze. But we must not allow mutation
        # after freeze — so we validate without mutating via setattr when frozen.
        # Easiest: if already frozen, just verify current values without mutating.
        is_frozen = self.__dict__.get("_frozen", False)

        # Coerce / validate each field. We must use object.__setattr__ to
        # bypass the frozen check during validation, since we are normalising.
        # If already frozen, we instead validate without mutating; if mismatch
        # we still raise.
        def _set_or_check(field_name: str, coerced: Any) -> None:
            current = self.__dict__.get(field_name)
            # If frozen, ensure coerced equals current (or current already correct)
            if is_frozen:
                # For cache_dir, compare Path equality; for enums direct; for str upper.
                if current != coerced:
                    # If values differ, it means env/override attempted to mutate frozen;
                    # but validate was not called via load_config — treat as validation error
                    raise FrozenInstanceError(
                        f"cannot re-validate frozen FrameworkConfig with changed {field_name!r}"
                    )
                return
            object.__setattr__(self, field_name, coerced)

        # log_level
        coerced_log = _coerce_log_level(self.log_level, "log_level")  # type: ignore[arg-type]
        _set_or_check("log_level", coerced_log)

        # log_format
        coerced_fmt = _coerce_log_format(self.log_format, "log_format")  # type: ignore[arg-type]
        _set_or_check("log_format", coerced_fmt)

        # default_failure_mode
        coerced_fm = _coerce_failure_mode(self.default_failure_mode, "default_failure_mode")  # type: ignore[arg-type]
        _set_or_check("default_failure_mode", coerced_fm)

        # registry_conflict_policy
        coerced_cp = _coerce_conflict_policy(
            self.registry_conflict_policy,
            "registry_conflict_policy",  # type: ignore[arg-type]
        )
        _set_or_check("registry_conflict_policy", coerced_cp)

        # cache_dir
        coerced_cache = _coerce_cache_dir(self.cache_dir, "cache_dir")  # type: ignore[arg-type]
        _set_or_check("cache_dir", coerced_cache)

        # consent_enforcement
        coerced_consent = _parse_bool(self.consent_enforcement, "consent_enforcement")  # type: ignore[arg-type]
        _set_or_check("consent_enforcement", coerced_consent)

        # cache_enabled
        coerced_cache_enabled = _parse_bool(self.cache_enabled, "cache_enabled")  # type: ignore[arg-type]
        _set_or_check("cache_enabled", coerced_cache_enabled)

        # log_redaction_enabled
        coerced_redact = _parse_bool(self.log_redaction_enabled, "log_redaction_enabled")  # type: ignore[arg-type]
        _set_or_check("log_redaction_enabled", coerced_redact)

        # sensitive_fields
        coerced_sensitive = _coerce_sensitive_fields(self.sensitive_fields, "sensitive_fields")  # type: ignore[arg-type]
        _set_or_check("sensitive_fields", coerced_sensitive)

        # metrics_backend
        coerced_metrics = _coerce_metrics_backend(self.metrics_backend, "metrics_backend")  # type: ignore[arg-type]
        _set_or_check("metrics_backend", coerced_metrics)

        # max_segment_length
        coerced_seg = _coerce_positive_int(self.max_segment_length, "max_segment_length")  # type: ignore[arg-type]
        _set_or_check("max_segment_length", coerced_seg)

        # max_metadata_depth
        coerced_depth = _coerce_metadata_depth(self.max_metadata_depth, "max_metadata_depth")  # type: ignore[arg-type]
        _set_or_check("max_metadata_depth", coerced_depth)

        # path_traversal_check_enabled
        coerced_path_check = _parse_bool(
            self.path_traversal_check_enabled,
            "path_traversal_check_enabled",  # type: ignore[arg-type]
        )
        _set_or_check("path_traversal_check_enabled", coerced_path_check)

        # Freeze — use object.__setattr__ to bypass our own guard
        if not is_frozen:
            object.__setattr__(self, "_frozen", True)
        # Update global cache flag (PEV-005) and security config (PRO-004)
        global _global_cache_enabled, _global_security_config
        with contextlib.suppress(Exception):
            _global_cache_enabled = bool(self.cache_enabled)
        with contextlib.suppress(Exception):
            _global_security_config = self.security_config

    @property
    def is_frozen(self) -> bool:
        """Whether this config has been validated and frozen."""
        return bool(self.__dict__.get("_frozen", False))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict of the config (excluding internal state)."""
        return {
            "log_level": self.log_level,
            "log_format": self.log_format,
            "default_failure_mode": self.default_failure_mode.value
            if isinstance(self.default_failure_mode, FailureMode)
            else self.default_failure_mode,
            "registry_conflict_policy": self.registry_conflict_policy.value
            if isinstance(self.registry_conflict_policy, ConflictPolicy)
            else self.registry_conflict_policy,
            "cache_dir": str(self.cache_dir),
            "consent_enforcement": self.consent_enforcement,
            "cache_enabled": self.cache_enabled,
            "log_redaction_enabled": self.log_redaction_enabled,
            "sensitive_fields": list(self.sensitive_fields),
            "metrics_backend": self.metrics_backend,
            "max_segment_length": self.max_segment_length,
            "max_metadata_depth": self.max_metadata_depth,
            "path_traversal_check_enabled": self.path_traversal_check_enabled,
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _get_cache_dir_env() -> str | None:
    """Centralised helper for reading the cache dir env var (used by ResourceManager)."""
    return os.environ.get("LINGUALDUB_CACHE_DIR")


def load_config(overrides: dict[str, Any] | None = None) -> FrameworkConfig:
    """
    Build a validated, frozen :class:`FrameworkConfig`.

    Precedence (lowest → highest):

    1. Hard-coded defaults in :class:`FrameworkConfig`.
    2. Environment variables (``LINGUALDUB_*``).
    3. Explicit ``overrides`` dict.

    Args:
        overrides: Optional mapping of field names to values. Keys must match
            :class:`FrameworkConfig` field names (e.g. ``{"log_level": "DEBUG"}``).

    Returns:
        A validated, immutable :class:`FrameworkConfig`.

    Raises:
        ConfigurationValidationError: If any field is invalid or an unknown
            override key is supplied.
    """
    cfg = FrameworkConfig()

    # 1. defaults already in cfg

    # 2. env var overrides
    for env_name, field_name in _ENV_MAP.items():
        raw = os.environ.get(env_name)
        if raw is not None:
            # For cache_dir, keep as string until validate coerces to Path;
            # for others, keep raw string and let validate coerce/validate.
            # Use object.__setattr__ bypass is not needed here because cfg not frozen.
            # But we assign via setattr to keep normal path.
            # Special handling for sensitive_fields (comma-separated)
            if field_name == "sensitive_fields":
                # env var as comma-separated
                setattr(cfg, field_name, raw)
            else:
                setattr(cfg, field_name, raw)

    # 3. explicit overrides
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise ConfigurationValidationError(
                f"overrides must be a dict, got {type(overrides).__name__}: {overrides!r}",
                field="overrides",
            )
        for key, value in overrides.items():
            if key not in FrameworkConfig.__dataclass_fields__ or key == "_frozen":
                raise ConfigurationValidationError(
                    f"Unknown config field {key!r}. Allowed: "
                    f"{[k for k in FrameworkConfig.__dataclass_fields__ if k != '_frozen']}",
                    field=key,
                )
            setattr(cfg, key, value)

    cfg.validate()
    return cfg
