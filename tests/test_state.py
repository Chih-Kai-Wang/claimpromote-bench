from __future__ import annotations

import pytest

from claimpromotebench.errors import PredictionFormatError
from claimpromotebench.state import changed_axes, is_strict_demotion, state_leq

BASE = {
    "research_status": "PROPOSED",
    "computation_status": "NONE",
    "formal_status": "NONE",
    "review_status": "UNREVIEWED",
}


def test_partial_order_is_reflexive() -> None:
    assert state_leq(BASE, BASE)


def test_axes_are_orthogonal() -> None:
    computed = {**BASE, "computation_status": "COMPUTATIONAL"}
    formal = {**BASE, "formal_status": "FORMALLY_CERTIFIED"}
    assert not state_leq(computed, formal)
    assert not state_leq(formal, computed)
    assert changed_axes(BASE, computed) == ("computation_status",)


def test_strict_demotion() -> None:
    current = {**BASE, "research_status": "OPEN", "computation_status": "COMPUTATIONAL"}
    demoted = {**current, "computation_status": "NONE"}
    assert is_strict_demotion(demoted, current)
    assert not is_strict_demotion(current, current)


def test_invalid_state_is_rejected() -> None:
    with pytest.raises(PredictionFormatError):
        state_leq({**BASE, "formal_status": "MAYBE"}, BASE)
