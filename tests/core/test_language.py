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
