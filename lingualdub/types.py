# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Centralized type aliases and common data contracts.

This module is the single source of truth for shared type definitions used
across the framework. Importing from here avoids scattered ad-hoc aliases
(``dict[str, Any]``, ``str | None``, ``Any`` for tensors, etc.) and keeps
mypy consistent at pipeline integration boundaries.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

__all__ = [
    "PathLike",
    "LanguageCode",
    "MetadataDict",
    "ProvenanceDict",
    "AudioTensor",
    "TimestampInterval",
]

# Filesystem path accepted by ResourceManager, Config, and CLI
PathLike = str | os.PathLike[str] | Path

# ISO 639-3 / BCP-47 language identifier (e.g. "lug", "eng", "nyn")
LanguageCode = str

# Free-form metadata attached to Result, Segment, and Resource.
# Keys are strings, values are JSON-serialisable.
MetadataDict = dict[str, Any]

# Structured provenance record (run_id, pipeline, component_versions, etc.)
ProvenanceDict = dict[str, Any]

# Audio data as loaded by components. In production this is a torch.Tensor
# or numpy.ndarray; offline dummy paths use list[float] or bytes.
# Kept as ``Any`` to avoid hard dependency on torch/numpy for type checking.
AudioTensor = Any

# Time interval for a segment or word alignment
TimestampInterval = tuple[float, float]
