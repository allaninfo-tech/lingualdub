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
from lingualdub.utils.provenance import make_provenance

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

        Provenance strategy (merge):
        The executor initialises a base provenance dict before the stage loop
        using make_provenance(), which generates a run_id and timestamp. After
        each stage returns a Result, the executor's base provenance keys are
        merged into that Result's provenance (stage-set keys take precedence
        for conflicts). This ensures executor-level provenance — pipeline name,
        run_id, timestamp — is never silently discarded when a stage returns
        its own Result object.

        Failure mode resolution:
        Each stage's own on_failure takes precedence over the pipeline-level
        on_stage_failure. If the stage has not explicitly overridden it from
        the pipeline default, the pipeline-level value is used.

        Args:
            input: A Resource or a Result from a previous pipeline to process.

        Returns:
            The final Result after all stages have run (or failed gracefully).

        Raises:
            PipelineExecutionError: If a stage fails under ABORT mode.
        """
        current: Union[Resource, Result] = input
        base_provenance = make_provenance(
            pipeline_name=self.pipeline.name or repr(self.pipeline),
            component_versions={s.name: s.version for s in self.pipeline.stages},
        )
        base_provenance["pipeline_repr"] = repr(self.pipeline)

        result = Result(
            source_language=self.pipeline.source_language,
            target_language=self.pipeline.target_language,
            provenance=dict(base_provenance),
        )

        for stage in self.pipeline.stages:
            # Resolve failure mode: stage-level overrides pipeline-level only
            # if they differ from the pipeline default (i.e. stage has its own).
            # Since FailureMode is always set (never None), we compare against
            # the pipeline default to detect explicit stage-level overrides.
            stage_fm = getattr(stage, "on_failure", None)
            failure_mode = stage_fm if stage_fm is not None else self.pipeline.on_stage_failure
            logger.info("Running stage: %s (failure_mode=%s)", stage.name, failure_mode.value)

            try:
                current = stage.run(current)
                if isinstance(current, Result):
                    # Merge base provenance into stage result; stage keys win on conflict.
                    merged = dict(base_provenance)
                    merged.update(current.provenance)
                    current.provenance = merged
                    # Preserve pipeline-level language fields if stage didn't set them.
                    if not current.source_language:
                        current.source_language = self.pipeline.source_language
                    if not current.target_language and self.pipeline.target_language:
                        current.target_language = self.pipeline.target_language
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
                            if not current.source_language:
                                current.source_language = self.pipeline.source_language
                            if not current.target_language and self.pipeline.target_language:
                                current.target_language = self.pipeline.target_language
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
