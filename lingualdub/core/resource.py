# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Resource abstraction.

Represents any data asset used or produced by the framework — speech recordings,
text corpora, parallel translations, lexicons, pronunciation resources, model
checkpoints, or evaluation sets. Provenance is not optional metadata; it is the
mechanism that makes evaluation and reproducibility enforceable across runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from lingualdub.types import LanguageCode, MetadataDict, PathLike, ProvenanceDict
from lingualdub.utils.validation import (
    require_non_empty_string,
    validate_language_code,
    validate_version_string,
)


class ResourceKind(str, Enum):
    """Enumeration of supported resource types."""

    SPEECH = "speech"
    TEXT = "text"
    PARALLEL_TEXT = "parallel_text"
    LEXICON = "lexicon"
    CHECKPOINT = "checkpoint"
    EVAL_SET = "eval_set"
    SYNTHETIC = "synthetic"
    ALIGNMENT = "alignment"
    VIDEO = "video"
    OTHER = "other"


@dataclass
class Resource:
    """
    A data asset registered with the framework.

    Attributes:
        id: Unique identifier for this resource (e.g. "lug_speech_v2").
        kind: The type of asset this resource represents.
        language: Language code this resource belongs to.
        version: Version string for this resource.
        provenance: Structured record of how this resource was created or obtained.
            Required fields include 'source' and 'license'. Voice resources must
            also carry a 'consent_basis' field to be compatible with voice-transfer
            or voice-retention components.
        quality_flags: Known quality issues or caveats (e.g. ["weak_transcripts"]).
        compatible_components: Component names verified to work with this resource.
        path: Local or remote path to the resource data. Optional at registration;
            required before use.
    """

    id: str
    kind: ResourceKind
    language: LanguageCode
    version: str
    provenance: ProvenanceDict = field(default_factory=dict)
    quality_flags: list[str] = field(default_factory=list)
    compatible_components: list[str] = field(default_factory=list)
    path: PathLike | None = None
    metadata: MetadataDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_empty_string(self.id, "id")
        require_non_empty_string(self.language, "language")
        require_non_empty_string(self.version, "version")
        validate_language_code(self.language)
        validate_version_string(self.version)

    @property
    def has_consent(self) -> bool:
        """
        Returns True if this resource carries a recorded consent basis.
        Required for compatibility with voice-transfer and voice-retention components.
        Whitespace-only values are not considered valid consent.
        """
        val = self.provenance.get("consent_basis")
        return isinstance(val, str) and bool(val.strip())

    def to_dict(self) -> dict:
        """Serialize this Resource to a JSON-compatible dictionary.

        ``path`` is always serialized as a string (or ``None``) so that
        ``pathlib.Path`` values round-trip correctly through JSON.
        """
        # PathLike may be a pathlib.Path — serialize to string for JSON
        path_val: str | None = None if self.path is None else str(self.path)

        return {
            "id": self.id,
            "kind": self.kind.value,
            "language": self.language,
            "version": self.version,
            "provenance": dict(self.provenance),
            "quality_flags": list(self.quality_flags),
            "compatible_components": list(self.compatible_components),
            "path": path_val,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Resource:
        """Deserialize a Resource from a dictionary produced by :meth:`to_dict`.

        Behaviour mirrors :meth:`Language.from_dict` — explicit schema validation,
        typed errors, and forward-compatible preservation of unknown keys in
        ``metadata``.

        Required keys: ``id``, ``kind``, ``language``, ``version``.
        """
        from pathlib import Path as _Path

        from lingualdub.exceptions import SerializationError

        if not isinstance(data, dict):
            raise SerializationError(
                f"Resource.from_dict expects a dict, got {type(data).__name__}: {data!r}.",
                field="data",
                code="RES_DESER_001",
            )

        known_keys = {
            "id",
            "kind",
            "language",
            "version",
            "provenance",
            "quality_flags",
            "compatible_components",
            "path",
            "metadata",
        }
        for key in ("id", "kind", "language", "version"):
            if key not in data:
                raise SerializationError(
                    f"Missing required field '{key}' for Resource.",
                    field=key,
                    code="RES_DESER_002",
                    context={"data_keys": list(data.keys())},
                )

        # Validate kind is a recognised enum value — provide clear error rather
        # than bare ValueError from Enum(value)
        raw_kind = data["kind"]
        if not isinstance(raw_kind, str):
            raise SerializationError(
                f"Field 'kind' must be a string, got {type(raw_kind).__name__}: {raw_kind!r}.",
                field="kind",
                code="RES_DESER_003",
            )
        valid_kinds = [k.value for k in ResourceKind]
        if raw_kind not in valid_kinds:
            raise SerializationError(
                f"Field 'kind' must be one of {valid_kinds!r}, got {raw_kind!r}.",
                field="kind",
                code="RES_DESER_003",
            )

        # Type checks for optional collections
        if (
            "provenance" in data
            and data["provenance"] is not None
            and not isinstance(data["provenance"], dict)
        ):
            raise SerializationError(
                f"Field 'provenance' must be a dict, got {type(data['provenance']).__name__}: {data['provenance']!r}.",
                field="provenance",
                code="RES_DESER_003",
            )
        for key in ("quality_flags", "compatible_components"):
            if key in data and data[key] is not None and not isinstance(data[key], list):
                raise SerializationError(
                    f"Field '{key}' must be a list, got {type(data[key]).__name__}: {data[key]!r}.",
                    field=key,
                    code="RES_DESER_003",
                )
        if (
            "metadata" in data
            and data["metadata"] is not None
            and not isinstance(data["metadata"], dict)
        ):
            raise SerializationError(
                f"Field 'metadata' must be a dict, got {type(data['metadata']).__name__}: {data['metadata']!r}.",
                field="metadata",
                code="RES_DESER_003",
            )

        # Path may be string, Path, os.PathLike or None — normalize to
        # string/None; to_dict will normalise again.  Any other type is a schema
        # error so we surface SerializationError instead of a later cryptic failure.
        import os as _os

        raw_path = data.get("path")
        if raw_path is not None and not isinstance(raw_path, (str, _Path, _os.PathLike)):
            raise SerializationError(
                f"Field 'path' must be a string, path-like, or None, got {type(raw_path).__name__}: {raw_path!r}.",
                field="path",
                code="RES_DESER_003",
            )

        # Preserve unknown keys in metadata for schema evolution
        base_metadata = dict(data.get("metadata") or {})
        unknown = {k: v for k, v in data.items() if k not in known_keys}
        merged_metadata = {**base_metadata, **unknown} if unknown else base_metadata

        return cls(
            id=data["id"],
            kind=ResourceKind(raw_kind),
            language=data["language"],
            version=data["version"],
            provenance=dict(data.get("provenance") or {}),
            quality_flags=list(data.get("quality_flags") or []),
            compatible_components=list(data.get("compatible_components") or []),
            path=str(raw_path) if isinstance(raw_path, _Path) else raw_path,
            metadata=merged_metadata,
        )

    def __repr__(self) -> str:
        return f"Resource(id={self.id!r}, kind={self.kind.value!r}, language={self.language!r}, version={self.version!r})"
