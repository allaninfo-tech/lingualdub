# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Asr components.

This package contains the base interface for asr components and any
built-in implementations shipped with the framework. Third-party asr
implementations are registered through the extension manifest system
and do not need to live in this package.
"""

from lingualdub.components.asr.base import ASRComponent
from lingualdub.components.asr.dummy import DummyASRComponent
from lingualdub.components.asr.runyankole import RunyankoleASRComponent
from lingualdub.components.asr.sunbird import SunbirdASRComponent
from lingualdub.components.asr.whisper import WhisperASRComponent

__all__: list[str] = [
    "ASRComponent",
    "DummyASRComponent",
    "RunyankoleASRComponent",
    "SunbirdASRComponent",
    "WhisperASRComponent",
]
