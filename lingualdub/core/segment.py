# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Segment — the shared unit of data between components.

A Segment is the atomic unit exchanged between pipeline stages. It carries
timing, text, per-segment language, speaker identity, confidence, and
provenance. Per-segment language is authoritative at the segment level —
not just at the file level — which is what makes code-switching a structural
property of the data rather than an annotation added after the fact.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lingualdub.types import LanguageCode, MetadataDict, ProvenanceDict
from lingualdub.utils.validation import (
    require_non_empty_string,
    validate_language_code,
)


@dataclass(frozen=True)
class Segment:
    """
    An atomic unit of speech or text data.

    This is an **immutable value object** — all fields are validated at
    construction and the instance is frozen. To produce a modified copy use
    :meth:`replace`.

    Attributes:
        start: Start time in seconds. Must be ``>= 0``. Invariant: ``end >= start``.
        end: End time in seconds. Must be ``>= start``. Duration is ``end - start``.
        text: Transcribed, translated, or synthesised text for this segment.
            May be empty (``\"\"``) for pure timing segments, but if non-empty
            must be a non-whitespace string.
        language: Language code for this specific segment. Authoritative per-segment,
            not inherited from the containing :class:`Result`. Validated as
            ISO 639-3 (``^[a-z]{2,3}$``). Code-switch detection populates this
            field; pipeline routing acts on it.
        speaker: Speaker identifier or reference for this segment, if known.
        confidence: Model confidence for this segment, in ``[0.0, 1.0]`` when set.
        source_language: Original language before translation, if applicable.
            When present, validated as language code.
        provenance: Model or component identifiers that produced this segment.
            Free-form dict, not validated beyond type.
        metadata: Extensible key-value store for component-specific data
            (e.g. ``word_timestamps``, ``fitting_strategy``).
    """

    start: float
    end: float
    text: str
    language: LanguageCode
    speaker: str | None = None
    confidence: float | None = None
    source_language: LanguageCode | None = None
    provenance: ProvenanceDict = field(default_factory=dict)
    metadata: MetadataDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        import math

        from lingualdub.exceptions import ConfigurationValidationError

        # start / end must be numbers (reject bool) and finite
        for field_name in ("start", "end"):
            val = getattr(self, field_name)
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ConfigurationValidationError(
                    f"Field {field_name!r} must be a number, got {type(val).__name__}: {val!r}.",
                    field=field_name,
                )
            if not math.isfinite(float(val)):
                raise ConfigurationValidationError(
                    f"Field {field_name!r} must be finite, got {val!r}.", field=field_name
                )
        if self.start < 0:
            raise ConfigurationValidationError(
                f"Field 'start' must be >= 0, got {self.start!r}.", field="start"
            )
        if self.end < self.start:
            raise ConfigurationValidationError(
                f"Field 'end' must be >= start ({self.start!r}), got {self.end!r}.",
                field="end",
            )
        # Validate core string fields via shared helper
        if not isinstance(self.text, str):
            raise ConfigurationValidationError(
                f"Field 'text' must be a string, got {type(self.text).__name__}: {self.text!r}.",
                field="text",
            )
        if self.text:
            require_non_empty_string(self.text, "text")
        require_non_empty_string(self.language, "language")
        validate_language_code(self.language)
        if self.source_language is not None:
            require_non_empty_string(self.source_language, "source_language")
            validate_language_code(self.source_language)
        if self.speaker is not None and not isinstance(self.speaker, str):
            raise ConfigurationValidationError(
                f"Field 'speaker' must be a string or None, got {type(self.speaker).__name__}: {self.speaker!r}.",
                field="speaker",
            )
        if self.speaker is not None and self.speaker != "" and not self.speaker.strip():
            raise ConfigurationValidationError(
                "Field 'speaker' must be non-whitespace when set.", field="speaker"
            )
        if not isinstance(self.provenance, dict):
            raise ConfigurationValidationError(
                f"Field 'provenance' must be a dict, got {type(self.provenance).__name__}: {self.provenance!r}.",
                field="provenance",
            )
        if not isinstance(self.metadata, dict):
            raise ConfigurationValidationError(
                f"Field 'metadata' must be a dict, got {type(self.metadata).__name__}: {self.metadata!r}.",
                field="metadata",
            )
        # confidence if provided must be in [0,1] and finite
        if self.confidence is not None:
            if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
                raise ConfigurationValidationError(
                    f"Field 'confidence' must be a number in [0, 1], got {type(self.confidence).__name__}: {self.confidence!r}.",
                    field="confidence",
                )
            cf = float(self.confidence)
            if not math.isfinite(cf) or not (0.0 <= cf <= 1.0):
                raise ConfigurationValidationError(
                    f"Field 'confidence' must be finite in [0, 1], got {self.confidence!r}.",
                    field="confidence",
                )
        # Freeze dict fields shallowly by copying and preventing mutation via object.__setattr__
        # Use copy to break external reference sharing
        object.__setattr__(self, "provenance", dict(self.provenance))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def replace(self, **changes) -> Segment:
        """
        Return a new :class:`Segment` with the given field changes.

        Args:
            **changes: Field names and new values. Unknown fields raise ``TypeError``.
                Invalid values (e.g. ``start=-1`` or ``language=\"bad_code\"``)
                raise :class:`ConfigurationValidationError`.

        Returns:
            A new, validated :class:`Segment` instance. The original is unchanged.

        Example:
            >>> seg = Segment(start=0, end=1, text=\"hi\", language=\"lug\")
            >>> seg2 = seg.replace(text=\"hello\", language=\"eng\")
        """
        from dataclasses import replace as dc_replace

        # Validate known field names early for clearer error
        valid_fields = set(self.__dataclass_fields__.keys())
        for k in changes:
            if k not in valid_fields:
                raise TypeError(  # justified: Python type contract for unexpected replace field
                    f"Segment.replace() got unexpected field {k!r}"
                )

        # Use dataclasses.replace which bypasses frozen __setattr__ via object.__setattr__
        new_obj = dc_replace(self, **changes)
        # Trigger validation via __post_init__ on new_obj
        try:
            new_obj.__post_init__()  # type: ignore[attr-defined]
        except Exception:
            raise
        return new_obj

    @property
    def duration(self) -> float:
        """Duration of this segment in seconds."""
        return self.end - self.start

    def to_dict(self) -> dict:
        """Serialize this Segment to a JSON-compatible dictionary.

        The returned dictionary is a deep copy suitable for JSON serialization
        and round-trip via :meth:`from_dict`.
        """
        import copy

        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "language": self.language,
            "speaker": self.speaker,
            "confidence": self.confidence,
            "source_language": self.source_language,
            "provenance": copy.deepcopy(self.provenance),
            "metadata": copy.deepcopy(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Segment:
        """Deserialize a Segment from a dictionary produced by :meth:`to_dict`.

        Validation mirrors :meth:`Language.from_dict` — required keys are checked
        explicitly, types are validated before construction, and unknown keys are
        preserved in ``metadata`` for forward compatibility.

        Required keys: ``start``, ``end``, ``text``, ``language``.

        Raises:
            SerializationError: If ``data`` is not a dict, required keys are
                missing, or a field has the wrong type / violates invariants
                (e.g. ``start`` not numeric, ``end < start``, ``confidence``
                out of range).
            ConfigurationValidationError: If a language code is malformed
                (propagated from the central validator).
        """
        from lingualdub.exceptions import SerializationError

        if not isinstance(data, dict):
            raise SerializationError(
                f"Segment.from_dict expects a dict, got {type(data).__name__}: {data!r}.",
                field="data",
                code="SEG_DESER_001",
            )

        known_keys = {
            "start",
            "end",
            "text",
            "language",
            "speaker",
            "confidence",
            "source_language",
            "provenance",
            "metadata",
        }
        for key in ("start", "end", "text", "language"):
            if key not in data:
                raise SerializationError(
                    f"Missing required field '{key}' for Segment.",
                    field=key,
                    code="SEG_DESER_002",
                    context={"data_keys": list(data.keys())},
                )

        # Validate numeric types for start / end before construction so the
        # error is a clear SerializationError naming the field rather than a
        # bare TypeError from ``<`` comparison on a string.
        for key in ("start", "end"):
            val = data[key]
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise SerializationError(
                    f"Field '{key}' must be a number, got {type(val).__name__}: {val!r}.",
                    field=key,
                    code="SEG_DESER_003",
                )

        start = float(data["start"])
        end = float(data["end"])
        if start < 0:
            raise SerializationError(
                f"Field 'start' must be >= 0, got {start!r}.",
                field="start",
                code="SEG_DESER_003",
            )
        if end < start:
            raise SerializationError(
                f"Field 'end' must be >= start ({start!r}), got {end!r}.",
                field="end",
                code="SEG_DESER_003",
            )

        text = data["text"]
        if not isinstance(text, str):
            raise SerializationError(
                f"Field 'text' must be a string, got {type(text).__name__}: {text!r}.",
                field="text",
                code="SEG_DESER_003",
            )

        language = data["language"]
        if not isinstance(language, str):
            raise SerializationError(
                f"Field 'language' must be a string, got {type(language).__name__}: {language!r}.",
                field="language",
                code="SEG_DESER_003",
            )

        # Optional field type checks
        if (
            "speaker" in data
            and data["speaker"] is not None
            and not isinstance(data["speaker"], str)
        ):
            raise SerializationError(
                f"Field 'speaker' must be a string or None, got {type(data['speaker']).__name__}: {data['speaker']!r}.",
                field="speaker",
                code="SEG_DESER_003",
            )
        if "confidence" in data and data["confidence"] is not None:
            conf = data["confidence"]
            if isinstance(conf, bool) or not isinstance(conf, (int, float)):
                raise SerializationError(
                    f"Field 'confidence' must be a number in [0, 1] or None, got {type(conf).__name__}: {conf!r}.",
                    field="confidence",
                    code="SEG_DESER_003",
                )
            if not (0.0 <= float(conf) <= 1.0):
                raise SerializationError(
                    f"Field 'confidence' must be in [0, 1], got {conf!r}.",
                    field="confidence",
                    code="SEG_DESER_003",
                )
        if (
            "source_language" in data
            and data["source_language"] is not None
            and not isinstance(data["source_language"], str)
        ):
            raise SerializationError(
                f"Field 'source_language' must be a string or None, got {type(data['source_language']).__name__}: {data['source_language']!r}.",
                field="source_language",
                code="SEG_DESER_003",
            )
        if (
            "provenance" in data
            and data["provenance"] is not None
            and not isinstance(data["provenance"], dict)
        ):
            raise SerializationError(
                f"Field 'provenance' must be a dict, got {type(data['provenance']).__name__}: {data['provenance']!r}.",
                field="provenance",
                code="SEG_DESER_003",
            )
        if (
            "metadata" in data
            and data["metadata"] is not None
            and not isinstance(data["metadata"], dict)
        ):
            raise SerializationError(
                f"Field 'metadata' must be a dict, got {type(data['metadata']).__name__}: {data['metadata']!r}.",
                field="metadata",
                code="SEG_DESER_003",
            )

        # Preserve unknown keys in metadata for schema evolution (no shadowing)
        base_metadata = dict(data.get("metadata") or {})
        unknown = {k: v for k, v in data.items() if k not in known_keys}
        # Base metadata wins on collision to avoid data loss
        merged_metadata = {**unknown, **base_metadata} if unknown else base_metadata

        # Construction delegates language-code and confidence invariants to
        # __post_init__ / validators (ConfigurationValidationError).  We pass
        # the already-validated numeric fields as floats to keep types stable.
        return cls(
            start=start,
            end=end,
            text=text,
            language=language,
            speaker=data.get("speaker"),
            confidence=data.get("confidence"),
            source_language=data.get("source_language"),
            provenance=dict(data.get("provenance") or {}),
            metadata=merged_metadata,
        )

    def __repr__(self) -> str:
        return (
            f"Segment(start={self.start}, end={self.end}, "
            f"language={self.language!r}, speaker={self.speaker!r})"
        )
