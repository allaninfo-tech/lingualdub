# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Language and resource registrations.

This package contains the framework's first-party language profiles — structured
resource audits and Language objects for each supported language. Language
registrations are the starting point of the Development Lifecycle: understanding
what a language has before deciding which components to select.

Adding a new language means adding a module here (or in an extension) and
registering it with the framework's Registry.
"""

from lingualdub.languages.luganda import LUGANDA
from lingualdub.languages.nllb import NLLB_CODE_MAP
from lingualdub.languages.runyankole import RUNYANKOLE

__all__: list[str] = [
    "LUGANDA",
    "RUNYANKOLE",
    "NLLB_CODE_MAP",
]
