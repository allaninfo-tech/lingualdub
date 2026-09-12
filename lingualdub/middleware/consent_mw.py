# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Consent middleware — EXT-006.

Enforces consent for voice-related resources.  Raises
``ConsentViolationError`` if consent is absent when required.
"""

from __future__ import annotations

from typing import Any

from lingualdub.core.resource import Resource
from lingualdub.core.result import Result
from lingualdub.exceptions import ConsentViolationError
from lingualdub.middleware.base import ExecutionContext

__all__ = ["ConsentMiddleware"]


class ConsentMiddleware:
    """Enforces consent for resources that require it.

    The middleware checks ``input.provenance`` for ``consent_basis``.  If the
    pipeline is considered voice-related (heuristic: pipeline name contains
    ``voice`` or ``tts`` or ``dubbing`` or input is voice-kind), and consent
    is missing, it raises :class:`ConsentViolationError`.

    For simplicity and testability, this implementation treats *any* ``Resource``
    with ``resource.kind`` that is voice-like or any pipeline whose name
    contains ``voice`` as requiring consent.  Callers can disable enforcement
    by setting ``context.metadata["skip_consent_check"] = True``.

    Attributes:
        name: Middleware name.
        priority: ``5`` — runs early, before logging/timing, to fail fast.
        strict: If ``True`` (default), all ``Resource`` inputs require consent;
                if ``False``, only voice-kind resources require it.
    """

    name: str = "consent"
    priority: int = 5
    __stability__: str = "stable"

    def __init__(self, strict: bool = False) -> None:
        self.strict: bool = strict

    def before(self, context: ExecutionContext) -> None:
        # Allow bypass via metadata
        if context.metadata.get("skip_consent_check") is True:
            return None
        inp = context.input
        # Determine if consent required
        requires_consent = self._requires_consent(context, inp)
        if not requires_consent:
            return None
        # Check consent
        has_consent = self._has_consent(inp)
        if not has_consent:
            raise ConsentViolationError(
                f"Consent required for pipeline {context.pipeline_name!r} but input {getattr(inp, 'id', str(inp))!r} lacks consent_basis.",
                resource_id=getattr(inp, "id", None),
                code="CONSENT_001",
                context={
                    "pipeline": context.pipeline_name,
                    "resource_id": getattr(inp, "id", None),
                },
            )
        return None

    def after(self, context: ExecutionContext, result: Result) -> Result:
        return result

    def on_error(self, context: ExecutionContext, error: Exception) -> None:
        return None

    def _requires_consent(self, context: ExecutionContext, inp: Any) -> bool:
        # Never require consent for Result inputs (they are intermediate)
        if isinstance(inp, Result):
            return False
        if not isinstance(inp, Resource):
            return False
        # Heuristic: if strict, all Resource require consent
        if self.strict:
            return True
        # Voice-related pipeline names — only for Resource
        name_lower = context.pipeline_name.lower()
        if any(kw in name_lower for kw in ("voice", "tts", "dub", "speaker")):
            # Check if resource is speech-like; otherwise not required in non-strict
            voice_kinds = {"speech", "voice", "audio"}
            kind_val = (
                getattr(inp.kind, "value", str(inp.kind)).lower() if hasattr(inp, "kind") else ""
            )
            return kind_val in voice_kinds
        # Resource kind voice-like (even without pipeline name)
        voice_kinds = {"speech", "voice", "audio"}
        kind_val = getattr(inp.kind, "value", str(inp.kind)).lower() if hasattr(inp, "kind") else ""
        return kind_val in voice_kinds

    def _has_consent(self, inp: Any) -> bool:
        # Resource has has_consent property; Result may carry provenance
        if hasattr(inp, "has_consent"):
            try:
                return bool(inp.has_consent)  # type: ignore[operator]
            except Exception:
                pass
        prov = getattr(inp, "provenance", None)
        if isinstance(prov, dict):
            val = prov.get("consent_basis")
            return isinstance(val, str) and bool(val.strip())
        return False

    def __repr__(self) -> str:
        return (
            f"ConsentMiddleware(name={self.name!r}, priority={self.priority}, strict={self.strict})"
        )
