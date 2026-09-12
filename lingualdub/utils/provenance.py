# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Provenance helpers.

Utilities for constructing and validating the provenance dictionaries
attached to Resource, Result, and Registry entries. Provenance is the
mechanism that makes evaluation runs comparable and reproducible.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def make_run_id() -> str:
    """Generate a unique run identifier."""
    return str(uuid.uuid4())


_RESERVED_KEYS = {"run_id", "timestamp", "pipeline", "component_versions", "dataset_version"}


def make_provenance(
    pipeline_name: str | None = None,
    component_versions: dict[str, str] | None = None,
    dataset_version: str | None = None,
    run_id: str | None = None,
    **extra: Any,
) -> dict:
    """
    Construct a provenance dictionary for a Result or Resource.

    Args:
        pipeline_name: Name of the pipeline that produced this result.
        component_versions: Mapping of component name to version string.
        dataset_version: Version of the input dataset used.
        run_id: Unique identifier for this run. Generated if not provided.
        **extra: Additional key-value pairs to include in provenance.

    Returns:
        A provenance dictionary suitable for Result.provenance or Resource.provenance.

    Raises:
        ValueError: If extra shadows a reserved key.
    """
    clashes = _RESERVED_KEYS.intersection(extra.keys())
    if clashes:
        raise ValueError(
            f"extra keys {sorted(clashes)} shadow reserved provenance keys {_RESERVED_KEYS}"
        )
    return {
        "run_id": run_id or make_run_id(),
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "pipeline": pipeline_name,
        "component_versions": dict(component_versions) if component_versions else {},
        "dataset_version": dataset_version,
        **extra,
    }
