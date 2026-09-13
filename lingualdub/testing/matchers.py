# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Test matchers — assertion helpers for Result/Resource tests — REL-005.

    from lingualdub.testing.matchers import (
        assert_result_complete,
        assert_result_failed,
        assert_result_has_segment,
    )

Matchers raise ``AssertionError`` with a diff-style message on failure, so
they integrate with ``pytest`` assertion rewriting.
"""

from __future__ import annotations

from lingualdub.core.resource import Resource
from lingualdub.core.result import Result, ResultStatus
from lingualdub.core.segment import Segment

__all__ = [
    "assert_result_complete",
    "assert_result_failed",
    "assert_result_partial",
    "assert_result_degraded",
    "assert_result_has_segment",
    "assert_result_has_language",
    "assert_resource_valid",
]


def assert_result_complete(result: Result) -> None:
    """Assert ``result.status == COMPLETE`` and ``is_usable``."""
    if not isinstance(result, Result):
        raise AssertionError(f"Expected Result, got {type(result).__name__}: {result!r}.")
    if result.status != ResultStatus.COMPLETE:
        raise AssertionError(
            f"Expected ResultStatus.COMPLETE, got {result.status.value!r}\n"
            f"  warnings: {result.warnings!r}\n"
            f"  segments: {len(result.segments)}"
        )
    if not result.is_usable:
        raise AssertionError("Expected is_usable True for COMPLETE result, got False.")


def assert_result_failed(result: Result) -> None:
    """Assert ``result.status == FAILED`` and ``is_usable is False``."""
    if not isinstance(result, Result):
        raise AssertionError(f"Expected Result, got {type(result).__name__}: {result!r}.")
    if result.status != ResultStatus.FAILED:
        raise AssertionError(
            f"Expected ResultStatus.FAILED, got {result.status.value!r}\n  warnings: {result.warnings!r}"
        )
    if result.is_usable:
        raise AssertionError("Expected is_usable False for FAILED result, got True.")


def assert_result_partial(result: Result) -> None:
    """Assert ``result.status == PARTIAL``."""
    if not isinstance(result, Result):
        raise AssertionError(f"Expected Result, got {type(result).__name__}: {result!r}.")
    if result.status != ResultStatus.PARTIAL:
        raise AssertionError(
            f"Expected ResultStatus.PARTIAL, got {result.status.value!r}\n  warnings: {result.warnings!r}"
        )


def assert_result_degraded(result: Result) -> None:
    """Assert ``result.status == DEGRADED``."""
    if not isinstance(result, Result):
        raise AssertionError(f"Expected Result, got {type(result).__name__}: {result!r}.")
    if result.status != ResultStatus.DEGRADED:
        raise AssertionError(
            f"Expected ResultStatus.DEGRADED, got {result.status.value!r}\n  warnings: {result.warnings!r}"
        )


def assert_result_has_segment(result: Result, text: str, language: str | None = None) -> Segment:
    """Assert ``result`` has a segment whose ``text`` contains the given substring.

    Args:
        result: Result to search.
        text: Substring to find (case-sensitive) within ``segment.text``.
        language: Optional language filter — only segments with this language are considered.

    Returns:
        The matching :class:`Segment`.

    Raises:
        AssertionError: If no matching segment is found.
    """
    if not isinstance(result, Result):
        raise AssertionError(f"Expected Result, got {type(result).__name__}: {result!r}.")
    if not isinstance(text, str):
        raise AssertionError(f"text must be str, got {type(text).__name__}: {text!r}.")

    candidates = result.segments
    if language is not None:
        candidates = [s for s in candidates if s.language == language]

    for seg in candidates:
        if text in seg.text:
            return seg

    # Build helpful message
    all_texts = [f"  - {s.text!r} ({s.language})" for s in result.segments]
    joined = "\n".join(all_texts) if all_texts else "  (no segments)"
    lang_note = f" with language={language!r}" if language is not None else ""
    raise AssertionError(
        f"Result has no segment containing {text!r}{lang_note}.\n"
        f"Segments ({len(result.segments)}):\n{joined}"
    )


def assert_result_has_language(result: Result, language: str) -> None:
    """Assert at least one segment in ``result`` has the given language."""
    if not isinstance(result, Result):
        raise AssertionError(f"Expected Result, got {type(result).__name__}: {result!r}.")
    if not any(s.language == language for s in result.segments):
        langs = sorted({s.language for s in result.segments})
        raise AssertionError(
            f"Result has no segment with language {language!r}.\n"
            f"Languages present: {langs!r}\n"
            f"Segments: {[s.text for s in result.segments]!r}"
        )


def assert_resource_valid(resource: Resource) -> None:
    """Assert ``resource`` is a valid :class:`Resource` (triggers validation)."""
    if not isinstance(resource, Resource):
        raise AssertionError(f"Expected Resource, got {type(resource).__name__}: {resource!r}.")
    # Validation happens in __post_init__; just re-validate via from_dict round-trip
    restored = Resource.from_dict(resource.to_dict())
    if restored.id != resource.id:
        raise AssertionError("Resource round-trip id mismatch.")
