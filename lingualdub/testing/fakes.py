# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Fake component implementations for testing — REL-005.

Each fake satisfies the corresponding ``ComponentProtocol`` and produces
deterministic, fast outputs without ML dependencies.

    from lingualdub.testing.fakes import FakeASR, FakeTTS
    from lingualdub.testing.builders import ResultBuilder

    asr = FakeASR()
    result = asr.run(audio_resource)
    assert_result_complete(result)
"""

from __future__ import annotations

from lingualdub.core.component import Component, ComponentTask, FailureMode
from lingualdub.core.resource import Resource
from lingualdub.core.result import Result, ResultStatus
from lingualdub.core.segment import Segment
from lingualdub.utils.provenance import make_provenance

__all__ = ["FakeASR", "FakeTTS", "FakeTranslation", "FakeAlignment", "FakeEvaluator"]


class FakeASR(Component):
    """Fake ASR — deterministic transcription without model.

    Requires ``[]`` (accepts ``Resource`` or ``Result``), provides
    ``["transcription", "word_timestamps"]``.
    """

    name: str = "fake_asr"
    version: str = "0.0.1"
    task: ComponentTask = ComponentTask.ASR
    supported_languages: list[str] = ["lug", "nyn", "eng"]
    requires: list[str] = []
    provides: list[str] = ["transcription", "word_timestamps"]
    on_failure: FailureMode | None = FailureMode.ABORT

    def __init__(self, text: str = "fake transcription", language: str = "lug") -> None:
        super().__init__()
        self._text = text
        self._language = language

    def run(self, input: Result | Resource) -> Result:
        # Accept either Resource or Result; produce deterministic segment
        seg = Segment(start=0.0, end=2.0, text=self._text, language=self._language, confidence=0.99)
        source_lang = (
            getattr(input, "language", None)
            or getattr(input, "source_language", None)
            or self._language
        )
        # If input was Resource, use its language; if Result, use source_language
        if isinstance(input, Resource):
            source_lang = input.language
        elif isinstance(input, Result) and input.source_language:
            source_lang = input.source_language
        return Result(
            segments=[seg],
            source_language=source_lang,  # type: ignore[arg-type]
            provenance=make_provenance(
                pipeline_name="fake_asr", component_versions={self.name: self.version}
            ),
            metadata={"model": "fake_asr"},
        )

    def degrade(self, input: Result | Resource) -> Result:
        seg = Segment(start=0.0, end=1.0, text=self._text, language=self._language, confidence=0.5)
        return Result(
            segments=[seg],
            source_language=self._language,
            status=ResultStatus.DEGRADED,
            warnings=["Degraded: FakeASR degraded path"],
            provenance=make_provenance(
                pipeline_name="fake_asr_degraded", component_versions={self.name: self.version}
            ),
        )


class FakeTranslation(Component):
    """Fake translation — deterministic upper-casing / suffix.

    Requires ``["transcription"]``, provides ``["translation"]``.
    """

    name: str = "fake_translator"
    version: str = "0.0.1"
    task: ComponentTask = ComponentTask.TRANSLATION
    supported_languages: list[str] = ["lug", "nyn", "eng"]
    requires: list[str] = ["transcription"]
    provides: list[str] = ["translation"]
    on_failure: FailureMode | None = FailureMode.ABORT

    def run(self, input: Result | Resource) -> Result:
        if isinstance(input, Resource):
            raise ValueError("FakeTranslation expects Result input with transcription segments")
        # Simple "translation": append " (translated)" and flip language to eng
        segments: list[Segment] = []
        for seg in input.segments:
            new_text = f"{seg.text} (translated)"
            segments.append(
                seg.replace(text=new_text, language="eng", source_language=seg.language)
            )
        return Result(
            segments=segments,
            source_language=input.source_language,
            target_language="eng",
            provenance=make_provenance(
                pipeline_name="fake_translator", component_versions={self.name: self.version}
            ),
            metadata={"model": "fake_translator"},
        )


class FakeTTS(Component):
    """Fake TTS — synthesizes dummy audio artifacts.

    Requires ``["translation"]``, provides ``["audio"]``.
    """

    name: str = "fake_tts"
    version: str = "0.0.1"
    task: ComponentTask = ComponentTask.TTS
    supported_languages: list[str] = ["eng", "lug"]
    requires: list[str] = ["translation"]
    provides: list[str] = ["audio"]
    on_failure: FailureMode | None = FailureMode.DEGRADE

    def run(self, input: Result | Resource) -> Result:
        if isinstance(input, Resource):
            raise ValueError("FakeTTS expects Result with translation segments")
        # Produce dummy artifacts
        artifacts = [f"/tmp/fake_tts_{i}.wav" for i, _ in enumerate(input.segments)]
        return Result(
            segments=list(input.segments),
            source_language=input.source_language,
            target_language=input.target_language or "eng",
            provenance=make_provenance(
                pipeline_name="fake_tts", component_versions={self.name: self.version}
            ),
            artifacts=artifacts,
            metadata={"model": "fake_tts", "synthesized": True},
        )

    def degrade(self, input: Result | Resource) -> Result:
        if isinstance(input, Resource):
            return Result(
                segments=[],
                source_language="eng",
                status=ResultStatus.DEGRADED,
                warnings=["Degraded: FakeTTS no input segments"],
                artifacts=[],
            )
        return Result(
            segments=list(input.segments),
            source_language=input.source_language,
            target_language=input.target_language,
            status=ResultStatus.DEGRADED,
            warnings=["Degraded: FakeTTS degraded path"],
            artifacts=[],
        )


class FakeAlignment(Component):
    """Fake forced alignment — assigns word-level timestamps deterministically.

    Requires ``["transcription"]``, provides ``["aligned_timestamps"]``.
    """

    name: str = "fake_aligner"
    version: str = "0.0.1"
    task: ComponentTask = ComponentTask.ALIGNMENT
    supported_languages: list[str] = ["lug", "nyn", "eng"]
    requires: list[str] = ["transcription"]
    provides: list[str] = ["aligned_timestamps"]
    on_failure: FailureMode | None = FailureMode.ABORT

    def run(self, input: Result | Resource) -> Result:
        if isinstance(input, Resource):
            raise ValueError("FakeAlignment expects Result")
        segments: list[Segment] = []
        for seg in input.segments:
            # Add word_timestamps to metadata deterministically
            words = seg.text.split()
            n = len(words) or 1
            dur = seg.duration / n
            word_ts = []
            for i, w in enumerate(words):
                s = seg.start + i * dur
                e = s + dur
                word_ts.append({"word": w, "start": s, "end": e})
            new_seg = seg.replace(metadata={**seg.metadata, "word_timestamps": word_ts})
            segments.append(new_seg)
        return Result(
            segments=segments,
            source_language=input.source_language,
            target_language=input.target_language,
            provenance=make_provenance(
                pipeline_name="fake_aligner", component_versions={self.name: self.version}
            ),
        )


class FakeEvaluator(Component):
    """Fake evaluator — computes dummy metrics without ground truth.

    Requires ``["audio"]`` or ``["translation"]``, provides ``["metrics"]``.
    This satisfies ``EvaluatorProtocol`` for DI tests.
    """

    name: str = "fake_evaluator"
    version: str = "0.0.1"
    task: ComponentTask = ComponentTask.EVAL
    supported_languages: list[str] = []
    requires: list[str] = []
    provides: list[str] = ["metrics"]
    on_failure: FailureMode | None = FailureMode.ABORT

    def run(self, input: Result | Resource) -> Result:
        if isinstance(input, Resource):
            # Eval against resource: return dummy metrics
            return Result(
                segments=[],
                source_language="lug",
                provenance=make_provenance(
                    pipeline_name="fake_evaluator", component_versions={self.name: self.version}
                ),
                metadata={"metrics": {"wer": 0.12, "cer": 0.05, "bleu": 42.0}},
            )
        # Eval against result
        metrics = {"wer": 0.10, "cer": 0.04, "bleu": 45.0, "chrf": 60.0}
        # Put in metadata.metrics
        return input.replace(metadata={**input.metadata, "metrics": metrics})

    # EvaluatorProtocol extension
    def evaluate_pair(self, hypothesis: Result, reference: Resource | Result) -> Result:  # type: ignore[override]
        return self.run(hypothesis)
