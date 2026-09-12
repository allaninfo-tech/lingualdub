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

import os
from dataclasses import FrozenInstanceError, dataclass, field
from pathlib import Path
from typing import Any

from lingualdub.core.component import FailureMode
from lingualdub.exceptions import ConfigurationValidationError
from lingualdub.registry.registry import ConflictPolicy

__all__ = ["FrameworkConfig", "load_config"]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL"}
# Normalise WARN -> WARNING
_LOG_LEVEL_ALIASES: dict[str, str] = {"WARN": "WARNING"}

_ENV_MAP: dict[str, str] = {
    "LINGUALDUB_LOG_LEVEL": "log_level",
    "LINGUALDUB_DEFAULT_FAILURE_MODE": "default_failure_mode",
    "LINGUALDUB_REGISTRY_CONFLICT_POLICY": "registry_conflict_policy",
    "LINGUALDUB_CACHE_DIR": "cache_dir",
    "LINGUALDUB_CONSENT_ENFORCEMENT": "consent_enforcement",
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
    """

    log_level: str = "INFO"
    default_failure_mode: FailureMode = FailureMode.ABORT
    registry_conflict_policy: ConflictPolicy = ConflictPolicy.NAMESPACED
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "lingualdub")
    consent_enforcement: bool = True

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

        # Freeze — use object.__setattr__ to bypass our own guard
        if not is_frozen:
            object.__setattr__(self, "_frozen", True)

    @property
    def is_frozen(self) -> bool:
        """Whether this config has been validated and frozen."""
        return bool(self.__dict__.get("_frozen", False))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict of the config (excluding internal state)."""
        return {
            "log_level": self.log_level,
            "default_failure_mode": self.default_failure_mode.value
            if isinstance(self.default_failure_mode, FailureMode)
            else self.default_failure_mode,
            "registry_conflict_policy": self.registry_conflict_policy.value
            if isinstance(self.registry_conflict_policy, ConflictPolicy)
            else self.registry_conflict_policy,
            "cache_dir": str(self.cache_dir),
            "consent_enforcement": self.consent_enforcement,
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
