"""
Pipeline abstraction.

A Pipeline composes an ordered sequence of Components into a reproducible
workflow. It manages inter-stage compatibility checking, per-segment language
routing for code-switch-aware execution, and stage failure handling.

Pipeline does not execute stages directly — that is delegated to the executor
in lingualdub.pipeline. This module defines the pipeline's structure and contract.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from lingualdub.core.component import Component, FailureMode


@dataclass
class Pipeline:
    """
    A composition of components forming a speech-processing workflow.

    Attributes:
        stages: Ordered list of Component instances forming the pipeline.
        source_language: Source language code for this pipeline.
        target_language: Target language code, if translation is involved.
        per_segment_language: When True, each Segment's language field is used
            to route that segment to the appropriate component independently,
            enabling code-switch-aware processing within a single run.
        on_stage_failure: Default failure mode applied to any stage that does
            not override it. Stages may declare their own on_failure value.
        name: Optional human-readable name for this pipeline.
        description: Optional description of this pipeline's purpose.
    """

    stages: List[Component]
    source_language: str
    target_language: Optional[str] = None
    per_segment_language: bool = False
    on_stage_failure: FailureMode = FailureMode.ABORT
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.stages:
            raise ValueError("Pipeline must have at least one stage.")
        if not self.source_language:
            raise ValueError("Pipeline.source_language must not be empty.")
        self._validate_stage_compatibility()

    def _validate_stage_compatibility(self) -> None:
        """
        Walk the stage list and verify that each stage's required capabilities
        are provided by the previous stage. Raises ValueError on mismatch.

        This check runs at pipeline assembly time, not at execution time.
        """
        provided: List[str] = []
        for stage in self.stages:
            missing = stage.check_compatibility(provided)
            if missing:
                raise ValueError(
                    f"Pipeline compatibility error: stage {stage.name!r} "
                    f"requires {missing!r} but upstream provides {provided!r}."
                )
            provided = stage.provides

    @property
    def stage_names(self) -> List[str]:
        """Returns the names of all stages in order."""
        return [s.name for s in self.stages]

    def __repr__(self) -> str:
        return (
            f"Pipeline(source={self.source_language!r}, "
            f"target={self.target_language!r}, "
            f"stages={self.stage_names})"
        )
