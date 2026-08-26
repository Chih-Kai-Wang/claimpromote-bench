"""Executable SLSA-derived artifact-admission policy for the portability study.

SLSA and in-toto define attestation and verification semantics.  The transition actions in this
module are an author-defined operational policy layered on those checks.  Keeping that boundary in
code prevents the study from presenting its labels as SLSA conformance certificates.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

from claimpromotebench.dataset import validate_with_schema

Json = dict[str, Any]
ParseStatus = Literal["OK", "JSON_SYNTAX_ERROR", "SCHEMA_ERROR", "SEMANTIC_ERROR"]

ACTIONS = ("ALLOW", "HOLD", "DEMOTE", "ESCALATE")
STATE_KEYS = ("release_status", "accepted_build_level", "incident_review_required")


def _ordered(values: list[str], order: list[str]) -> list[str]:
    rank = {value: index for index, value in enumerate(order)}
    if unknown := sorted(set(values) - set(rank)):
        raise ValueError(f"reason codes absent from policy: {unknown}")
    return sorted(dict.fromkeys(values), key=rank.__getitem__)


def load_slsa_policy(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("SLSA-derived policy must be a JSON object")
    validate_policy(value)
    return value


def validate_policy(policy: Json) -> None:
    if policy.get("schema_version") != "1.0.0":
        raise ValueError("unsupported SLSA-derived policy schema version")
    if policy.get("action_precedence") != ["DEMOTE", "ESCALATE", "HOLD", "ALLOW"]:
        raise ValueError("unexpected action precedence")
    checks = policy.get("boolean_checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("policy.boolean_checks must be a non-empty list")
    fields: set[str] = set()
    reasons: set[str] = set()
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("each boolean check must be an object")
        field = check.get("field")
        reason = check.get("reason_code")
        if not isinstance(field, str) or not isinstance(reason, str):
            raise ValueError("each boolean check needs field and reason_code")
        if field in fields:
            raise ValueError(f"duplicate boolean check: {field}")
        fields.add(field)
        reasons.add(reason)
    conflicts = policy.get("authenticated_conflict_codes")
    if not isinstance(conflicts, list) or not all(isinstance(value, str) for value in conflicts):
        raise ValueError("authenticated_conflict_codes must be a list of strings")
    reason_order = policy.get("reason_order")
    if not isinstance(reason_order, list) or not all(
        isinstance(value, str) for value in reason_order
    ):
        raise ValueError("reason_order must be a list of strings")
    required = {
        "CURRENT_RELEASE_BASIS_INVALID",
        "AUTHENTICATED_ATTESTATION_CONFLICT",
        "BUILD_LEVEL_BELOW_TARGET",
        "POLICY_SATISFIED",
        *reasons,
        *conflicts,
    }
    if set(reason_order) != required or len(reason_order) != len(required):
        raise ValueError("reason_order does not enumerate each policy reason exactly once")


def candidate_state() -> Json:
    return {
        "release_status": "CANDIDATE",
        "accepted_build_level": 0,
        "incident_review_required": False,
    }


def quarantined_state() -> Json:
    return {
        "release_status": "QUARANTINED",
        "accepted_build_level": 0,
        "incident_review_required": True,
    }


def validate_state(state: Any, label: str) -> None:
    if not isinstance(state, dict) or set(state) != set(STATE_KEYS):
        raise ValueError(f"{label} must contain the canonical state fields")
    if state["release_status"] not in {"CANDIDATE", "ADMITTED", "QUARANTINED"}:
        raise ValueError(f"{label}.release_status is invalid")
    level = state["accepted_build_level"]
    if not isinstance(level, int) or isinstance(level, bool) or level not in {0, 1, 2, 3}:
        raise ValueError(f"{label}.accepted_build_level is invalid")
    if not isinstance(state["incident_review_required"], bool):
        raise ValueError(f"{label}.incident_review_required must be boolean")
    if state["release_status"] == "CANDIDATE" and (level != 0 or state["incident_review_required"]):
        raise ValueError(f"{label} has an inconsistent candidate state")
    if state["release_status"] == "ADMITTED" and (level == 0 or state["incident_review_required"]):
        raise ValueError(f"{label} has an inconsistent admitted state")
    if state["release_status"] == "QUARANTINED" and (
        level != 0 or not state["incident_review_required"]
    ):
        raise ValueError(f"{label} has an inconsistent quarantined state")


def validate_item(item: Json, policy: Json) -> None:
    validate_policy(policy)
    if item.get("schema_version") != "1.0.0":
        raise ValueError("unsupported SLSA item schema version")
    validate_state(item.get("current_state"), "current_state")
    validate_state(item.get("requested_state"), "requested_state")
    requested = item["requested_state"]
    if requested["release_status"] != "ADMITTED":
        raise ValueError("requested state must be an admitted state")
    evidence = item.get("evidence")
    if not isinstance(evidence, list) or len(evidence) != 1 or not isinstance(evidence[0], dict):
        raise ValueError("each study item must contain one evidence snapshot")
    if not isinstance(evidence[0].get("evidence_id"), str):
        raise ValueError("evidence snapshot lacks evidence_id")
    observed = evidence[0].get("observed")
    if not isinstance(observed, dict):
        raise ValueError("evidence snapshot lacks observed checks")
    expected_fields = {str(check["field"]) for check in policy["boolean_checks"]} | {
        "build_level_verified",
        "authenticated_conflicts",
    }
    if set(observed) != expected_fields:
        raise ValueError("observed checks differ from the policy contract")
    for field in expected_fields - {"build_level_verified", "authenticated_conflicts"}:
        if not isinstance(observed[field], bool):
            raise ValueError(f"observed.{field} must be boolean")
    level = observed["build_level_verified"]
    if not isinstance(level, int) or isinstance(level, bool) or level not in {0, 1, 2, 3}:
        raise ValueError("observed.build_level_verified is invalid")
    conflicts = observed["authenticated_conflicts"]
    allowed_conflicts = set(policy["authenticated_conflict_codes"])
    if not isinstance(conflicts, list) or not all(isinstance(value, str) for value in conflicts):
        raise ValueError("observed.authenticated_conflicts must be a list of strings")
    if len(conflicts) != len(set(conflicts)) or set(conflicts) - allowed_conflicts:
        raise ValueError("observed.authenticated_conflicts contains duplicate or unknown values")


def evaluate_slsa(item: Json, policy: Json) -> Json:
    """Return the definitional action for one SLSA-derived policy item."""

    validate_item(item, policy)
    current = deepcopy(item["current_state"])
    requested = deepcopy(item["requested_state"])
    evidence = item["evidence"][0]
    evidence_id = str(evidence["evidence_id"])
    observed = evidence["observed"]
    check_reasons = [
        str(check["reason_code"])
        for check in policy["boolean_checks"]
        if observed[str(check["field"])] is False
    ]
    target_level = int(requested["accepted_build_level"])
    below_target = int(observed["build_level_verified"]) < target_level
    conflicts = [str(value) for value in observed["authenticated_conflicts"]]
    used_ids = [evidence_id] if observed["provenance_present"] else []
    missing_ids = [] if observed["provenance_present"] else [evidence_id]

    demote_reasons: list[str] = []
    if current["release_status"] == "ADMITTED":
        if check_reasons:
            demote_reasons.extend(check_reasons)
        if int(observed["build_level_verified"]) < int(current["accepted_build_level"]):
            demote_reasons.append("BUILD_LEVEL_BELOW_TARGET")
    if demote_reasons:
        reasons = _ordered(
            ["CURRENT_RELEASE_BASIS_INVALID", *demote_reasons], policy["reason_order"]
        )
        return {
            "action": "DEMOTE",
            "proposed_state": candidate_state(),
            "p_admissible": 1.0,
            "used_evidence_ids": used_ids,
            "reason_codes": reasons,
            "missing_evidence_ids": missing_ids,
        }
    if conflicts:
        reasons = _ordered(
            ["AUTHENTICATED_ATTESTATION_CONFLICT", *conflicts], policy["reason_order"]
        )
        return {
            "action": "ESCALATE",
            "proposed_state": quarantined_state(),
            "p_admissible": 1.0,
            "used_evidence_ids": [evidence_id],
            "reason_codes": reasons,
            "missing_evidence_ids": [],
        }
    hold_reasons = [*check_reasons]
    if below_target:
        hold_reasons.append("BUILD_LEVEL_BELOW_TARGET")
    if hold_reasons:
        return {
            "action": "HOLD",
            "proposed_state": current,
            "p_admissible": 0.0,
            "used_evidence_ids": used_ids,
            "reason_codes": _ordered(hold_reasons, policy["reason_order"]),
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


def validate_decision_semantics(item: Json, decision: Json, policy: Json) -> None:
    """Check internal decision semantics without evaluating the policy oracle."""

    validate_item(item, policy)
    action = decision["action"]
    current = item["current_state"]
    expected_state = {
        "ALLOW": item["requested_state"],
        "HOLD": current,
        "DEMOTE": candidate_state(),
        "ESCALATE": quarantined_state(),
    }[action]
    if decision["proposed_state"] != expected_state:
        raise ValueError("proposed_state is inconsistent with the declared action")
    evidence_ids = {str(value["evidence_id"]) for value in item["evidence"]}
    used = decision["used_evidence_ids"]
    missing = decision["missing_evidence_ids"]
    if set(used) - evidence_ids or set(missing) - evidence_ids:
        raise ValueError("decision references evidence absent from the item")
    if set(used) & set(missing):
        raise ValueError("used and missing evidence IDs must be disjoint")
    reasons = decision["reason_codes"]
    if not reasons:
        raise ValueError("reason_codes must not be empty")
    if reasons != _ordered(reasons, policy["reason_order"]):
        raise ValueError("reason_codes do not follow the policy order")
    reason_set = set(reasons)
    if action == "ALLOW" and reason_set != {"POLICY_SATISFIED"}:
        raise ValueError("ALLOW requires only POLICY_SATISFIED")
    if action == "HOLD" and reason_set & {
        "POLICY_SATISFIED",
        "CURRENT_RELEASE_BASIS_INVALID",
        "AUTHENTICATED_ATTESTATION_CONFLICT",
    }:
        raise ValueError("HOLD contains an incompatible reason")
    if action == "DEMOTE" and "CURRENT_RELEASE_BASIS_INVALID" not in reason_set:
        raise ValueError("DEMOTE requires CURRENT_RELEASE_BASIS_INVALID")
    if action == "ESCALATE" and "AUTHENTICATED_ATTESTATION_CONFLICT" not in reason_set:
        raise ValueError("ESCALATE requires AUTHENTICATED_ATTESTATION_CONFLICT")


def diagnose_slsa_decision(
    content: str,
    item: Json,
    policy: Json,
    *,
    schema_path: Path,
) -> tuple[ParseStatus, Json | None, str | None]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        return "JSON_SYNTAX_ERROR", None, f"{exc.msg} at line {exc.lineno} column {exc.colno}"
    if not isinstance(value, dict):
        return "SCHEMA_ERROR", None, "top-level JSON value is not an object"
    try:
        validate_with_schema(value, schema_path, "SLSA portability decision")
    except Exception as exc:
        return "SCHEMA_ERROR", None, str(exc)
    try:
        validate_decision_semantics(item, value, policy)
    except Exception as exc:
        return "SEMANTIC_ERROR", None, str(exc)
    return "OK", value, None
