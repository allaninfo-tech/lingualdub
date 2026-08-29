"""
Provenance helpers.

Utilities for constructing and validating the provenance dictionaries
attached to Resource, Result, and Registry entries. Provenance is the
mechanism that makes evaluation runs comparable and reproducible.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def make_run_id() -> str:
    """Generate a unique run identifier."""
    return str(uuid.uuid4())


def make_provenance(
    pipeline_name: Optional[str] = None,
    component_versions: Optional[Dict[str, str]] = None,
    dataset_version: Optional[str] = None,
    run_id: Optional[str] = None,
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
    """
    return {
        "run_id": run_id or make_run_id(),
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "pipeline": pipeline_name,
        "component_versions": component_versions or {},
        "dataset_version": dataset_version,
        **extra,
    }
