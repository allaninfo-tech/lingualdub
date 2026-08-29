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
