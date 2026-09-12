# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Consent enforcement utilities for voice processing (M5/M6).

Centralises the check that voice Resources/Results carry a recorded
consent_basis in provenance. Prevents silent processing of voice data
without consent across all voice-related components.
"""

from __future__ import annotations

from lingualdub.core.resource import Resource
from lingualdub.core.result import Result


def has_valid_consent(provenance: dict) -> bool:
    """Return True if provenance contains a non-empty consent_basis."""
    val = provenance.get("consent_basis")
    return isinstance(val, str) and bool(val.strip())


def _result_has_voice_signal(result: Result) -> bool:
    """Heuristic: does this Result carry voice data requiring consent?"""
    # Only treat audio-like artifacts as voice (wav/mp3 etc), not generic metrics
    audio_exts = (".wav", ".mp3", ".flac", ".ogg", ".m4a", ".mp4", ".webm")
    if any(str(a).lower().endswith(audio_exts) for a in result.artifacts):
        return True
    if any(s.speaker for s in result.segments):
        return True
    # If provenance has non-empty consent already, this is voice pipeline
    if has_valid_consent(result.provenance):
        return True
    # Legacy: segments with voice keys
    return any(has_valid_consent(s.provenance) or s.speaker for s in result.segments)


def ensure_consent(
    input_obj: Resource | Result, component_name: str, *, require_for_resource: bool = True
) -> None:
    """
    Enforce consent_basis for voice processing.

    For Resource: requires consent_basis only for voice-like resources (SPEECH/VIDEO/CHECKPOINT or has voice provenance).
    For Result: requires consent if the Result appears to carry voice data
    (audio artifacts or speaker identifiers). Results without voice signals pass.

    Raises:
        ValueError: If consent is missing with a clear remediation message.
    """
    if isinstance(input_obj, Resource):
        # Only enforce for voice-like resources to avoid blocking TEXT/EVAL_SET
        from lingualdub.core.resource import ResourceKind

        voice_kinds = {
            ResourceKind.SPEECH,
            ResourceKind.VIDEO,
            ResourceKind.CHECKPOINT,
            ResourceKind.SYNTHETIC,
        }
        is_voice_resource = (
            input_obj.kind in voice_kinds
            or has_valid_consent(input_obj.provenance)
            or "consent_basis" in input_obj.provenance
        )
        if not require_for_resource:
            is_voice_resource = False
        if is_voice_resource and not has_valid_consent(input_obj.provenance):
            raise ValueError(  # justified: component input validation — not a framework config error
                f"{component_name}: Resource {input_obj.id!r} (kind={input_obj.kind.value!r}) lacks a valid 'consent_basis' "
                "in provenance. Voice data must carry a recorded consent basis to be processed. "
                "Add provenance={'consent_basis': '...'} to the Resource."
            )
        return
    elif isinstance(input_obj, Result):
        # Check if this Result carries voice data requiring consent
        has_voice = _result_has_voice_signal(input_obj)
        # Provenance is authoritative; metadata consent is fallback only
        provenance = input_obj.provenance or {}
        has_consent = has_valid_consent(provenance)
        # Check segment-level consent as fallback
        if not has_consent and has_voice:
            for seg in input_obj.segments:
                if has_valid_consent(seg.provenance):
                    has_consent = True
                    break
        # Finally consider metadata as last fallback (not authoritative)
        if not has_consent and has_voice:
            meta = input_obj.metadata if isinstance(input_obj.metadata, dict) else {}
            if has_valid_consent(meta):
                has_consent = True
        if has_voice and not has_consent:
            raise ValueError(  # justified: component input validation — not a framework config error
                f"{component_name}: Result lacks valid 'consent_basis' in provenance. "
                "Voice-derived Results must carry provenance={'consent_basis': '...'} "
                "to be processed. Ensure the source Resource had consent and that "
                "provenance was propagated through the pipeline."
            )
