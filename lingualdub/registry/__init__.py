"""
Registry — component, language, and resource discovery.

The Registry is the mechanism for discovering, registering, and resolving
languages, resources, components, and evaluators without editing framework
internals. Extensions ship a manifest declaring what they provide; the
Registry scans installed manifests at startup.

Every entry is versioned. Conflict resolution between extensions that
provide the same capability is governed by the declared conflict policy
rather than implicit precedence.
"""

from lingualdub.registry.registry import Registry

__all__ = ["Registry"]
