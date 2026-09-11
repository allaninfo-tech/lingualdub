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
        """Serialize this Resource to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "kind": self.kind.value,
            "language": self.language,
            "version": self.version,
            "provenance": dict(self.provenance),
            "quality_flags": list(self.quality_flags),
            "compatible_components": list(self.compatible_components),
            "path": self.path,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Resource:
        """Deserialize a Resource from a dictionary produced by to_dict()."""
        return cls(
            id=data["id"],
            kind=ResourceKind(data["kind"]),
            language=data["language"],
            version=data["version"],
            provenance=data.get("provenance", {}),
            quality_flags=data.get("quality_flags", []),
            compatible_components=data.get("compatible_components", []),
            path=data.get("path"),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return f"Resource(id={self.id!r}, kind={self.kind.value!r}, language={self.language!r}, version={self.version!r})"
