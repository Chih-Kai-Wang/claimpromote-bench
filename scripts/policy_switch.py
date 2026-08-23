#!/usr/bin/env python3
"""Executable author policy for the counterfactual profile-switch study."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from slsa_policy import candidate_state, quarantined_state, validate_item, validate_policy

Json = dict[str, Any]


def load_switch_policy(path: Path, base_policy: Json) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("policy-switch contract must be a JSON object")
    validate_switch_policy(value, base_policy)
    return value


def validate_switch_policy(policy: Json, base_policy: Json) -> None:
    validate_policy(base_policy)
    if policy.get("schema_version") != "1.0.0":
        raise ValueError("unsupported policy-switch schema version")
    if policy.get("action_precedence") != ["DEMOTE", "ESCALATE", "HOLD", "ALLOW"]:
        raise ValueError("unexpected policy-switch action precedence")
    order = policy.get("profile_order")
    profiles = policy.get("profiles")
    if order != ["POLICY_BLUE", "POLICY_AMBER"] or not isinstance(profiles, dict):
        raise ValueError("policy-switch profiles are malformed")
    if set(profiles) != set(order):
        raise ValueError("profile order and profile map differ")

    boolean_fields = {str(row["field"]) for row in base_policy["boolean_checks"]}
    conflict_codes = {str(value) for value in base_policy["authenticated_conflict_codes"]}
    seen_fields: set[str] = set()
    seen_conflicts: set[str] = set()
    for profile_id in order:
        profile = profiles[profile_id]
        if not isinstance(profile, dict):
            raise ValueError(f"{profile_id} must be an object")
        fields = profile.get("enforced_boolean_fields")
        conflicts = profile.get("escalated_conflict_codes")
        if not isinstance(fields, list) or not all(isinstance(value, str) for value in fields):
            raise ValueError(f"{profile_id} enforced fields are malformed")
        if not isinstance(conflicts, list) or not all(
            isinstance(value, str) for value in conflicts
        ):
            raise ValueError(f"{profile_id} conflict codes are malformed")
        if len(fields) != len(set(fields)) or set(fields) - boolean_fields:
            raise ValueError(f"{profile_id} contains duplicate or unknown fields")
        if len(conflicts) != len(set(conflicts)) or set(conflicts) - conflict_codes:
            raise ValueError(f"{profile_id} contains duplicate or unknown conflicts")
        if seen_fields & set(fields) or seen_conflicts & set(conflicts):
            raise ValueError("profile rules overlap")
        seen_fields.update(fields)
        seen_conflicts.update(conflicts)
    if len(seen_fields) != 8 or seen_conflicts != conflict_codes:
        raise ValueError("policy-switch factor inventory is incomplete")


def _ordered(values: list[str], base_policy: Json) -> list[str]:
    rank = {str(value): index for index, value in enumerate(base_policy["reason_order"])}
    if unknown := sorted(set(values) - set(rank)):
        raise ValueError(f"reason codes absent from base policy: {unknown}")
    return sorted(dict.fromkeys(values), key=rank.__getitem__)


def evaluate_policy_switch(item: Json, switch_policy: Json, base_policy: Json) -> Json:
    """Return the definitional action under the item's active counterfactual profile."""

    validate_switch_policy(switch_policy, base_policy)
    validate_item(item, base_policy)
    profile_id = item.get("active_policy_profile")
    if profile_id not in switch_policy["profile_order"]:
        raise ValueError("item has an unknown active policy profile")
    profile = switch_policy["profiles"][profile_id]
    current = deepcopy(item["current_state"])
    requested = deepcopy(item["requested_state"])
    evidence = item["evidence"][0]
    evidence_id = str(evidence["evidence_id"])
    observed = evidence["observed"]
    reason_by_field = {
        str(row["field"]): str(row["reason_code"]) for row in base_policy["boolean_checks"]
    }
    failed_reasons = [
        reason_by_field[field]
        for field in profile["enforced_boolean_fields"]
        if observed[field] is False
    ]
    escalated_conflicts = [
        str(code)
        for code in observed["authenticated_conflicts"]
        if code in profile["escalated_conflict_codes"]
    ]
    used_ids = [evidence_id] if observed["provenance_present"] else []
    missing_ids = [] if observed["provenance_present"] else [evidence_id]

    if current["release_status"] == "ADMITTED" and failed_reasons:
        return {
            "action": "DEMOTE",
            "proposed_state": candidate_state(),
            "p_admissible": 1.0,
            "used_evidence_ids": used_ids,
            "reason_codes": _ordered(
                ["CURRENT_RELEASE_BASIS_INVALID", *failed_reasons], base_policy
            ),
            "missing_evidence_ids": missing_ids,
        }
    if escalated_conflicts:
        return {
            "action": "ESCALATE",
            "proposed_state": quarantined_state(),
            "p_admissible": 1.0,
            "used_evidence_ids": [evidence_id],
            "reason_codes": _ordered(
                ["AUTHENTICATED_ATTESTATION_CONFLICT", *escalated_conflicts], base_policy
            ),
            "missing_evidence_ids": [],
        }
    if failed_reasons:
        return {
            "action": "HOLD",
            "proposed_state": current,
            "p_admissible": 0.0,
            "used_evidence_ids": used_ids,
            "reason_codes": _ordered(failed_reasons, base_policy),
            "missing_evidence_ids": missing_ids,
        }
    return {
        "action": "ALLOW",
        "proposed_state": requested,
        "p_admissible": 1.0,
        "used_evidence_ids": [evidence_id],
        "reason_codes": ["POLICY_SATISFIED"],
        "missing_evidence_ids": [],
    }
