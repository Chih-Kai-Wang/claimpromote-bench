"""Operations on the four orthogonal claim-state axes."""

from __future__ import annotations

import math
from typing import Any

from .errors import PredictionFormatError

STATE_ORDER: dict[str, tuple[str, ...]] = {
    "research_status": ("PROPOSED", "OPEN", "RESOLVED"),
    "computation_status": ("NONE", "COMPUTATIONAL"),
    "formal_status": ("NONE", "FORMALLY_CERTIFIED"),
    "review_status": ("UNREVIEWED", "INDEPENDENTLY_VERIFIED"),
}


def state_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Compare only the public state axes."""

    return all(left.get(axis) == right.get(axis) for axis in STATE_ORDER)


def state_leq(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Return whether every left axis is no stronger than the corresponding right axis."""

    for axis, order in STATE_ORDER.items():
        try:
            if order.index(str(left[axis])) > order.index(str(right[axis])):
                return False
        except (KeyError, ValueError) as exc:
            raise PredictionFormatError(f"invalid claim state at {axis}") from exc
    return True


def changed_axes(current: dict[str, Any], target: dict[str, Any]) -> tuple[str, ...]:
    """Return axes changed by a requested transition in public order."""

    return tuple(axis for axis in STATE_ORDER if current[axis] != target[axis])


def is_strict_demotion(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    """Check that candidate weakens at least one axis and strengthens none."""

    return state_leq(candidate, current) and not state_equal(candidate, current)


def validate_decision_semantics(item: dict[str, Any], decision: dict[str, Any]) -> None:
    """Apply cross-field constraints that JSON Schema cannot express."""

    action = decision["action"]
    proposed = decision["proposed_state"]
    current = item["current_state"]
    target = item["requested_transition"]["target_state"]
    if not math.isfinite(float(decision["p_admissible"])):
        raise PredictionFormatError("p_admissible must be finite")
    if action == "ALLOW" and not state_equal(proposed, target):
        raise PredictionFormatError("ALLOW must propose the requested target state")
    if action in {"HOLD", "ESCALATE"} and not state_equal(proposed, current):
        raise PredictionFormatError(f"{action} must retain the current state")
    if action == "DEMOTE" and not is_strict_demotion(proposed, current):
        raise PredictionFormatError("DEMOTE must strictly weaken at least one state axis")

    evidence_ids = {str(evidence["id"]) for evidence in item["evidence"]}
    used = [str(value) for value in decision["used_evidence_ids"]]
    if len(used) != len(set(used)) or not set(used) <= evidence_ids:
        raise PredictionFormatError("used_evidence_ids must be unique evidence IDs from the item")

    referenced_dependencies = {
        str(dependency)
        for evidence in item["evidence"]
        for dependency in evidence.get("dependencies", [])
    }
    missing = [str(value) for value in decision["missing_evidence_ids"]]
    if len(missing) != len(set(missing)) or not set(missing) <= referenced_dependencies:
        raise PredictionFormatError(
            "missing_evidence_ids must be unique dependency IDs referenced by the item"
        )
