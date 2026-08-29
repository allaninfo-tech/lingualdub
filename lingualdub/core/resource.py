"""
Resource abstraction.

Represents any data asset used or produced by the framework — speech recordings,
text corpora, parallel translations, lexicons, pronunciation resources, model
checkpoints, or evaluation sets. Provenance is not optional metadata; it is the
mechanism that makes evaluation and reproducibility enforceable across runs.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


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
    language: str
    version: str
    provenance: dict = field(default_factory=dict)
    quality_flags: List[str] = field(default_factory=list)
    compatible_components: List[str] = field(default_factory=list)
    path: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Resource.id must not be empty.")
        if not self.language:
            raise ValueError("Resource.language must not be empty.")

    @property
    def has_consent(self) -> bool:
        """
        Returns True if this resource carries a recorded consent basis.
        Required for compatibility with voice-transfer and voice-retention components.
        """
        return bool(self.provenance.get("consent_basis"))

    def __repr__(self) -> str:
        return f"Resource(id={self.id!r}, kind={self.kind.value!r}, language={self.language!r}, version={self.version!r})"
