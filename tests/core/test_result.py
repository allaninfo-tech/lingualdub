"""Tests for lingualdub.core.result."""

from lingualdub.core.result import Result, ResultStatus


def test_result_defaults():
    result = Result()
    assert result.status == ResultStatus.COMPLETE
    assert result.is_usable is True


def test_result_mark_partial():
    result = Result()
    result.mark_partial("alignment skipped")
    assert result.status == ResultStatus.PARTIAL
    assert result.is_usable is True
    assert any("Partial" in w for w in result.warnings)


def test_result_mark_failed():
    result = Result()
    result.mark_failed("fatal error")
    assert result.status == ResultStatus.FAILED
    assert result.is_usable is False


def test_result_mark_degraded():
    result = Result()
    result.mark_degraded("poor audio quality")
    assert result.status == ResultStatus.DEGRADED
    assert result.is_usable is True
    assert any("Degraded" in w for w in result.warnings)


def test_result_add_warning():
    result = Result()
    result.add_warning("something minor")
    assert result.status == ResultStatus.COMPLETE
    assert "something minor" in result.warnings


def test_result_multiple_warnings():
    result = Result()
    result.add_warning("first")
    result.add_warning("second")
    assert len(result.warnings) == 2


def test_result_has_segments():
    from lingualdub.core.segment import Segment
    seg = Segment(start=0.0, end=1.0, text="hello", language="lug")
    result = Result(segments=[seg])
    assert len(result.segments) == 1
