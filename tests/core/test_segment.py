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
