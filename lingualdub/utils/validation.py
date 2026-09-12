# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Input validation utilities — centralized, framework-wide argument checks.

Every public constructor and API entry point should delegate to these helpers
so that validation errors are consistent, early, and raise
:class:`ConfigurationValidationError` (a ``LingualDubError`` subclass) rather
than bare ``ValueError``/``TypeError``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from lingualdub.exceptions import ConfigurationValidationError

__all__ = [
    "require_non_empty_string",
    "require_positive_number",
    "require_one_of",
    "require_not_none",
    "validate_language_code",
    "validate_version_string",
]

# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

_LANGUAGE_CODE_RE = re.compile(r"^[a-z]{2,3}$")
# MAJOR.MINOR(.PATCH) — allow 2 or 3 numeric parts for backward compat (tests use "1.0")
_VERSION_RE = re.compile(r"^\d+\.\d+(\.\d+)?$")


def require_non_empty_string(value: Any, field_name: str) -> str:
    """
    Validate that ``value`` is a non-empty, non-whitespace string.

    Args:
        value: Value to check.
        field_name: Field name used in the error message / context.

    Returns:
        The original string (stripped is not returned, original kept).

    Raises:
        ConfigurationValidationError: If ``value`` is not a string or is empty/whitespace.
    """
    if not isinstance(value, str):
        raise ConfigurationValidationError(
            f"Field {field_name!r} must be a non-empty string, got {type(value).__name__}: {value!r}.",
            field=field_name,
        )
    if not value.strip():
        raise ConfigurationValidationError(
            f"Field {field_name!r} must be a non-empty string.",
            field=field_name,
        )
    return value


def require_positive_number(value: Any, field_name: str) -> float:
    """
    Validate that ``value`` is a positive number (> 0).

    Bool is explicitly rejected (``bool`` is a subclass of ``int`` in Python).

    Raises:
        ConfigurationValidationError: If not a number or not > 0.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationValidationError(
            f"Field {field_name!r} must be a positive number, got {type(value).__name__}: {value!r}.",
            field=field_name,
        )
    if not (value > 0):  # type: ignore[operator]
        raise ConfigurationValidationError(
            f"Field {field_name!r} must be > 0, got {value!r}.",
            field=field_name,
        )
    return float(value)


def require_one_of(value: Any, allowed: Iterable[Any], field_name: str) -> Any:
    """
    Validate that ``value`` is one of ``allowed``.

    Uses identity-aware check for bool/int ambiguity (True != 1).

    Raises:
        ConfigurationValidationError: If ``value`` not in ``allowed``.
    """
    allowed_list = list(allowed)
    # Use exact type+value match for bool to avoid True==1
    for a in allowed_list:
        if a is value or (type(a) is type(value) and a == value):
            return value
        # For non-bool, fall back to equality but guard bool/int confusion
        if not isinstance(value, bool) and not isinstance(a, bool) and value == a:
            return value
    raise ConfigurationValidationError(
        f"Field {field_name!r} must be one of {allowed_list!r}, got {value!r}.",
        field=field_name,
    )


def require_not_none(value: Any, field_name: str) -> Any:
    """
    Validate that ``value`` is not ``None``.

    Raises:
        ConfigurationValidationError: If ``value`` is ``None``.
    """
    if value is None:
        raise ConfigurationValidationError(
            f"Field {field_name!r} must not be None.",
            field=field_name,
        )
    return value


# ---------------------------------------------------------------------------
# Domain validators
# ---------------------------------------------------------------------------


def validate_language_code(code: Any, field_name: str = "language_code") -> str:
    """
    Validate an ISO 639-3 / BCP-47-ish language code.

    Accepts 2–3 lowercase letters (e.g. ``\"lug\"``, ``\"eng\"``). The check is
    intentionally conservative — it ensures the common case is correct while
    remaining fast and dependency-free. ``\"*\"`` is **not** considered a valid
    language code (it is a wildcard for ``supported_languages``, not a code).

    Returns:
        The validated code.

    Raises:
        ConfigurationValidationError: If ``code`` is not a valid language code.
    """
    require_non_empty_string(code, field_name)
    if not isinstance(code, str):
        raise ConfigurationValidationError("language_code must be a string.", field=field_name)
    if not _LANGUAGE_CODE_RE.match(code):
        raise ConfigurationValidationError(
            f"Invalid {field_name} {code!r}: must match {_LANGUAGE_CODE_RE.pattern!r} "
            "(2–3 lowercase letters, e.g. 'lug', 'eng', 'nyn').",
            field=field_name,
        )
    return code


def validate_version_string(version: Any) -> str:
    """
    Validate a ``MAJOR.MINOR.PATCH`` version string.

    Args:
        version: Version string to check.

    Returns:
        The validated version string.

    Raises:
        ConfigurationValidationError: If ``version`` does not match ``MAJOR.MINOR.PATCH``.
    """
    require_non_empty_string(version, "version")
    if not isinstance(version, str):
        raise ConfigurationValidationError("version must be a string.", field="version")
    if not _VERSION_RE.match(version):
        raise ConfigurationValidationError(
            f"Invalid version {version!r}: must match {_VERSION_RE.pattern!r} "
            "(e.g. '1.0.0', '0.1.0').",
            field="version",
        )
    return version
