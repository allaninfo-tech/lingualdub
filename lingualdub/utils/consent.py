"""
Consent enforcement utilities for voice processing (M5/M6).

Centralises the check that voice Resources/Results carry a recorded
consent_basis in provenance. Prevents silent processing of voice data
without consent across all voice-related components.
"""

from __future__ import annotations

from typing import Union

from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


def has_valid_consent(provenance: dict) -> bool:
    """Return True if provenance contains a non-empty consent_basis."""
    val = provenance.get("consent_basis")
    return isinstance(val, str) and bool(val.strip())


def _result_has_voice_signal(result: Result) -> bool:
    """Heuristic: does this Result carry voice data requiring consent?"""
    if result.artifacts:
        return True
    if any(s.speaker for s in result.segments):
        return True
    # If provenance already indicates voice processing, treat as voice
    if result.provenance.get("consent_basis") is not None:
        # provenance has consent key (even if empty) -> caller intends voice
        return True
    # Legacy: segments with provenance voice keys
    for s in result.segments:
        if s.provenance.get("consent_basis") or s.speaker:
            return True
    return False


def ensure_consent(input_obj: Union[Resource, Result], component_name: str) -> None:
    """
    Enforce consent_basis for voice processing.

    For Resource: always requires consent_basis when component is voice-related.
    For Result: requires consent if the Result appears to carry voice data
    (artifacts or speaker identifiers). Results without voice signals pass.

    Raises:
        ValueError: If consent is missing with a clear remediation message.
    """
    if isinstance(input_obj, Resource):
        if not has_valid_consent(input_obj.provenance):
            raise ValueError(
                f"{component_name}: Resource {input_obj.id!r} lacks a valid 'consent_basis' "
                "in provenance. Voice data must carry a recorded consent basis to be processed. "
                "Add provenance={'consent_basis': '...'} to the Resource."
            )
    elif isinstance(input_obj, Result):
        # Check if this Result carries voice data requiring consent
        has_voice = _result_has_voice_signal(input_obj)
        # Also consider metadata consent
        provenance = input_obj.provenance or {}
        has_consent = has_valid_consent(provenance) or has_valid_consent(
            input_obj.metadata if isinstance(input_obj.metadata, dict) else {}
        )
        # Check segment-level consent as fallback
        if not has_consent and has_voice:
            for seg in input_obj.segments:
                if has_valid_consent(seg.provenance):
                    has_consent = True
                    break
        if has_voice and not has_consent:
            raise ValueError(
                f"{component_name}: Result lacks valid 'consent_basis' in provenance. "
                "Voice-derived Results must carry provenance={'consent_basis': '...'} "
                "to be processed. Ensure the source Resource had consent and that "
                "provenance was propagated through the pipeline."
            )
