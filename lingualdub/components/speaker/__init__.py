# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Speaker components.

This package contains the base interface for speaker components and any
built-in implementations shipped with the framework. Third-party speaker
implementations are registered through the extension manifest system
and do not need to live in this package.
"""

from lingualdub.components.speaker.base import SpeakerComponent
from lingualdub.components.speaker.embedding import SpeakerEmbeddingComponent

__all__: list[str] = [
    "SpeakerComponent",
    "SpeakerEmbeddingComponent",
]
