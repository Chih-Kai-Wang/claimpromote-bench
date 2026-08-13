"""Deterministic non-model baselines."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .oracle import evaluate

BASELINES = ("always_allow", "always_hold", "policy_oracle")


def baseline_decision(
    name: str,
    item: dict[str, Any],
    policy: dict[str, Any],
    evaluation_time: str,
) -> dict[str, Any]:
    """Return one decision; none of these baselines calls a model."""

    if name == "always_allow":
        return {
            "action": "ALLOW",
            "proposed_state": deepcopy(item["requested_transition"]["target_state"]),
            "p_admissible": 1.0,
            "used_evidence_ids": [],
            "reason_codes": ["BASELINE_ALWAYS_ALLOW"],
            "missing_evidence_ids": [],
        }
    if name == "always_hold":
        return {
            "action": "HOLD",
            "proposed_state": deepcopy(item["current_state"]),
            "p_admissible": 0.0,
            "used_evidence_ids": [],
            "reason_codes": ["BASELINE_ALWAYS_HOLD"],
            "missing_evidence_ids": [],
        }
    if name == "policy_oracle":
        result = evaluate(item, policy, evaluation_time)
        return {
            key: deepcopy(result[key])
            for key in (
                "action",
                "proposed_state",
                "p_admissible",
                "used_evidence_ids",
                "reason_codes",
                "missing_evidence_ids",
            )
        }
    raise ValueError(f"unknown baseline: {name}")
