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
from typing import List, Optional, Tuple, Union

from lingualdub.core.component import Component, FailureMode
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result, ResultStatus
from lingualdub.core.segment import Segment
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
        # Propagate input provenance (e.g. consent_basis) into base provenance
        # so voice consent is not lost after the first stage. Stage-specific keys
        # win on conflict, but consent and dataset keys are preserved. We must
        # not let make_provenance's None placeholders (e.g. dataset_version=None)
        # shadow real values from the input resource.
        if isinstance(input, (Resource, Result)):
            for k, v in getattr(input, "provenance", {}).items():
                if v is None:
                    continue
                if k not in base_provenance or base_provenance[k] is None:
                    base_provenance[k] = v
                # existing non-None base values (run_id, pipeline, timestamp) keep precedence

        result = Result(
            source_language=self.pipeline.source_language,
            target_language=self.pipeline.target_language,
            provenance=dict(base_provenance),
        )

        for stage in self.pipeline.stages:
            # Resolve failure mode: stage-level (Component.on_failure) wins if
            # explicitly set (not None); otherwise fall back to pipeline default.
            stage_fm = getattr(stage, "on_failure", None)
            failure_mode = stage_fm if stage_fm is not None else self.pipeline.on_stage_failure
            logger.info("Running stage: %s (failure_mode=%s)", stage.name, failure_mode.value)

            try:
                if (
                    self.pipeline.per_segment_language
                    and isinstance(current, Result)
                    and current.segments
                ):
                    current = self._run_per_segment_stage(stage, current, failure_mode)
                else:
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

    def _run_per_segment_stage(
        self,
        stage: Component,
        current: Result,
        failure_mode: FailureMode,
    ) -> Result:
        """
        Execute a stage specifically for segments matching its supported languages.

        When per_segment_language is enabled, this selectively routes each segment
        to the stage if the segment's language is supported by that stage.
        Unsupported segments are skipped, degraded, or cause an abort based on failure_mode.
        """
        stage_langs = getattr(stage, "supported_languages", [])
        if not stage_langs or "*" in stage_langs:
            return stage.run(current)

        supported: List[Tuple[int, Segment]] = []
        unsupported: List[Tuple[int, Segment]] = []

        for idx, seg in enumerate(current.segments):
            seg_lang = seg.language or current.source_language or self.pipeline.source_language
            if seg_lang in stage_langs:
                supported.append((idx, seg))
            else:
                unsupported.append((idx, seg))

        if not unsupported:
            return stage.run(current)

        unsupported_langs = sorted(list(set(
            (s.language or current.source_language or self.pipeline.source_language)
            for _, s in unsupported
        )))

        if failure_mode == FailureMode.ABORT:
            raise PipelineExecutionError(
                f"Stage {stage.name!r} does not support segment language(s): {unsupported_langs}"
            )

        # Mark unsupported segments as skipped
        for _, seg in unsupported:
            seg.metadata["skipped_by"] = stage.name

        if not supported:
            logger.info(
                "Stage %r skipped all segments (supported=%s, segment_languages=%s)",
                stage.name,
                stage_langs,
                unsupported_langs,
            )
            current.mark_partial(
                f"Stage {stage.name!r} skipped all segments with unsupported language(s): {unsupported_langs}"
            )
            return current

        # Create sub-result with only supported segments
        sub_result = Result(
            segments=[s for _, s in supported],
            source_language=current.source_language,
            target_language=current.target_language,
            warnings=list(current.warnings),
            provenance=dict(current.provenance),
            artifacts=list(current.artifacts),
            metadata=dict(current.metadata),
        )

        stage_out = stage.run(sub_result)
        if not isinstance(stage_out, Result):
            return current

        # Recombine processed segments and skipped segments
        combined_segments: List[Segment] = []
        if len(stage_out.segments) == len(supported):
            new_segments_map = {orig_idx: stage_out.segments[i] for i, (orig_idx, _) in enumerate(supported)}
            unsupported_map = {orig_idx: seg for orig_idx, seg in unsupported}
            for i in range(len(current.segments)):
                if i in new_segments_map:
                    combined_segments.append(new_segments_map[i])
                elif i in unsupported_map:
                    combined_segments.append(unsupported_map[i])
        else:
            combined_segments = sorted(
                list(stage_out.segments) + [s for _, s in unsupported],
                key=lambda s: (s.start, s.end),
            )

        stage_out.segments = combined_segments
        if failure_mode == FailureMode.DEGRADE:
            stage_out.mark_degraded(
                f"Stage {stage.name!r} routed {len(supported)} segments; {len(unsupported)} unsupported segments degraded."
            )
        else:
            stage_out.mark_partial(
                f"Stage {stage.name!r} routed {len(supported)} segments; skipped {len(unsupported)} segments."
            )
        return stage_out

