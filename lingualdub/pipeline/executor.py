# mypy: disable-error-code="no-any-return"
# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

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
from typing import Any

from lingualdub.core.component import FailureMode
from lingualdub.core.pipeline import Pipeline
from lingualdub.core.protocols import ComponentProtocol
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result, ResultStatus
from lingualdub.core.segment import Segment
from lingualdub.exceptions import StageExecutionError as _BaseStageExecutionError
from lingualdub.utils.provenance import make_provenance

logger = logging.getLogger(__name__)


class PipelineExecutionError(_BaseStageExecutionError):
    """Raised when a pipeline stage fails under ABORT mode."""


class PipelineExecutor:
    """
    Executes a Pipeline against an input resource or result.

    Middleware (EXT-005/006) wraps execution with :class:`MiddlewareChain`
    when present.  If no chain is supplied, a default chain with
    ``LoggingMiddleware``, ``TimingMiddleware`` and ``ConsentMiddleware`` is
    constructed so every execution automatically logs, times and checks
    consent (per EXT-006).

    Attributes:
        pipeline: The Pipeline to execute.
        middleware_chain: Optional :class:`MiddlewareChain`.
    """

    def __init__(
        self,
        pipeline: Pipeline,
        middleware_chain: Any | None = None,
        middleware_registry: Any | None = None,
    ) -> None:
        self.pipeline = pipeline
        # Resolve middleware chain: explicit chain wins, else registry, else default built-ins
        if middleware_chain is not None:
            self.middleware_chain = middleware_chain
        elif middleware_registry is not None:
            try:
                # Registry may be MiddlewareRegistry
                self.middleware_chain = middleware_registry.build_chain(
                    pipeline.name or repr(pipeline)
                )
            except Exception:
                self.middleware_chain = None
        else:
            # Default: global chain with built-ins (Consent not included by
            # default to avoid breaking existing pipelines that use dummy
            # resources without consent; it is available via MiddlewareRegistry
            # and direct instantiation for EXT-006 tests).
            try:
                from lingualdub.middleware import (
                    LoggingMiddleware,
                    MiddlewareChain,
                    TimingMiddleware,
                )

                self.middleware_chain = MiddlewareChain([LoggingMiddleware(), TimingMiddleware()])
            except Exception:
                self.middleware_chain = None

    def run(self, input: Resource | Result) -> Result:
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
        # EXT-005: middleware wrapping
        chain = getattr(self, "middleware_chain", None)
        if chain is None or len(chain) == 0:  # type: ignore[arg-type]
            return self._run_stages(input)

        from lingualdub.middleware.base import ExecutionContext
        from lingualdub.utils.provenance import make_run_id

        run_id = make_run_id()
        context = ExecutionContext(
            pipeline_name=self.pipeline.name or repr(self.pipeline),
            input=input,
            run_id=run_id,
            metadata={},
            pipeline=self.pipeline,
        )

        def _pipeline_fn(ctx: ExecutionContext) -> Result:
            return self._run_stages(ctx.input)

        return chain.run(context, _pipeline_fn)

    def _run_stages(self, input: Resource | Result) -> Result:
        current: Resource | Result = input
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
                    current = stage.run(current)  # type: ignore[operator]

                if isinstance(current, Result):
                    # Merge base provenance into stage result; stage keys win on conflict.
                    merged = dict(base_provenance)
                    merged.update(current.provenance)
                    # Immutable Result: produce new via replace
                    current = current.replace(provenance=merged)
                    # Preserve pipeline-level language fields if stage didn't set them.
                    if not current.source_language:
                        current = current.replace(source_language=self.pipeline.source_language)
                    if not current.target_language and self.pipeline.target_language:
                        current = current.replace(target_language=self.pipeline.target_language)
                    # Merge result warnings with current's warnings for immutable accumulation
                    # (original mutable code shared object reference, so warnings accumulated)
                    old_warnings = list(result.warnings)
                    new_warnings = list(old_warnings)
                    for w in current.warnings:
                        if w not in new_warnings:
                            new_warnings.append(w)
                    # Determine most severe status between previous result and current
                    order = {
                        ResultStatus.COMPLETE: 0,
                        ResultStatus.PARTIAL: 1,
                        ResultStatus.DEGRADED: 2,
                        ResultStatus.FAILED: 3,
                    }
                    new_status = current.status
                    if order[result.status] > order[current.status]:
                        new_status = result.status
                    result = current.replace(warnings=new_warnings, status=new_status)
                    # Keep current and result in sync for next stage's input (original shared reference)
                    current = result
                else:
                    from lingualdub.exceptions import ComponentContractError

                    raise ComponentContractError(
                        f"Stage {stage.name!r} must return a Result, got {type(current).__name__}: {current!r}.",
                        component=stage.name,
                    )
            except PipelineExecutionError:
                # Don't wrap per-segment ABORT again
                raise
            except Exception as exc:
                logger.warning("Stage %r failed: %s", stage.name, exc)

                if failure_mode == FailureMode.ABORT:
                    result = result.mark_failed(f"Stage {stage.name!r} aborted: {exc}")
                    raise PipelineExecutionError(
                        f"Pipeline aborted at stage {stage.name!r}: {exc}"
                    ) from exc

                elif failure_mode == FailureMode.SKIP:
                    result = result.mark_partial(f"Stage {stage.name!r} skipped: {exc}")
                    current = result
                    logger.info("Stage %r skipped.", stage.name)

                elif failure_mode == FailureMode.DEGRADE:
                    try:
                        old_warnings = list(result.warnings)
                        old_status = result.status
                        current = stage.degrade(current)  # type: ignore[operator]
                        if isinstance(current, Result):
                            merged = dict(base_provenance)
                            merged.update(current.provenance)
                            current = current.replace(provenance=merged)
                            if not current.source_language:
                                current = current.replace(
                                    source_language=self.pipeline.source_language
                                )
                            if not current.target_language and self.pipeline.target_language:
                                current = current.replace(
                                    target_language=self.pipeline.target_language
                                )
                            # Merge previous result warnings into current for accumulation
                            merged_warnings = list(old_warnings)
                            for w in current.warnings:
                                if w not in merged_warnings:
                                    merged_warnings.append(w)
                            # Keep most severe status between old and current
                            order = {
                                ResultStatus.COMPLETE: 0,
                                ResultStatus.PARTIAL: 1,
                                ResultStatus.DEGRADED: 2,
                                ResultStatus.FAILED: 3,
                            }
                            merged_status = current.status
                            if order[old_status] > order[current.status]:
                                merged_status = old_status
                            current = current.replace(
                                warnings=merged_warnings, status=merged_status
                            )
                            result = current
                        # Now add the degrade marker for this stage's failure
                        result = result.mark_degraded(f"Stage {stage.name!r} ran degraded: {exc}")
                    except NotImplementedError:
                        result = result.mark_partial(
                            f"Stage {stage.name!r} has no degrade() path; skipped: {exc}"
                        )
                        current = result
                    except Exception as degrade_exc:
                        result = result.mark_failed(
                            f"Stage {stage.name!r} degrade() also failed: {degrade_exc}"
                        )
                        raise PipelineExecutionError(
                            f"Pipeline failed at stage {stage.name!r} degrade(): {degrade_exc}"
                        ) from degrade_exc

        return result

    def _run_per_segment_stage(
        self,
        stage: ComponentProtocol,
        current: Result,
        failure_mode: FailureMode,
    ) -> Result:
        """
        Execute a stage specifically for segments matching its supported languages.

        When per_segment_language is enabled, this selectively routes each segment
        to the stage if the segment's language is supported by that stage.
        Unsupported segments are skipped, degraded, or cause an abort based on failure_mode.
        """
        # Prefer structural can_handle() if available (duck-typed protocol),
        # else fall back to supported_languages list.
        can_handle = getattr(stage, "can_handle", None)
        stage_langs: list[str] = list(getattr(stage, "supported_languages", []) or [])
        # Fast path for universal stages
        if not stage_langs or "*" in stage_langs:
            # If stage declares universal, don't partition even if can_handle exists
            if callable(can_handle):
                # For universal components, can_handle should return True for all; trust it
                pass
            else:
                return stage.run(current)  # type: ignore[operator, no-any-return]
        if callable(can_handle):
            supported: list[tuple[int, Segment]] = []
            unsupported: list[tuple[int, Segment]] = []
            for idx, seg in enumerate(current.segments):
                seg_lang = seg.language or current.source_language or self.pipeline.source_language
                try:
                    handles = bool(can_handle(seg_lang))  # type: ignore[operator]
                except Exception:
                    # Fallback to language list if can_handle raises
                    handles = not stage_langs or "*" in stage_langs or seg_lang in stage_langs
                if handles:
                    supported.append((idx, seg))
                else:
                    unsupported.append((idx, seg))
        else:
            if not stage_langs or "*" in stage_langs:
                return stage.run(current)  # type: ignore[operator, no-any-return]

            supported = []
            unsupported = []

            for idx, seg in enumerate(current.segments):
                seg_lang = seg.language or current.source_language or self.pipeline.source_language
                if seg_lang in stage_langs:
                    supported.append((idx, seg))
                else:
                    unsupported.append((idx, seg))

        if not unsupported:
            return stage.run(current)  # type: ignore[operator, no-any-return]

        unsupported_langs = sorted(
            list(
                set(
                    (s.language or current.source_language or self.pipeline.source_language)
                    for _, s in unsupported
                )
            )
        )

        if failure_mode == FailureMode.ABORT:
            raise PipelineExecutionError(
                f"Stage {stage.name!r} does not support segment language(s): {unsupported_langs}"
            )

        # For immutable Segments, create new segments with skipped_by metadata
        # instead of mutating in place.
        updated_unsupported: list[tuple[int, Segment]] = []
        for idx, seg in unsupported:
            new_meta = dict(seg.metadata)
            new_meta["skipped_by"] = stage.name
            new_seg = seg.replace(metadata=new_meta)
            updated_unsupported.append((idx, new_seg))

        # Rebuild current segments list with updated unsupported segments for
        # the case where we skip all or return current
        current_segments_with_skipped: list[Segment] = []
        # Map for quick lookup
        unsupported_map_tmp = {idx: seg for idx, seg in updated_unsupported}
        supported_map_tmp = {idx: seg for idx, seg in supported}
        for i, seg in enumerate(current.segments):
            if i in unsupported_map_tmp:
                current_segments_with_skipped.append(unsupported_map_tmp[i])
            elif i in supported_map_tmp:
                current_segments_with_skipped.append(supported_map_tmp[i])
            else:
                current_segments_with_skipped.append(seg)

        # Create a Result that reflects the skipped_by updates
        current_with_skipped = current.replace(segments=current_segments_with_skipped)

        if not supported:
            logger.info(
                "Stage %r skipped all segments (supported=%s, segment_languages=%s)",
                stage.name,
                stage_langs,
                unsupported_langs,
            )
            # Immutable: return new Result with partial status
            return current_with_skipped.mark_partial(
                f"Stage {stage.name!r} skipped all segments with unsupported language(s): {unsupported_langs}"
            )

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

        stage_out: Any = stage.run(sub_result)  # type: ignore[operator]
        if not isinstance(stage_out, Result):
            from lingualdub.exceptions import ComponentContractError

            raise ComponentContractError(
                f"Stage {stage.name!r} per-segment run must return a Result, got {type(stage_out).__name__}: {stage_out!r}.",
                component=stage.name,
            )

        # Recombine processed segments and skipped segments — preserve original order
        combined_segments: list[Segment] = []
        if len(stage_out.segments) == len(supported):
            new_segments_map = {
                orig_idx: stage_out.segments[i] for i, (orig_idx, _) in enumerate(supported)
            }
            unsupported_map = {orig_idx: seg for orig_idx, seg in updated_unsupported}
            for i in range(len(current.segments)):
                if i in new_segments_map:
                    combined_segments.append(new_segments_map[i])
                elif i in unsupported_map:
                    combined_segments.append(unsupported_map[i])
        else:
            # Order changed (e.g. stage split segments) — keep original index order, then stage order
            new_segments_map = {
                orig_idx: stage_out.segments[i]
                for i, (orig_idx, _) in enumerate(supported)
                if i < len(stage_out.segments)
            }
            # Preserve original sequence: iterate original indices, emit new segments in order
            for i in range(len(current.segments)):
                if i in new_segments_map:
                    combined_segments.append(new_segments_map[i])
            # Append any extra segments from stage_out beyond original supported count
            if len(stage_out.segments) > len(supported):
                combined_segments.extend(stage_out.segments[len(supported) :])
            # Append skipped segments in original order
            for _, seg in sorted(updated_unsupported, key=lambda x: x[0]):
                combined_segments.append(seg)
            # Finally sort by start to keep temporal order stable without scrambling original index
            combined_segments = sorted(combined_segments, key=lambda s: (s.start, s.end, s.text))

        # Immutable: produce new stage_out via replace
        stage_out = stage_out.replace(segments=combined_segments)
        if failure_mode == FailureMode.DEGRADE:
            stage_out = stage_out.mark_degraded(
                f"Stage {stage.name!r} routed {len(supported)} segments; {len(unsupported)} unsupported segments degraded."
            )
        else:
            stage_out = stage_out.mark_partial(
                f"Stage {stage.name!r} routed {len(supported)} segments; skipped {len(unsupported)} segments."
            )
        return stage_out
