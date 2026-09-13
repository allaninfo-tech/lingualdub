# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Test builders for core domain objects — REL-005.

Fluent builders that produce valid instances with sensible defaults, so tests
need only override fields relevant to the scenario:

    from lingualdub.testing.builders import ResourceBuilder, ResultBuilder, SegmentBuilder, LanguageBuilder

    seg = SegmentBuilder().with_text("Oli otya").with_language("lug").build()
    res = ResultBuilder().with_segments([seg]).with_status(ResultStatus.COMPLETE).build()
"""

from __future__ import annotations

from typing import Any

from lingualdub.core.language import Language
from lingualdub.core.resource import Resource, ResourceKind, ResourceOwnership
from lingualdub.core.result import Result, ResultStatus
from lingualdub.core.segment import Segment

__all__ = ["ResourceBuilder", "ResultBuilder", "SegmentBuilder", "LanguageBuilder"]


class LanguageBuilder:
    """Builder for :class:`Language`.

    Defaults produce a valid Luganda-like language:

        Language(code="lug", name="Luganda", family="Bantu (Great Lakes)",
                 resource_profile="speech-moderate / text-moderate")
    """

    def __init__(self) -> None:
        self._kwargs: dict[str, Any] = {
            "code": "lug",
            "name": "Luganda",
            "family": "Bantu (Great Lakes)",
            "resource_profile": "speech-moderate / text-moderate",
            "supported_tasks": ["asr", "translation"],
            "related_languages": ["nyn"],
            "resources": [],
            "compatible_components": [],
            "metadata": {},
        }

    def with_code(self, code: str) -> LanguageBuilder:
        self._kwargs["code"] = code
        return self

    def with_name(self, name: str) -> LanguageBuilder:
        self._kwargs["name"] = name
        return self

    def with_family(self, family: str) -> LanguageBuilder:
        self._kwargs["family"] = family
        return self

    def with_resource_profile(self, profile: str) -> LanguageBuilder:
        self._kwargs["resource_profile"] = profile
        return self

    def with_supported_tasks(self, tasks: list[str]) -> LanguageBuilder:
        self._kwargs["supported_tasks"] = list(tasks)
        return self

    def with_related_languages(self, langs: list[str]) -> LanguageBuilder:
        self._kwargs["related_languages"] = list(langs)
        return self

    def with_resources(self, resources: list[str]) -> LanguageBuilder:
        self._kwargs["resources"] = list(resources)
        return self

    def with_compatible_components(self, comps: list[str]) -> LanguageBuilder:
        self._kwargs["compatible_components"] = list(comps)
        return self

    def with_metadata(self, metadata: dict[str, Any]) -> LanguageBuilder:
        self._kwargs["metadata"] = dict(metadata)
        return self

    def build(self, **overrides: Any) -> Language:
        kwargs = {**self._kwargs, **overrides}
        return Language(**kwargs)


class ResourceBuilder:
    """Builder for :class:`Resource`.

    Defaults:

        Resource(id="test_resource", kind=SPEECH, language="lug",
                 version="1.0.0",
                 provenance={"source": "test", "license": "Apache-2.0"})
    """

    def __init__(self) -> None:
        self._kwargs: dict[str, Any] = {
            "id": "test_resource",
            "kind": ResourceKind.SPEECH,
            "language": "lug",
            "version": "1.0.0",
            "provenance": {"source": "test", "license": "Apache-2.0"},
            "quality_flags": [],
            "compatible_components": [],
            "path": None,
            "metadata": {},
            "ownership": ResourceOwnership.USER_OWNED,
        }

    def with_id(self, id: str) -> ResourceBuilder:
        self._kwargs["id"] = id
        return self

    def with_kind(self, kind: ResourceKind | str) -> ResourceBuilder:
        self._kwargs["kind"] = kind
        return self

    def with_language(self, language: str) -> ResourceBuilder:
        self._kwargs["language"] = language
        return self

    def with_version(self, version: str) -> ResourceBuilder:
        self._kwargs["version"] = version
        return self

    def with_provenance(self, provenance: dict[str, Any]) -> ResourceBuilder:
        self._kwargs["provenance"] = dict(provenance)
        return self

    def with_quality_flags(self, flags: list[str]) -> ResourceBuilder:
        self._kwargs["quality_flags"] = list(flags)
        return self

    def with_compatible_components(self, comps: list[str]) -> ResourceBuilder:
        self._kwargs["compatible_components"] = list(comps)
        return self

    def with_path(self, path: Any) -> ResourceBuilder:
        self._kwargs["path"] = path
        return self

    def with_metadata(self, metadata: dict[str, Any]) -> ResourceBuilder:
        self._kwargs["metadata"] = dict(metadata)
        return self

    def with_ownership(self, ownership: ResourceOwnership | str) -> ResourceBuilder:
        self._kwargs["ownership"] = ownership
        return self

    def build(self, **overrides: Any) -> Resource:
        kwargs = {**self._kwargs, **overrides}
        return Resource(**kwargs)


class SegmentBuilder:
    """Builder for :class:`Segment`.

    Defaults: ``start=0.0, end=1.0, text="hello", language="lug"``

    Example:
        seg = SegmentBuilder().with_text("Oli otya").with_language("lug").build()
    """

    def __init__(self) -> None:
        self._kwargs: dict[str, Any] = {
            "start": 0.0,
            "end": 1.0,
            "text": "hello",
            "language": "lug",
            "speaker": None,
            "confidence": None,
            "source_language": None,
            "provenance": {},
            "metadata": {},
        }

    def with_start(self, start: float) -> SegmentBuilder:
        self._kwargs["start"] = float(start)
        return self

    def with_end(self, end: float) -> SegmentBuilder:
        self._kwargs["end"] = float(end)
        return self

    def with_text(self, text: str) -> SegmentBuilder:
        self._kwargs["text"] = text
        return self

    def with_language(self, language: str) -> SegmentBuilder:
        self._kwargs["language"] = language
        return self

    def with_speaker(self, speaker: str | None) -> SegmentBuilder:
        self._kwargs["speaker"] = speaker
        return self

    def with_confidence(self, confidence: float | None) -> SegmentBuilder:
        self._kwargs["confidence"] = confidence
        return self

    def with_source_language(self, lang: str | None) -> SegmentBuilder:
        self._kwargs["source_language"] = lang
        return self

    def with_provenance(self, provenance: dict[str, Any]) -> SegmentBuilder:
        self._kwargs["provenance"] = dict(provenance)
        return self

    def with_metadata(self, metadata: dict[str, Any]) -> SegmentBuilder:
        self._kwargs["metadata"] = dict(metadata)
        return self

    def build(self, **overrides: Any) -> Segment:
        kwargs = {**self._kwargs, **overrides}
        return Segment(**kwargs)


class ResultBuilder:
    """Builder for :class:`Result`.

    Defaults: single ``lug`` segment, ``source_language="lug"``, ``COMPLETE``,
    provenance with deterministic ``run_id``.

    Example:
        result = ResultBuilder().with_segments([seg1, seg2]).with_source_language("lug").build()
        result = ResultBuilder().with_status(ResultStatus.FAILED).build()
    """

    def __init__(self) -> None:
        # Default segment for convenience
        default_seg = Segment(start=0.0, end=1.0, text="hello", language="lug")
        self._kwargs: dict[str, Any] = {
            "segments": [default_seg],
            "source_language": "lug",
            "target_language": None,
            "status": ResultStatus.COMPLETE,
            "warnings": [],
            "provenance": {"run_id": "test-run-builder"},
            "artifacts": [],
            "metadata": {},
        }

    def with_segments(self, segments: list[Segment]) -> ResultBuilder:
        self._kwargs["segments"] = list(segments)
        return self

    def with_source_language(self, lang: str | None) -> ResultBuilder:
        self._kwargs["source_language"] = lang
        return self

    def with_target_language(self, lang: str | None) -> ResultBuilder:
        self._kwargs["target_language"] = lang
        return self

    def with_status(self, status: ResultStatus) -> ResultBuilder:
        self._kwargs["status"] = status
        return self

    def with_warnings(self, warnings: list[str]) -> ResultBuilder:
        self._kwargs["warnings"] = list(warnings)
        return self

    def with_provenance(self, provenance: dict[str, Any]) -> ResultBuilder:
        self._kwargs["provenance"] = dict(provenance)
        return self

    def with_artifacts(self, artifacts: list[str]) -> ResultBuilder:
        self._kwargs["artifacts"] = list(artifacts)
        return self

    def with_metadata(self, metadata: dict[str, Any]) -> ResultBuilder:
        self._kwargs["metadata"] = dict(metadata)
        return self

    def add_segment(self, segment: Segment) -> ResultBuilder:
        self._kwargs["segments"].append(segment)
        return self

    def build(self, **overrides: Any) -> Result:
        kwargs = {**self._kwargs, **overrides}
        # Ensure copy
        if "segments" in kwargs and isinstance(kwargs["segments"], list):
            kwargs["segments"] = list(kwargs["segments"])
        if "warnings" in kwargs:
            kwargs["warnings"] = list(kwargs["warnings"])
        if "artifacts" in kwargs:
            kwargs["artifacts"] = list(kwargs["artifacts"])
        if "provenance" in kwargs:
            kwargs["provenance"] = dict(kwargs["provenance"])
        if "metadata" in kwargs:
            kwargs["metadata"] = dict(kwargs["metadata"])
        return Result(**kwargs)
