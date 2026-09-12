# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""Extensions package — contracts and plugin registry."""

from lingualdub.extensions.contracts import (
    ComponentExtension,
    EvaluatorExtension,
    LanguageExtension,
    MiddlewareExtension,
    ResourceExtension,
)
from lingualdub.extensions.plugin import Plugin, PluginRegistry, PluginState

__all__ = [
    "ComponentExtension",
    "LanguageExtension",
    "ResourceExtension",
    "EvaluatorExtension",
    "MiddlewareExtension",
    "Plugin",
    "PluginRegistry",
    "PluginState",
]
