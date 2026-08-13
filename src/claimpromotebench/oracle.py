"""Pure deterministic oracle for the alpha transition policy."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from datetime import datetime
from typing import Any

from .errors import DatasetIntegrityError
from .policy import interval_covers, parse_timestamp
from .state import changed_axes, state_leq


def _ordered_unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _closure(
    roots: list[str], evidence_by_id: dict[str, dict[str, Any]]
) -> tuple[list[str], list[str], bool]:
    visited: set[str] = set()
    visiting: set[str] = set()
    missing: list[str] = []
    ordered: list[str] = []
    cycle = False

    def visit(evidence_id: str) -> None:
        nonlocal cycle
        if evidence_id in visiting:
            cycle = True
            return
        if evidence_id in visited:
            return
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            missing.append(evidence_id)
            return
        visiting.add(evidence_id)
        for dependency in sorted(str(value) for value in evidence.get("dependencies", [])):
            visit(dependency)
        visiting.remove(evidence_id)
        visited.add(evidence_id)
        ordered.append(evidence_id)

    for root in sorted(roots):
        visit(root)
    return ordered, sorted(set(missing)), cycle


def _demoted_state(item: dict[str, Any], invalid_axes: set[str]) -> dict[str, Any]:
    state = deepcopy(item["current_state"])
    bases = {
        "research_status": "PROPOSED",
        "computation_status": "NONE",
        "formal_status": "NONE",
        "review_status": "UNREVIEWED",
    }
    for axis in invalid_axes:
        state[axis] = bases[axis]
    return dict(state)


CURRENT_AXIS_BASIS: dict[str, tuple[str, str]] = {
    "computation_status": ("COMPUTATIONAL", "COMPUTATION"),
    "formal_status": ("FORMALLY_CERTIFIED", "FORMAL_CERTIFICATE"),
    "review_status": ("INDEPENDENTLY_VERIFIED", "REVIEW"),
}


def evaluate(
    item: dict[str, Any], policy: dict[str, Any], evaluation_time: str | datetime
) -> dict[str, Any]:
    """Evaluate a benchmark input without reading clocks, files, networks, or models."""

    if item.get("policy_id") != policy.get("policy_id"):
        raise DatasetIntegrityError("item policy_id does not match loaded policy")
    if item.get("policy_version") != policy.get("policy_version"):
        raise DatasetIntegrityError("item policy_version does not match loaded policy")
    if isinstance(evaluation_time, str):
        frozen_time = parse_timestamp(evaluation_time)
    else:
        if evaluation_time.tzinfo is None:
            raise DatasetIntegrityError("evaluation_time must be timezone-aware")
        frozen_time = evaluation_time
    if parse_timestamp(str(policy["evaluation_time"])) != frozen_time:
        raise DatasetIntegrityError("evaluation_time does not match the loaded policy")

    current = item["current_state"]
    target = item["requested_transition"]["target_state"]
    if not state_leq(current, target) or not changed_axes(current, target):
        raise DatasetIntegrityError("requested transition must strictly promote at least one axis")

    evidence_values = item.get("evidence", [])
    evidence_ids = [str(evidence["id"]) for evidence in evidence_values]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise DatasetIntegrityError("evidence IDs must be unique")
    evidence_by_id = {str(evidence["id"]): evidence for evidence in evidence_values}
    roots = [str(value) for value in item["requested_transition"]["basis_evidence_ids"]]
    closure, missing, cycle = _closure(roots, evidence_by_id)

    hold_reasons: list[str] = []
    escalate_reasons: list[str] = []
    demote_reasons: list[str] = []
    minimal_missing: list[str] = []

    if missing:
        hold_reasons.append("MISSING_DEPENDENCY")
        minimal_missing.extend(missing)
    if cycle:
        hold_reasons.append("DEPENDENCY_CYCLE")

    root_set = set(roots)
    for evidence_id in closure:
        evidence = evidence_by_id[evidence_id]
        is_dependency = evidence_id not in root_set
        tool_exit = evidence.get("tool_exit")
        verifier_result = evidence.get("verifier_result")
        if is_dependency and tool_exit != 0:
            hold_reasons.append("DEPENDENCY_RUNTIME_FAILURE")
        if is_dependency and verifier_result != "PASS":
            hold_reasons.append("DEPENDENCY_NOT_VERIFIED")

        scope = evidence.get("scope", {})
        claim_id = scope.get("claim_id")
        if claim_id != item["claim_context"]["claim_id"]:
            hold_reasons.append("CLAIM_ID_MISMATCH")
        statement = scope.get("statement_sha256")
        if statement != item["claim_context"]["statement_sha256"]:
            hold_reasons.append("STATEMENT_HASH_MISMATCH")

        if evidence_id in root_set:
            if tool_exit is None:
                hold_reasons.append("RUN_INCOMPLETE")
            elif tool_exit != 0:
                hold_reasons.append("TOOL_EXIT_NONZERO")
            if verifier_result != "PASS":
                hold_reasons.append("VERIFIER_NOT_PASS")

        timestamp = parse_timestamp(str(evidence["timestamp"]))
        age_days = (frozen_time - timestamp).total_seconds() / 86_400
        if age_days < 0:
            hold_reasons.append("EVIDENCE_FROM_FUTURE")
        elif age_days > float(policy["max_age_days"]):
            hold_reasons.append("EVIDENCE_STALE")

    for evidence in evidence_values:
        if evidence.get("type") != "CONTRADICTION":
            continue
        scope = evidence.get("scope", {})
        provenance = evidence.get("provenance", {})
        timestamp = parse_timestamp(str(evidence["timestamp"]))
        age_days = (frozen_time - timestamp).total_seconds() / 86_400
        if (
            scope.get("claim_id") == item["claim_context"]["claim_id"]
            and scope.get("statement_sha256") == item["claim_context"]["statement_sha256"]
            and scope.get("contradiction_status") == "OPEN"
            and provenance.get("actor_role") == "INDEPENDENT_REVIEWER"
            and provenance.get("actor_id") != item["claim_context"]["author_id"]
            and provenance.get("environment_sha256")
            != item["claim_context"]["author_environment_sha256"]
            and provenance.get("cold_start") is True
            and evidence.get("tool_exit") == 0
            and evidence.get("verifier_result") == "PASS"
            and 0 <= age_days <= float(policy["max_age_days"])
        ):
            escalate_reasons.append("UNRESOLVED_CONTRADICTION")

    target = item["requested_transition"]["target_state"]
    current = item["current_state"]
    new_computation = (
        target["computation_status"] == "COMPUTATIONAL"
        and current["computation_status"] != "COMPUTATIONAL"
    )
    new_formal = (
        target["formal_status"] == "FORMALLY_CERTIFIED"
        and current["formal_status"] != "FORMALLY_CERTIFIED"
    )
    any_research_transition = target["research_status"] != current["research_status"]
    new_review = (
        target["review_status"] == "INDEPENDENTLY_VERIFIED"
        and current["review_status"] != "INDEPENDENTLY_VERIFIED"
    )

    if new_computation:
        numeric = policy["numerical"]
        computations = [
            evidence_by_id[eid] for eid in closure if evidence_by_id[eid]["type"] == "COMPUTATION"
        ]
        if not computations:
            hold_reasons.append("COMPUTATION_EVIDENCE_REQUIRED")
        if not any(evidence_by_id.get(root, {}).get("type") == "COMPUTATION" for root in roots):
            hold_reasons.append("COMPUTATION_BASIS_TYPE_MISMATCH")
        for evidence in computations:
            scope = evidence["scope"]
            if (
                scope.get("protocol_id") != numeric["protocol_id"]
                or scope.get("protocol_version") != numeric["protocol_version"]
            ):
                hold_reasons.append("NUMERICAL_PROTOCOL_MISMATCH")
            if int(scope.get("repetitions", 0)) < int(numeric["min_repetitions"]):
                hold_reasons.append("INSUFFICIENT_REPETITIONS")
            if bool(numeric["requires_preregistration"]) and not scope.get("preregistered"):
                hold_reasons.append("PREREGISTRATION_REQUIRED")
            if int(scope.get("precision_bits", 0)) < int(numeric["min_precision_bits"]):
                hold_reasons.append("INSUFFICIENT_PRECISION")
            required_domain = item["claim_context"].get("required_domain")
            if required_domain is not None and not interval_covers(
                scope.get("domain", {}), required_domain
            ):
                hold_reasons.append("DOMAIN_NOT_COVERED")

    if new_formal:
        formal = policy["formal"]
        certificates = [
            evidence_by_id[eid]
            for eid in closure
            if evidence_by_id[eid]["type"] == "FORMAL_CERTIFICATE"
        ]
        if not certificates:
            hold_reasons.append("FORMAL_CERTIFICATE_REQUIRED")
        if not any(
            evidence_by_id.get(root, {}).get("type") == "FORMAL_CERTIFICATE" for root in roots
        ):
            hold_reasons.append("FORMAL_BASIS_TYPE_MISMATCH")
        for evidence in certificates:
            scope = evidence["scope"]
            if evidence["provenance"]["actor_role"] != "TOOL":
                hold_reasons.append("FORMAL_PROVENANCE_NOT_TOOL")
            if scope.get("verifier") != formal["verifier"]:
                hold_reasons.append("UNTRUSTED_FORMAL_VERIFIER")
            if scope.get("toolchain_lock_sha256") != formal["toolchain_lock_sha256"]:
                hold_reasons.append("UNTRUSTED_TOOLCHAIN")

    if any_research_transition:
        hold_reasons.append("RESEARCH_STATUS_TRANSITION_NOT_SUPPORTED_BY_ALPHA_POLICY")

    if new_review:
        reviews = [
            evidence_by_id[eid] for eid in closure if evidence_by_id[eid]["type"] == "REVIEW"
        ]
        if not reviews:
            hold_reasons.append("INDEPENDENT_REVIEW_REQUIRED")
        if not any(evidence_by_id.get(root, {}).get("type") == "REVIEW" for root in roots):
            hold_reasons.append("REVIEW_BASIS_TYPE_MISMATCH")
        for evidence in reviews:
            provenance = evidence["provenance"]
            if provenance["actor_role"] != "INDEPENDENT_REVIEWER":
                hold_reasons.append("REVIEWER_ROLE_NOT_INDEPENDENT")
            if provenance["actor_id"] == item["claim_context"]["author_id"]:
                hold_reasons.append("REVIEWER_NOT_INDEPENDENT")
            if (
                provenance["environment_sha256"]
                == item["claim_context"]["author_environment_sha256"]
            ):
                hold_reasons.append("REVIEW_ENVIRONMENT_NOT_INDEPENDENT")
            if not provenance.get("cold_start"):
                hold_reasons.append("REVIEW_NOT_COLD_START")

    invalid_basis_axes: set[str] = set()
    current_basis = item.get("current_state_basis", {})
    for axis, (elevated_value, expected_type) in CURRENT_AXIS_BASIS.items():
        if current[axis] != elevated_value:
            if axis in current_basis:
                raise DatasetIntegrityError(f"bottom current axis has an unexpected basis: {axis}")
            continue
        basis_record = current_basis.get(axis)
        if not isinstance(basis_record, dict):
            invalid_basis_axes.add(axis)
            continue
        basis_ids = [str(value) for value in basis_record.get("evidence_ids", [])]
        bound_hash = basis_record.get("bound_artifact_sha256")
        if not basis_ids or not isinstance(bound_hash, str):
            invalid_basis_axes.add(axis)
            continue
        basis_closure, basis_missing, basis_cycle = _closure(basis_ids, evidence_by_id)
        basis_invalid = bool(basis_missing or basis_cycle)
        for evidence_id in basis_closure:
            evidence = evidence_by_id[evidence_id]
            scope = evidence.get("scope", {})
            timestamp = parse_timestamp(str(evidence["timestamp"]))
            age_days = (frozen_time - timestamp).total_seconds() / 86_400
            if (
                evidence.get("tool_exit") != 0
                or evidence.get("verifier_result") != "PASS"
                or scope.get("claim_id") != item["claim_context"]["claim_id"]
                or scope.get("statement_sha256") != item["claim_context"]["statement_sha256"]
                or not 0 <= age_days <= float(policy["max_age_days"])
            ):
                basis_invalid = True
        for basis_id in basis_ids:
            evidence = evidence_by_id.get(basis_id)
            if (
                evidence is None
                or evidence.get("type") != expected_type
                or evidence.get("artifact_hash") != bound_hash
            ):
                basis_invalid = True
                continue
            scope = evidence["scope"]
            if axis == "computation_status":
                numeric = policy["numerical"]
                required_domain = item["claim_context"].get("required_domain")
                if (
                    scope.get("protocol_id") != numeric["protocol_id"]
                    or scope.get("protocol_version") != numeric["protocol_version"]
                    or int(scope.get("repetitions", 0)) < int(numeric["min_repetitions"])
                    or (
                        bool(numeric["requires_preregistration"]) and not scope.get("preregistered")
                    )
                    or int(scope.get("precision_bits", 0)) < int(numeric["min_precision_bits"])
                    or (
                        required_domain is not None
                        and not interval_covers(scope.get("domain", {}), required_domain)
                    )
                ):
                    basis_invalid = True
            elif axis == "formal_status":
                formal = policy["formal"]
                if (
                    evidence["provenance"]["actor_role"] != "TOOL"
                    or scope.get("verifier") != formal["verifier"]
                    or scope.get("toolchain_lock_sha256") != formal["toolchain_lock_sha256"]
                ):
                    basis_invalid = True
            elif axis == "review_status":
                provenance = evidence["provenance"]
                if (
                    provenance["actor_role"] != "INDEPENDENT_REVIEWER"
                    or provenance["actor_id"] == item["claim_context"]["author_id"]
                    or provenance["environment_sha256"]
                    == item["claim_context"]["author_environment_sha256"]
                    or not provenance.get("cold_start")
                ):
                    basis_invalid = True
        if basis_invalid:
            invalid_basis_axes.add(axis)
    if invalid_basis_axes:
        demote_reasons.append("CURRENT_STATE_BASIS_INVALID")

    hold_reasons = _ordered_unique(hold_reasons)
    escalate_reasons = _ordered_unique(escalate_reasons)
    demote_reasons = _ordered_unique(demote_reasons)
    if demote_reasons:
        action = "DEMOTE"
        reasons = demote_reasons + escalate_reasons + hold_reasons
        proposed_state = _demoted_state(item, invalid_basis_axes)
        probability = 0.0
    elif escalate_reasons:
        action = "ESCALATE"
        reasons = escalate_reasons + hold_reasons
        proposed_state = deepcopy(current)
        probability = 0.0
    elif hold_reasons:
        action = "HOLD"
        reasons = hold_reasons
        proposed_state = deepcopy(current)
        probability = 0.0
    else:
        action = "ALLOW"
        reasons = ["POLICY_SATISFIED"]
        proposed_state = deepcopy(target)
        probability = 1.0

    return {
        "action": action,
        "proposed_state": proposed_state,
        "p_admissible": probability,
        "used_evidence_ids": closure,
        "reason_codes": reasons,
        "missing_evidence_ids": missing,
        "minimal_missing_evidence": sorted(set(minimal_missing)),
    }
