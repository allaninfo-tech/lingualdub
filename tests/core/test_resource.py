"""Tests for lingualdub.core.resource."""

import pytest
from lingualdub.core.resource import Resource, ResourceKind


def test_resource_creation():
    r = Resource(id="lug_v1", kind=ResourceKind.SPEECH, language="lug", version="1.0.0")
    assert r.id == "lug_v1"
    assert r.kind == ResourceKind.SPEECH
    assert r.language == "lug"
    assert r.version == "1.0.0"


def test_resource_requires_id():
    with pytest.raises(ValueError):
        Resource(id="", kind=ResourceKind.SPEECH, language="lug", version="1.0.0")


def test_resource_requires_language():
    with pytest.raises(ValueError):
        Resource(id="lug_v1", kind=ResourceKind.SPEECH, language="", version="1.0.0")


def test_resource_has_consent_false():
    r = Resource(id="lug_v1", kind=ResourceKind.SPEECH, language="lug", version="1.0.0")
    assert r.has_consent is False


def test_resource_has_consent_true():
    r = Resource(
        id="lug_v1", kind=ResourceKind.SPEECH, language="lug", version="1.0.0",
        provenance={"consent_basis": "explicit_written"},
    )
    assert r.has_consent is True


def test_resource_all_kinds():
    for kind in ResourceKind:
        r = Resource(id="x", kind=kind, language="lug", version="1.0.0")
        assert r.kind == kind


def test_resource_quality_flags():
    r = Resource(
        id="lug_v1", kind=ResourceKind.SPEECH, language="lug", version="1.0.0",
        quality_flags=["weak_transcripts"],
    )
    assert "weak_transcripts" in r.quality_flags


def test_resource_repr():
    r = Resource(id="lug_v1", kind=ResourceKind.SPEECH, language="lug", version="1.0.0")
    rep = repr(r)
    assert "lug_v1" in rep
    assert "speech" in rep
    assert "lug" in rep
    assert "1.0.0" in rep
