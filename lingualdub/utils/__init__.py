"""
Shared utilities for LingualDub.

This package contains helpers used across the framework: provenance
construction, artifact path management, logging configuration, and
version comparison utilities.
"""

from lingualdub.utils.resource_manager import (
    ResourceManager,
    ChecksumError,
    ResourceNotFoundError,
)

__all__ = ["ResourceManager", "ChecksumError", "ResourceNotFoundError"]
