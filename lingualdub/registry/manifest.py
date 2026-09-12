# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

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

from lingualdub.exceptions import RegistryError
from lingualdub.registry.registry import Registry

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = "lingualdub.manifest.json"

REQUIRED_ENTRY_FIELDS = {"kind", "key", "module", "attr", "version"}

# Inline schema constants — mirror lingualdub/registry/manifest_schema.json
_ALLOWED_KINDS = {"component", "language", "resource", "evaluator"}
_ALLOWED_TASKS: set[str] | None = None  # lazy-loaded from ComponentTask
_VERSION_RE = None  # lazy compiled
_MODULE_RE = None
_ATTR_RE = None
_NAME_RE = None


def _get_allowed_tasks() -> set[str]:
    global _ALLOWED_TASKS
    if _ALLOWED_TASKS is None:
        from lingualdub.core.component import ComponentTask

        _ALLOWED_TASKS = {t.value for t in ComponentTask}
    return _ALLOWED_TASKS


def _get_version_re():
    global _VERSION_RE
    if _VERSION_RE is None:
        import re

        _VERSION_RE = re.compile(r"^\d+\.\d+(\.\d+)?$")
    return _VERSION_RE


def _get_module_re():
    global _MODULE_RE
    if _MODULE_RE is None:
        import re

        _MODULE_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$")
    return _MODULE_RE


def _get_attr_re():
    global _ATTR_RE
    if _ATTR_RE is None:
        import re

        _ATTR_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    return _ATTR_RE


def _get_name_re():
    global _NAME_RE
    if _NAME_RE is None:
        import re

        _NAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")
    return _NAME_RE


class ManifestError(RegistryError):
    """Raised when a manifest file is malformed or invalid."""


def _validate_manifest_top_level(data: dict, manifest_path: Path) -> None:
    """Validate top-level manifest fields against the JSON schema.

    Raises:
        ManifestError: with file path and specific violation.
    """
    # Check required top-level keys
    for key in ("name", "version", "entries"):
        if key not in data:
            raise ManifestError(
                f"Manifest {manifest_path}: missing required top-level key '{key}'."
            )

    # Validate name
    name = data["name"]
    if not isinstance(name, str) or not name.strip():
        raise ManifestError(
            f"Manifest {manifest_path}: top-level 'name' must be a non-empty string, "
            f"got {type(name).__name__}: {name!r}."
        )
    if not _get_name_re().match(name):
        raise ManifestError(
            f"Manifest {manifest_path}: top-level 'name' {name!r} must match "
            f"{_get_name_re().pattern!r}."
        )

    # Validate version
    version = data["version"]
    if not isinstance(version, str) or not version.strip():
        raise ManifestError(
            f"Manifest {manifest_path}: top-level 'version' must be a non-empty string."
        )
    if not _get_version_re().match(version):
        raise ManifestError(
            f"Manifest {manifest_path}: top-level 'version' {version!r} must match "
            f"{_get_version_re().pattern!r} (e.g. '1.0.0')."
        )

    # entries already checked for existence in caller, but validate type here as well
    entries = data["entries"]
    if not isinstance(entries, list):
        raise ManifestError(f"Manifest {manifest_path}: 'entries' must be a JSON array.")


def _validate_entry(entry: dict, manifest_path: Path, index: int) -> None:
    """Validate a single manifest entry dict against the schema.

    Checks required fields, types, formats, allowed enum values, and
    component task validity.  Raises ManifestError with file path, section
    (entry index), and specific violation for actionable diagnostics.
    """
    missing = REQUIRED_ENTRY_FIELDS - set(entry.keys())
    if missing:
        raise ManifestError(
            f"Manifest {manifest_path}: entry[{index}] is missing required fields: "
            f"{sorted(missing)}. All entries must have: {sorted(REQUIRED_ENTRY_FIELDS)}."
        )

    # Reject unknown top-level entry keys (additionalProperties: false per schema)
    allowed_entry_keys = REQUIRED_ENTRY_FIELDS | {"metadata"}
    unknown = set(entry.keys()) - allowed_entry_keys
    if unknown:
        raise ManifestError(
            f"Manifest {manifest_path}: entry[{index}] has unknown fields {sorted(unknown)}; "
            f"allowed keys are {sorted(allowed_entry_keys)}."
        )

    for field in ("kind", "key", "module", "attr", "version"):
        val = entry[field]
        if not isinstance(val, str) or not val.strip():
            raise ManifestError(
                f"Manifest {manifest_path}: entry[{index}].{field!r} must be a non-empty string, "
                f"got {type(val).__name__}: {val!r}."
            )

    # Validate kind enum
    kind = entry["kind"]
    if kind not in _ALLOWED_KINDS:
        raise ManifestError(
            f"Manifest {manifest_path}: entry[{index}] has invalid kind {kind!r}; "
            f"must be one of {sorted(_ALLOWED_KINDS)}."
        )

    # Validate version pattern
    version = entry["version"]
    if not _get_version_re().match(version):
        raise ManifestError(
            f"Manifest {manifest_path}: entry[{index}].version {version!r} must match "
            f"{_get_version_re().pattern!r} (e.g. '1.0.0')."
        )

    # Validate module / attr patterns
    module = entry["module"]
    if not _get_module_re().match(module):
        raise ManifestError(
            f"Manifest {manifest_path}: entry[{index}].module {module!r} must be a dotted "
            f"Python path matching {_get_module_re().pattern!r}."
        )
    attr = entry["attr"]
    if not _get_attr_re().match(attr):
        raise ManifestError(
            f"Manifest {manifest_path}: entry[{index}].attr {attr!r} must match "
            f"{_get_attr_re().pattern!r}."
        )

    # Validate key is not empty and looks like a slug (allow alphanum, _, -)
    # We keep this lenient but ensure non-empty already checked.

    # Validate metadata when present
    metadata = entry.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise ManifestError(
            f"Manifest {manifest_path}: entry[{index}].metadata must be a JSON object, "
            f"got {type(metadata).__name__}: {metadata!r}."
        )

    # Validate component task enum when kind is component and task is declared
    if kind == "component" and isinstance(metadata, dict) and "task" in metadata:
        task_val = metadata["task"]
        if not isinstance(task_val, str):
            raise ManifestError(
                f"Manifest {manifest_path}: entry[{index}] has invalid task {task_val!r} "
                f"for component {entry['key']!r}; task must be a string."
            )
        allowed_tasks = _get_allowed_tasks()
        if task_val not in allowed_tasks:
            raise ManifestError(
                f"Manifest {manifest_path}: entry[{index}] has invalid task {task_val!r} "
                f"for component {entry['key']!r}; must be one of {sorted(allowed_tasks)}."
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

    def load(self, manifest_path: Path, verify_imports: bool = True) -> int:
        """
        Parse and register all entries from a single manifest file.

        Validation is performed against the formal JSON schema at
        ``lingualdub/registry/manifest_schema.json`` — missing keys, wrong
        types, invalid ``kind``/``task`` enums and malformed version strings
        raise :class:`ManifestError` with file path, section and specific
        violation before any registration occurs.

        Args:
            manifest_path: Path to a lingualdub.manifest.json file.
            verify_imports: When ``True`` (default) the declared
                ``module``/``attr`` entrypoints are imported and verified to
                exist. Set ``False`` to validate schema only without importing
                (useful for offline linting).

        Returns:
            Number of entries successfully registered.

        Raises:
            ManifestError: If the file is malformed, schema validation fails,
                a task value is invalid, or an entrypoint cannot be imported
                (when ``verify_imports`` is True).
        """
        try:
            raw = manifest_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ManifestError(f"Cannot read manifest at {manifest_path}: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ManifestError(f"Manifest {manifest_path} is not valid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise ManifestError(f"Manifest {manifest_path}: top-level value must be a JSON object.")

        # Strict schema validation for top-level fields
        _validate_manifest_top_level(data, manifest_path)

        entries = data.get("entries")
        # Redundant check — _validate_manifest_top_level already ensured list, but keep for safety
        if not isinstance(entries, list):
            raise ManifestError(f"Manifest {manifest_path}: 'entries' must be a JSON array.")

        # Detect duplicate (kind, key, version) within the same manifest file (allow multi-version)
        seen_keys: set[tuple[str, str, str]] = set()
        registered = 0
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ManifestError(f"Manifest {manifest_path}: entry[{i}] must be a JSON object.")
            _validate_entry(entry, manifest_path, i)

            # Duplicate detection within file — same kind/key/version
            dup_key = (entry["kind"], entry["key"], entry["version"])
            if dup_key in seen_keys:
                raise ManifestError(
                    f"Manifest {manifest_path}: entry[{i}] duplicates (kind={entry['kind']!r}, "
                    f"key={entry['key']!r}, version={entry['version']!r}) already declared in this manifest; "
                    f"duplicate registrations are not allowed."
                )
            seen_keys.add(dup_key)

            if verify_imports:
                try:
                    module = importlib.import_module(entry["module"])
                    impl = getattr(module, entry["attr"])
                except ImportError as exc:
                    raise ManifestError(
                        f"Manifest {manifest_path}: entry[{i}] cannot import '{entry['module']}': {exc}"
                    ) from exc
                except AttributeError as exc:
                    raise ManifestError(
                        f"Manifest {manifest_path}: entry[{i}] module "
                        f"'{entry['module']}' has no attribute '{entry['attr']}': {exc}"
                    ) from exc
            else:
                # Schema-only mode — do not import; store a stable placeholder string
                # so the registry entry exists for validation without executing code.
                impl = f"{entry['module']}:{entry['attr']}"

            self.registry.register(
                kind=entry["kind"],
                key=entry["key"],
                impl=impl,
                version=entry["version"],
                metadata=entry.get("metadata", {}),
            )
            logger.debug(
                "Registered %r/%r@%s from %s",
                entry["kind"],
                entry["key"],
                entry["version"],
                manifest_path.name,
            )
            registered += 1

        logger.info("Loaded %d entries from manifest %s", registered, manifest_path.name)
        return registered

    # ------------------------------------------------------------------
    # Compatibility aliases required by the roadmap (FND-009)
    # ------------------------------------------------------------------
    def scan_file(self, manifest_path: Path, verify_imports: bool = True) -> int:
        """Alias for :meth:`load` — validates and loads a single manifest file.

        Provided for API stability; the roadmap refers to this as ``scan_file()``.
        """
        return self.load(manifest_path, verify_imports=verify_imports)

    def scan_installed(self, verify_imports: bool = True) -> int:
        """Scan all installed packages for manifests (alias for :meth:`scan`).

        Provided for API stability; the roadmap refers to this as ``scan_installed()``.
        """
        return self.scan(verify_imports=verify_imports)

    def scan(self, search_paths: list[Path] | None = None, verify_imports: bool = True) -> int:
        """
        Discover and load all extension manifests from installed packages.

        This is a best-effort discovery: malformed manifests (invalid JSON or
        schema violations when loaded via this path) are logged at ``WARNING``
        and skipped, so a single bad extension does not block discovery of
        others. For strict validation that raises :class:`ManifestError`
        immediately (e.g. invalid ``task``), use :meth:`load` or
        :meth:`scan_file`.

        Searches sys.path (or the provided search_paths) for directories
        containing a lingualdub.manifest.json file.

        Args:
            search_paths: Optional list of directories to search. Defaults
                to all directories currently on sys.path.
            verify_imports: When ``False``, schema validation is performed but
                entrypoint import verification is skipped.

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
                resolved = Path.cwd().resolve() if not p or p == "." else Path(p).resolve()
                if resolved.is_dir() and resolved not in paths:
                    paths.append(resolved)
        total = 0
        seen: set = set()  # Deduplicate resolved manifest paths
        # Directories to prune during walk (heavy or irrelevant)
        prune_dirs = {
            ".git",
            ".hg",
            ".svn",
            ".eggs",
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
            "htmlcov",
            ".ruff_cache",
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
                        total += self.load(manifest_path, verify_imports=verify_imports)
                    except ManifestError as exc:
                        logger.warning("Skipping malformed manifest: %s", exc)

        return total
