"""Tests for lingualdub.core.language."""

import pytest
from lingualdub.core.language import Language


def test_language_creation():
    lang = Language(
        code="lug",
        name="Luganda",
        family="Bantu (Great Lakes)",
        resource_profile="speech-moderate / text-moderate",
    )
    assert lang.code == "lug"
    assert lang.name == "Luganda"


def test_language_requires_code():
    with pytest.raises(ValueError):
        Language(code="", name="Luganda", family="Bantu", resource_profile="sparse")


def test_language_requires_name():
    with pytest.raises(ValueError):
        Language(code="lug", name="", family="Bantu", resource_profile="sparse")


def test_language_defaults():
    lang = Language(code="lug", name="Luganda", family="Bantu", resource_profile="sparse")
    assert lang.supported_tasks == []
    assert lang.related_languages == []
    assert lang.resources == []
    assert lang.compatible_components == []


def test_language_metadata():
    lang = Language(
        code="lug", name="Luganda", family="Bantu", resource_profile="sparse",
        metadata={"region": "Uganda"},
    )
    assert lang.metadata["region"] == "Uganda"


def test_language_repr():
    lang = Language(code="lug", name="Luganda", family="Bantu", resource_profile="sparse")
    r = repr(lang)
    assert "lug" in r
    assert "Luganda" in r
