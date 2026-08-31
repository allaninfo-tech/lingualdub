"""Tests for lingualdub.core.segment."""

import pytest
from lingualdub.core.segment import Segment


def test_segment_duration():
    seg = Segment(start=1.0, end=3.5, text="hello", language="lug")
    assert seg.duration == pytest.approx(2.5)


def test_segment_invalid_timing():
    with pytest.raises(ValueError):
        Segment(start=3.0, end=1.0, text="oops", language="lug")

def test_segment_negative_start():
    with pytest.raises(ValueError):
        Segment(start=-1.0, end=1.0, text="oops", language="lug")


def test_segment_zero_start():
    seg = Segment(start=0.0, end=1.0, text="hello", language="lug")
    assert seg.start == 0.0


def test_segment_zero_duration():
    seg = Segment(start=1.0, end=1.0, text="", language="lug")
    assert seg.duration == 0.0


def test_segment_optional_fields_default_none():
    seg = Segment(start=0.0, end=1.0, text="hi", language="lug")
    assert seg.speaker is None
    assert seg.confidence is None
    assert seg.source_language is None
