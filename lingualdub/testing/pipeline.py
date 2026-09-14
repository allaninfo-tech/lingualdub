# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Pipeline test harness — REL-005.

    from lingualdub.testing.pipeline import PipelineTestHarness
    from lingualdub.testing.fakes import FakeASR, FakeTranslation, FakeTTS
    from lingualdub.testing.builders import ResourceBuilder

    harness = PipelineTestHarness()
    harness.with_components(FakeASR(), FakeTranslation(), FakeTTS())
    result = harness.run(ResourceBuilder().build())
    assert result.status == ResultStatus.COMPLETE

The harness wires a private :class:`Registry` and :class:`ConfigLoader` /
:class:`PipelineExecutor` so tests don't share global state.
"""

from __future__ import annotations

from typing import Any

from lingualdub.core.pipeline import Pipeline
from lingualdub.core.protocols import ComponentProtocol
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result, ResultStatus
from lingualdub.pipeline.config_loader import ConfigLoader
from lingualdub.pipeline.executor import PipelineExecutor
from lingualdub.registry.registry import Registry

__all__ = ["PipelineTestHarness"]


class PipelineTestHarness:
    """Helper to run pipelines end-to-end in under 20 lines (REL-005).

    Example:

        harness = PipelineTestHarness(source_language="lug", target_language="eng")
        harness.with_components(FakeASR(), FakeTranslation(), FakeTTS())
        result = harness.run(ResourceBuilder().build())
        assert_result_complete(result)

    Or from declarative config:

        harness = PipelineTestHarness()
        result = harness.run_with_config({
            \"source_language\": \"lug\",
            \"target_language\": \"eng\",
            \"stages\": [\"fake_asr\", \"fake_translator\", \"fake_tts\"]
        }, input_resource)

    Attributes:
        registry: Private registry pre-populated via ``with_components``.
        source_language: Default source language for pipelines built via ``run``.
        target_language: Default target language.
    """

    def __init__(
        self,
        source_language: str = "lug",
        target_language: str | None = "eng",
        registry: Registry | None = None,
    ) -> None:
        self.source_language: str = source_language
        self.target_language: str | None = target_language
        self.registry: Registry = registry or Registry()
        self._components: list[ComponentProtocol] = []

    def with_components(self, *components: ComponentProtocol) -> PipelineTestHarness:
        """Register components (instances) directly, bypassing name/version resolution.

        Each component is stored for direct pipeline assembly (no registry lookup needed
        when using :meth:`run`).

        Returns:
            ``self`` for chaining.
        """
        for comp in components:
            self._components.append(comp)
            # Also register in private registry for config-based tests
            try:
                self.registry.register(
                    "component",
                    comp.name,
                    comp.__class__,
                    version=getattr(comp, "version", "0.0.1"),
                )
                # Also try instance registration fallback — store instance under same key if class fails protocol check
                # We store the instance so ConfigLoader can instantiate? ConfigLoader expects class.
                # For direct run we keep _components; for config we need class mapping.
                # So we register the instance directly as well via private dict.
                # To make ConfigLoader work with fakes, we monkey-patch resolve for these names.
                pass
            except Exception:
                # Already registered or conflict — ignore for harness convenience
                pass
        return self

    def with_registry_components(self, registry: Registry) -> PipelineTestHarness:
        """Use an existing registry (e.g. CLI default) instead of private one."""
        self.registry = registry
        return self

    def build_pipeline(
        self,
        stages: list[ComponentProtocol] | None = None,
        source_language: str | None = None,
        target_language: str | None = None,
        per_segment_language: bool = False,
        on_stage_failure: str | None = None,
        name: str | None = None,
    ) -> Pipeline:
        """Build a :class:`Pipeline` from the harness components or supplied stages.

        Args:
            stages: Explicit stages; defaults to ``self._components``.
            source_language: Override harness default.
            target_language: Override harness default.
            per_segment_language: Per-segment routing flag.
            on_stage_failure: Failure mode string (e.g. ``\"skip\"``) or None for default ABORT.
            name: Optional pipeline name.

        Returns:
            Assembled, compatibility-checked pipeline.
        """
        from lingualdub.core.component import FailureMode

        use_stages = stages if stages is not None else list(self._components)
        if not use_stages:
            raise ValueError(  # justified: test harness — no components configured
                "PipelineTestHarness has no components; call with_components(...) first or pass stages explicitly."
            )
        src = source_language if source_language is not None else self.source_language
        tgt = target_language if target_language is not None else self.target_language
        fm = FailureMode.ABORT
        if on_stage_failure is not None:
            fm = FailureMode(on_stage_failure.lower())
        return Pipeline(
            stages=use_stages,  # type: ignore[arg-type]
            source_language=src,  # type: ignore[arg-type]
            target_language=tgt,  # type: ignore[arg-type]
            per_segment_language=per_segment_language,
            on_stage_failure=fm,
            name=name or "test_harness_pipeline",
        )

    def run(
        self,
        input: Resource | Result,
        stages: list[ComponentProtocol] | None = None,
        **pipeline_kwargs: Any,
    ) -> Result:
        """Build and run a pipeline against ``input``.

        Args:
            input: Input resource or result.
            stages: Explicit stages; defaults to harness components.
            **pipeline_kwargs: Passed to :meth:`build_pipeline` (e.g. ``per_segment_language=True``).

        Returns:
            Pipeline :class:`Result`.
        """
        pipeline = self.build_pipeline(stages=stages, **pipeline_kwargs)
        executor = PipelineExecutor(pipeline)
        return executor.run(input)

    def run_with_config(self, config: dict[str, Any], input: Resource | Result) -> Result:
        """Load a pipeline from a declarative config dict and run it.

        Uses the harness's private registry (populated via ``with_components``
        or manually). This is the path that exercises ``ConfigLoader`` + ``Manifest``.

        Args:
            config: Config dict as accepted by :class:`ConfigLoader`.
            input: Input resource/result.

        Returns:
            Pipeline result.
        """
        # Ensure fakes registered under their names resolve to classes that can be instantiated.
        # ConfigLoader will call impl(**params); if we registered classes, that's fine.
        # If harness used instance-based with_components, we need to ensure those names are resolvable.
        # We temporarily inject instance resolvers for names that are not yet in registry.
        for comp in self._components:
            key = getattr(comp, "name", None)
            if key and key not in [k for k, _ in self.registry.list("component")]:
                import contextlib

                with contextlib.suppress(Exception):
                    self.registry.register(
                        "component", key, comp, version=getattr(comp, "version", "0.0.1")
                    )
        loader = ConfigLoader(self.registry)
        pipeline = loader.load_dict(config)
        executor = PipelineExecutor(pipeline)
        return executor.run(input)

    def assert_complete(self, result: Result) -> Result:
        """Assert result is COMPLETE and return it for chaining."""
        if result.status != ResultStatus.COMPLETE:
            raise AssertionError(
                f"Expected COMPLETE, got {result.status.value!r} warnings={result.warnings!r}"
            )
        return result

    def __repr__(self) -> str:
        return f"PipelineTestHarness(source={self.source_language!r}, target={self.target_language!r}, stages={[getattr(c, 'name', str(c)) for c in self._components]})"
