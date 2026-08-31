"""
PipelineExecutor — runs a Pipeline stage by stage.

The executor walks a Pipeline's stages in order, passes the running Result
between them, and applies the configured failure mode when a stage raises
an exception. It handles abort, skip, and degrade failure paths.

Execution strategy is intentionally kept simple (linear, ordered) for the
initial implementation. Non-linear DAG execution is a planned extension.
"""

from __future__ import annotations
import logging
from typing import Union

from lingualdub.core.component import FailureMode
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result, ResultStatus

logger = logging.getLogger(__name__)


class PipelineExecutionError(Exception):
    """Raised when a pipeline stage fails under ABORT mode."""


class PipelineExecutor:
    """
    Executes a Pipeline against an input resource or result.

    Attributes:
        pipeline: The Pipeline to execute.
    """

    def __init__(self, pipeline: Pipeline) -> None:
        self.pipeline = pipeline

    def run(self, input: Union[Resource, Result]) -> Result:
        """
        Execute all pipeline stages in order.

        Provenance strategy (Option A — merge):
        The executor initialises a base provenance dict before the stage loop.
        After each stage returns a Result, the executor's base provenance keys
        are merged into that Result's provenance (stage-set keys take precedence
        for conflicts). This ensures that executor-level provenance — pipeline
        name, run metadata — is never silently discarded when a stage returns
        its own Result object.

        Args:
            input: A Resource or a Result from a previous pipeline to process.

        Returns:
            The final Result after all stages have run (or failed gracefully).

        Raises:
            PipelineExecutionError: If a stage fails under ABORT mode.
        """
        current: Union[Resource, Result] = input
        base_provenance = {"pipeline": repr(self.pipeline)}
        result = Result(
            source_language=self.pipeline.source_language,
            target_language=self.pipeline.target_language,
            provenance=dict(base_provenance),
        )

        for stage in self.pipeline.stages:
            failure_mode = stage.on_failure or self.pipeline.on_stage_failure
            logger.info("Running stage: %s", stage.name)

            try:
                current = stage.run(current)
                if isinstance(current, Result):
                    # Merge base provenance into stage result; stage keys win on conflict.
                    merged = dict(base_provenance)
                    merged.update(current.provenance)
                    current.provenance = merged
                    result = current
            except Exception as exc:
                logger.warning("Stage %r failed: %s", stage.name, exc)

                if failure_mode == FailureMode.ABORT:
                    result.mark_failed(f"Stage {stage.name!r} aborted: {exc}")
                    raise PipelineExecutionError(
                        f"Pipeline aborted at stage {stage.name!r}: {exc}"
                    ) from exc

                elif failure_mode == FailureMode.SKIP:
                    result.mark_partial(f"Stage {stage.name!r} skipped: {exc}")
                    logger.info("Stage %r skipped.", stage.name)

                elif failure_mode == FailureMode.DEGRADE:
                    try:
                        current = stage.degrade(current)
                        if isinstance(current, Result):
                            merged = dict(base_provenance)
                            merged.update(current.provenance)
                            current.provenance = merged
                            result = current
                        result.mark_degraded(f"Stage {stage.name!r} ran degraded: {exc}")
                    except NotImplementedError:
                        result.mark_partial(
                            f"Stage {stage.name!r} has no degrade() path; skipped: {exc}"
                        )
                    except Exception as degrade_exc:
                        result.mark_failed(
                            f"Stage {stage.name!r} degrade() also failed: {degrade_exc}"
                        )
                        raise PipelineExecutionError(
                            f"Pipeline failed at stage {stage.name!r} degrade(): {degrade_exc}"
                        ) from degrade_exc

        return result
