"""
Extension manifest scanner.

Discovers installed LingualDub extensions and loads their component,
language, and resource registrations into a Registry without requiring
any hardcoded imports in the framework core.

Manifest format (lingualdub.manifest.json):
    {
        "name": "my-extension",
        "version": "1.0.0",
        "entries": [
            {
                "kind": "component",
                "key": "my_asr",
                "module": "my_extension.asr",
                "attr": "MyASRComponent",
                "version": "1.0.0",
                "metadata": {}
            }
        ]
    }

Extensions place this file in their package root (alongside __init__.py).
The scanner discovers all installed packages that contain a
lingualdub.manifest.json file and registers each declared entry.
"""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
from typing import List, Optional

from lingualdub.registry.registry import Registry, RegistryError

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = "lingualdub.manifest.json"

REQUIRED_ENTRY_FIELDS = {"kind", "key", "module", "attr", "version"}


class ManifestError(Exception):
    """Raised when a manifest file is malformed or invalid."""


def _validate_entry(entry: dict, manifest_path: Path, index: int) -> None:
    """Validate a single manifest entry dict."""
    missing = REQUIRED_ENTRY_FIELDS - set(entry.keys())
    if missing:
        raise ManifestError(
            f"Manifest {manifest_path}: entry[{index}] is missing required fields: "
            f"{sorted(missing)}. All entries must have: {sorted(REQUIRED_ENTRY_FIELDS)}."
        )
    for field in ("kind", "key", "module", "attr", "version"):
        if not isinstance(entry[field], str) or not entry[field]:
            raise ManifestError(
                f"Manifest {manifest_path}: entry[{index}].{field!r} must be a non-empty string."
            )


class ManifestScanner:
    """
    Scans installed packages for LingualDub extension manifests and
    registers all declared entries into a Registry.

    Usage:
        registry = Registry()
        scanner = ManifestScanner(registry)
        scanner.scan()               # discovers all installed extensions
        scanner.load(path)           # loads a single manifest file by path
    """

    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def load(self, manifest_path: Path) -> int:
        """
        Parse and register all entries from a single manifest file.

        Args:
            manifest_path: Path to a lingualdub.manifest.json file.

        Returns:
            Number of entries successfully registered.

        Raises:
            ManifestError: If the file is malformed or a required field is missing.
        """
        try:
            raw = manifest_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ManifestError(f"Cannot read manifest at {manifest_path}: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ManifestError(
                f"Manifest {manifest_path} is not valid JSON: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ManifestError(
                f"Manifest {manifest_path}: top-level value must be a JSON object."
            )

        entries = data.get("entries")
        if entries is None:
            raise ManifestError(
                f"Manifest {manifest_path}: missing required top-level key 'entries'."
            )
        if not isinstance(entries, list):
            raise ManifestError(
                f"Manifest {manifest_path}: 'entries' must be a JSON array."
            )

        registered = 0
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ManifestError(
                    f"Manifest {manifest_path}: entry[{i}] must be a JSON object."
                )
            _validate_entry(entry, manifest_path, i)

            try:
                module = importlib.import_module(entry["module"])
                impl = getattr(module, entry["attr"])
            except ImportError as exc:
                raise ManifestError(
                    f"Manifest {manifest_path}: entry[{i}] cannot import "
                    f"'{entry['module']}': {exc}"
                ) from exc
            except AttributeError as exc:
                raise ManifestError(
                    f"Manifest {manifest_path}: entry[{i}] module "
                    f"'{entry['module']}' has no attribute '{entry['attr']}': {exc}"
                ) from exc

            self.registry.register(
                kind=entry["kind"],
                key=entry["key"],
                impl=impl,
                version=entry["version"],
                metadata=entry.get("metadata", {}),
            )
            logger.debug(
                "Registered %r/%r@%s from %s",
                entry["kind"], entry["key"], entry["version"], manifest_path.name,
            )
            registered += 1

        logger.info(
            "Loaded %d entries from manifest %s", registered, manifest_path.name
        )
        return registered

    def scan(self, search_paths: Optional[List[Path]] = None) -> int:
        """
        Discover and load all extension manifests from installed packages.

        Searches sys.path (or the provided search_paths) for directories
        containing a lingualdub.manifest.json file.

        Args:
            search_paths: Optional list of directories to search. Defaults
                to all directories currently on sys.path.

        Returns:
            Total number of entries registered across all discovered manifests.
        """
        import sys

        if search_paths is not None:
            paths = [Path(p).resolve() for p in search_paths]
        else:
            # Build search paths from sys.path; empty string means cwd
            paths = []
            for p in sys.path:
                if not p or p == ".":
                    resolved = Path.cwd().resolve()
                else:
                    resolved = Path(p).resolve()
                if resolved.is_dir() and resolved not in paths:
                    paths.append(resolved)
        total = 0
        seen: set = set()  # Deduplicate resolved manifest paths
        # Directories to prune during walk (heavy or irrelevant)
        prune_dirs = {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            ".mypy_cache",
            ".pytest_cache",
            "node_modules",
            ".tox",
            "build",
            "dist",
            "website",
        }

        for base in paths:
            if not base.is_dir():
                continue
            # Limit search depth to 3 levels to avoid crawling entire site-packages tree deeply
            # Use os.walk with pruning instead of unbounded rglob
            import os

            for root, dirs, files in os.walk(base, topdown=True):
                # Prune heavy dirs
                dirs[:] = [d for d in dirs if d not in prune_dirs and not d.startswith(".")]
                # Depth check: relative depth from base
                try:
                    rel = Path(root).relative_to(base)
                    depth = len(rel.parts)
                except ValueError:
                    depth = 0
                if depth > 3:
                    dirs[:] = []
                    continue
                if MANIFEST_FILENAME in files:
                    manifest_path = Path(root) / MANIFEST_FILENAME
                    resolved = manifest_path.resolve()
                    if resolved in seen:
                        continue
                    seen.add(resolved)
                    try:
                        total += self.load(manifest_path)
                    except ManifestError as exc:
                        logger.warning("Skipping malformed manifest: %s", exc)

        return total
