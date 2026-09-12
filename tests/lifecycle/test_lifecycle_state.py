import pytest

from lingualdub.exceptions import LifecycleError
from lingualdub.lifecycle import FrameworkLifecycle, LifecycleState


def test_legal_sequence():
    lc = FrameworkLifecycle()
    seq = [
        LifecycleState.CONFIGURING,
        LifecycleState.CONFIGURED,
        LifecycleState.INITIALIZING,
        LifecycleState.READY,
        LifecycleState.RUNNING,
        LifecycleState.READY,
        LifecycleState.SHUTTING_DOWN,
        LifecycleState.STOPPED,
    ]
    for s in seq:
        lc.transition(s)
    assert lc.state == LifecycleState.STOPPED
    assert lc.history == [LifecycleState.UNINITIALIZED] + seq


def test_illegal_transition_raises():
    lc = FrameworkLifecycle()
    with pytest.raises(LifecycleError) as e:
        lc.transition(LifecycleState.READY)  # UNINITIALIZED -> READY illegal
    assert e.value.code == "LIFECYCLE_001"


def test_ensure_allowed():
    lc = FrameworkLifecycle()
    lc.transition(LifecycleState.CONFIGURING)
    lc.ensure(LifecycleState.CONFIGURING)
    with pytest.raises(LifecycleError) as e:
        lc.ensure(LifecycleState.READY)
    assert e.value.code == "LIFECYCLE_002"


def test_can_transition():
    lc = FrameworkLifecycle()
    assert lc.can_transition(LifecycleState.CONFIGURING) is True
    assert lc.can_transition(LifecycleState.RUNNING) is False


def test_history_immutable_copy():
    lc = FrameworkLifecycle()
    h = lc.history
    h.append(LifecycleState.STOPPED)  # type: ignore
    assert LifecycleState.STOPPED not in lc.history
