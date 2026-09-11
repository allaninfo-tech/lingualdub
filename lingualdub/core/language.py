# Copyright 2026 LingualDub Authors.
# SPDX-License-Identifier: Apache-2.0

"""
Language abstraction.

Represents a language together with its metadata, resource profile,
supported tasks, available resources, related languages, and compatible
components. Resource profile is a first-class property — the framework
does not assume every language has identical data or model coverage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lingualdub.types import LanguageCode, MetadataDict
from lingualdub.utils.validation import require_non_empty_string, validate_language_code


@dataclass
class Language:
    """
    A language registered with the framework.

    Attributes:
        code: Short language identifier (e.g. "lug", "nyn", "eng").
        name: Human-readable name (e.g. "Luganda").
        family: Language family or sub-family (e.g. "Bantu (Great Lakes)").
        resource_profile: A descriptive label of the language's data situation
            (e.g. "speech-scarce / text-moderate"). Guides adaptation strategy
            and component selection.
        supported_tasks: Tasks the framework can attempt for this language
            given current available resources and components.
        related_languages: Codes of languages with shared properties that
            may be leveraged for transfer or cross-lingual adaptation.
        resources: References to registered Resource objects for this language.
            These are references, not copies.
        compatible_components: Names of components verified to support this language.
    """

    code: LanguageCode
    name: str
    family: str
    resource_profile: str
    supported_tasks: list[str] = field(default_factory=list)
    related_languages: list[LanguageCode] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    compatible_components: list[str] = field(default_factory=list)
    metadata: MetadataDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_empty_string(self.code, "code")
        require_non_empty_string(self.name, "name")
        # Validate language code format (2–3 letters). Uses centered helper so
        # callers get ConfigurationValidationError instead of bare ValueError.
        validate_language_code(self.code)
        # family and resource_profile are descriptive but should be non-empty
        require_non_empty_string(self.family, "family")
        require_non_empty_string(self.resource_profile, "resource_profile")

    def to_dict(self) -> dict[str, Any]:
        """Serialize this Language to a JSON-compatible dictionary.

        The returned dictionary is a deep copy suitable for JSON serialization
        and round-trip via :meth:`from_dict`.
        """
        return {
            "code": self.code,
            "name": self.name,
            "family": self.family,
            "resource_profile": self.resource_profile,
            "supported_tasks": list(self.supported_tasks),
            "related_languages": list(self.related_languages),
            "resources": list(self.resources),
            "compatible_components": list(self.compatible_components),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Language:
        """Deserialize a Language from a dictionary produced by :meth:`to_dict`.

        Validation is explicit and schema-aware:

        * ``data`` must be a ``dict`` — otherwise :class:`SerializationError`.
        * Required keys ``code``, ``name``, ``family``, ``resource_profile`` must
          be present — otherwise ``SerializationError`` naming the missing field.
        * Field types are validated (e.g. ``code`` must be a valid language code
          and ``supported_tasks`` must be a list).  Failures raise
          :class:`SerializationError` or :class:`ConfigurationValidationError`
          with the offending field in ``context``.
        * Unknown keys are preserved in ``metadata`` rather than crashing, to
          allow forward-compatible schema evolution.

        Round-trip idempotence is guaranteed: ``cls.from_dict(obj.to_dict()) == obj``
        for any valid ``obj``.

        Args:
            data: Dictionary to decode — typically produced by :meth:`to_dict`.

        Raises:
            SerializationError: If ``data`` is not a dict, required keys are
                missing, or a field has the wrong type.
            ConfigurationValidationError: If a field value fails domain validation
                (e.g. invalid language code format).
        """
        from lingualdub.exceptions import SerializationError

        if not isinstance(data, dict):
            raise SerializationError(
                f"Language.from_dict expects a dict, got {type(data).__name__}: {data!r}.",
                field="data",
                code="LANG_DESER_001",
            )

        known_keys = {
            "code",
            "name",
            "family",
            "resource_profile",
            "supported_tasks",
            "related_languages",
            "resources",
            "compatible_components",
            "metadata",
        }
        required_keys = ("code", "name", "family", "resource_profile")
        for key in required_keys:
            if key not in data:
                raise SerializationError(
                    f"Missing required field '{key}' for Language.",
                    field=key,
                    code="LANG_DESER_002",
                    context={"data_keys": list(data.keys())},
                )

        # Validate optional collection types explicitly before construction so the
        # error is a clear SerializationError naming the field rather than a
        # cryptic TypeError deeper in the stack.
        optional_lists = (
            "supported_tasks",
            "related_languages",
            "resources",
            "compatible_components",
        )
        for key in optional_lists:
            if key in data and data[key] is not None and not isinstance(data[key], list):
                raise SerializationError(
                    f"Field '{key}' must be a list, got {type(data[key]).__name__}: {data[key]!r}.",
                    field=key,
                    code="LANG_DESER_003",
                )

        if (
            "metadata" in data
            and data["metadata"] is not None
            and not isinstance(data["metadata"], dict)
        ):
            raise SerializationError(
                f"Field 'metadata' must be a dict, got {type(data['metadata']).__name__}: {data['metadata']!r}.",
                field="metadata",
                code="LANG_DESER_003",
            )

        # Preserve unknown keys in metadata for forward compatibility
        base_metadata = dict(data.get("metadata") or {})
        unknown = {k: v for k, v in data.items() if k not in known_keys}
        merged_metadata = {**base_metadata, **unknown} if unknown else base_metadata

        # Construction delegates string/code validation to __post_init__
        # (which raises ConfigurationValidationError).  We let that propagate
        # because it is the correct hierarchy for domain validation.
        return cls(
            code=data["code"],
            name=data["name"],
            family=data["family"],
            resource_profile=data["resource_profile"],
            supported_tasks=list(data.get("supported_tasks") or []),
            related_languages=list(data.get("related_languages") or []),
            resources=list(data.get("resources") or []),
            compatible_components=list(data.get("compatible_components") or []),
            metadata=merged_metadata,
        )

    def __repr__(self) -> str:
        return (
            f"Language(code={self.code!r}, name={self.name!r}, profile={self.resource_profile!r})"
        )
