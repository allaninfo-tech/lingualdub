"""
Language abstraction.

Represents a language together with its metadata, resource profile,
supported tasks, available resources, related languages, and compatible
components. Resource profile is a first-class property — the framework
does not assume every language has identical data or model coverage.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


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

    code: str
    name: str
    family: str
    resource_profile: str
    supported_tasks: List[str] = field(default_factory=list)
    related_languages: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    compatible_components: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("Language.code must not be empty.")
        if not self.name:
            raise ValueError("Language.name must not be empty.")

    def __repr__(self) -> str:
        return f"Language(code={self.code!r}, name={self.name!r}, profile={self.resource_profile!r})"
