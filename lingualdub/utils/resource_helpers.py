# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0
# Internal — not part of public API

"""
Resource acquisition helpers — DRY for Registry+ResourceManager boilerplate.

Previously duplicated 15-line pattern across forced.py, embedding.py, voice_conditioned.py
with inconsistent hasattr checks (resolve vs get) and unreachable branches.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def acquire_resource(
    registry: object | None,
    resource_manager: object | None,
    resource_key: str,
    kind: str = "resource",
):
    """
    Look up a resource in the registry and optionally acquire via ResourceManager.

    Returns (resource, resource_path_or_None) tuple. Never raises; logs debug on failure.
    """
    if registry is None:
        logger.debug(
            "acquire_resource: registry is None for %r — deterministic fallback", resource_key
        )
        return None, None

    resource = None
    # Registry lookup — canonical is resolve(kind, key); no get fallback (dead code removed)
    if hasattr(registry, "resolve"):
        try:
            resource = registry.resolve(kind, resource_key)  # type: ignore[attr-defined]
        except Exception as exc:
            logger.debug("Registry resolve(%r, %r) failed: %s", kind, resource_key, exc)

    if resource is None:
        logger.debug("Resource %r not found in registry.", resource_key)
        return None, None

    # Acquire via ResourceManager if URL/checksum present
    resource_path = None
    if resource_manager is not None and hasattr(resource_manager, "get"):
        try:
            prov = getattr(resource, "provenance", {}) or {}
            url = prov.get("url")
            checksum = prov.get("checksum")
            if url and checksum:
                path = resource_manager.get(resource.id, resource.version, url, checksum)
                resource_path = str(path)
                logger.info("Acquired resource %r via ResourceManager: %s", resource_key, path)
        except Exception as exc:
            logger.debug("ResourceManager acquisition for %r: %s", resource_key, exc)

    if resource is not None:
        logger.info("Loaded resource %r", getattr(resource, "id", None))
    return resource, resource_path
