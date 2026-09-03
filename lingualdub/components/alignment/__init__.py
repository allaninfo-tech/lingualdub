"""
Alignment components.

This package contains the base interface for alignment components and any
built-in implementations shipped with the framework. Third-party alignment
implementations are registered through the extension manifest system
and do not need to live in this package.
"""

from lingualdub.components.alignment.forced import DummyForcedAlignmentComponent
from lingualdub.components.alignment.duration import DurationModellingComponent

__all__ = [
    "DummyForcedAlignmentComponent",
    "DurationModellingComponent",
]
