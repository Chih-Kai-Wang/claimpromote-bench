"""Pure deterministic oracle driven by a complete versioned policy contract."""

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


def _ordered_reasons(values: Iterable[str], policy: dict[str, Any]) -> list[str]:
    unique = _ordered_unique(values)
    precedence = {str(reason): index for index, reason in enumerate(policy["reason_precedence"])}
    unknown = sorted(set(unique) - set(precedence))
    if unknown:
        raise DatasetIntegrityError(f"oracle emitted reasons absent from policy: {unknown}")
    return sorted(unique, key=precedence.__getitem__)


def _path_value(value: dict[str, Any], path: list[Any]) -> Any:
    current: Any = value
    for part in path:
        if not isinstance(current, dict) or str(part) not in current:
            raise DatasetIntegrityError(f"policy path does not resolve in item: {path}")
        current = current[str(part)]
    return current


def _closure(
    roots: list[str], evidence_by_id: dict[str, dict[str, Any]], rules: dict[str, Any]
) -> tuple[list[str], list[str], bool]:
    visited: set[str] = set()
    visiting: set[str] = set()
    missing: list[str] = []
    ordered: list[str] = []
    cycle = False
    dependency_field = str(rules["dependency_ids_field"])

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
        dependencies = [str(value) for value in evidence.get(dependency_field, [])]
        if rules["ordering"] == "LEXICOGRAPHIC":
            dependencies.sort()
        for dependency in dependencies:
            visit(dependency)
        visiting.remove(evidence_id)
        visited.add(evidence_id)
        ordered.append(evidence_id)

    ordered_roots = sorted(roots) if rules["ordering"] == "LEXICOGRAPHIC" else roots
    for root in ordered_roots:
        visit(root)
    return ordered, sorted(set(missing)), cycle


def _demoted_state(
    item: dict[str, Any], invalid_axes: set[str], policy: dict[str, Any]
) -> dict[str, Any]:
    state = deepcopy(item["current_state"])
    axes = policy["transition_axes"]
    for axis in invalid_axes:
        state[axis] = axes[axis]["bottom_value"]
    return dict(state)


def _independence_satisfied(
    provenance: dict[str, Any], context: dict[str, Any], rules: dict[str, Any]
) -> bool:
    return (
        provenance.get("actor_role") == rules["required_actor_role"]
        and (
            not rules["actor_must_differ_from_author"]
            or provenance.get("actor_id") != context["author_id"]
        )
        and (
            not rules["environment_must_differ_from_author"]
            or provenance.get("environment_sha256") != context["author_environment_sha256"]
        )
        and (not rules["cold_start_required"] or provenance.get("cold_start") is True)
    )


def evaluate(
    item: dict[str, Any], policy: dict[str, Any], evaluation_time: str | datetime
) -> dict[str, Any]:
    """Evaluate one input using only rules declared in the loaded policy."""

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
    research_scope = policy["alpha_scope"]["research_status"]
    if (
        current.get("research_status") not in research_scope["allowed_current_values"]
        or target.get("research_status") not in research_scope["allowed_target_values"]
    ):
        raise DatasetIntegrityError(
            f"{research_scope['unsupported_transition_reason']}: alpha inputs must keep "
            "research_status within the policy-declared scope"
        )
    if not state_leq(current, target) or not changed_axes(current, target):
        raise DatasetIntegrityError("requested transition must strictly promote at least one axis")

    evidence_values = item.get("evidence", [])
    evidence_ids = [str(evidence["id"]) for evidence in evidence_values]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise DatasetIntegrityError("evidence IDs must be unique")
    evidence_by_id = {str(evidence["id"]): evidence for evidence in evidence_values}
    dependency_rules = policy["dependency_closure"]
    roots_value = _path_value(item, list(dependency_rules["basis_root_path"]))
    if not isinstance(roots_value, list):
        raise DatasetIntegrityError("policy-declared transition roots must be an array")
    roots = [str(value) for value in roots_value]
    closure, missing, cycle = _closure(roots, evidence_by_id, dependency_rules)

    hold_reasons: list[str] = []
    escalate_reasons: list[str] = []
    demote_reasons: list[str] = []
    minimal_missing: list[str] = []
    validity = policy["evidence_validity"]
    max_age_days = float(validity["max_age_days"])
    context = item["claim_context"]

    if missing:
        hold_reasons.append(str(dependency_rules["missing_reason"]))
        minimal_missing.extend(missing)
    if cycle:
        hold_reasons.append(str(dependency_rules["cycle_reason"]))

    root_set = set(roots)
    for evidence_id in closure:
        evidence = evidence_by_id[evidence_id]
        is_dependency = evidence_id not in root_set
        tool_exit = evidence.get("tool_exit")
        verifier_result = evidence.get("verifier_result")
        if is_dependency and tool_exit != dependency_rules["required_tool_exit"]:
            hold_reasons.append(str(dependency_rules["runtime_reason"]))
        if is_dependency and verifier_result != dependency_rules["required_verifier_result"]:
            hold_reasons.append(str(dependency_rules["verification_reason"]))

        scope = evidence.get("scope", {})
        if scope.get(validity["claim_id_scope_field"]) != context["claim_id"]:
            hold_reasons.append(str(validity["claim_id_mismatch_reason"]))
        if scope.get(validity["statement_hash_scope_field"]) != context["statement_sha256"]:
            hold_reasons.append(str(validity["statement_hash_mismatch_reason"]))

        if evidence_id in root_set:
            runtime = validity["root_runtime"]
            if tool_exit is None:
                hold_reasons.append(str(runtime["missing_tool_exit_reason"]))
            elif tool_exit != runtime["required_tool_exit"]:
                hold_reasons.append(str(runtime["tool_exit_mismatch_reason"]))
            if verifier_result != runtime["required_verifier_result"]:
                hold_reasons.append(str(runtime["verifier_mismatch_reason"]))

        timestamp = parse_timestamp(str(evidence["timestamp"]))
        age_days = (frozen_time - timestamp).total_seconds() / 86_400
        if age_days < 0:
            hold_reasons.append(str(validity["future_reason"]))
        elif age_days > max_age_days:
            hold_reasons.append(str(validity["stale_reason"]))

    contradiction = policy["contradiction_authority"]
    for evidence in evidence_values:
        if evidence.get("type") != contradiction["evidence_type"]:
            continue
        scope = evidence.get("scope", {})
        provenance = evidence.get("provenance", {})
        timestamp = parse_timestamp(str(evidence["timestamp"]))
        age_days = (frozen_time - timestamp).total_seconds() / 86_400
        identity_ok = not contradiction["require_claim_identity"] or (
            scope.get(validity["claim_id_scope_field"]) == context["claim_id"]
            and scope.get(validity["statement_hash_scope_field"]) == context["statement_sha256"]
        )
        fresh_ok = not contradiction["require_fresh"] or 0 <= age_days <= max_age_days
        if (
            scope.get(contradiction["status_scope_field"]) == contradiction["open_status_value"]
            and identity_ok
            and fresh_ok
            and evidence.get("tool_exit") == contradiction["required_tool_exit"]
            and evidence.get("verifier_result") == contradiction["required_verifier_result"]
            and _independence_satisfied(provenance, context, contradiction)
        ):
            escalate_reasons.append(str(contradiction["escalation_reason"]))

    axes = policy["transition_axes"]
    newly_elevated = {
        axis: target[axis] == rules["elevated_value"] and current[axis] != rules["elevated_value"]
        for axis, rules in axes.items()
    }

    computation_axis = axes["computation_status"]
    if newly_elevated["computation_status"]:
        evidence_type = computation_axis["root_evidence_type"]
        computations = [
            evidence_by_id[eid] for eid in closure if evidence_by_id[eid]["type"] == evidence_type
        ]
        if not computations:
            hold_reasons.append(str(computation_axis["evidence_required_reason"]))
        if not any(evidence_by_id.get(root, {}).get("type") == evidence_type for root in roots):
            hold_reasons.append(str(computation_axis["root_type_mismatch_reason"]))
        numeric = policy["numerical"]
        for evidence in computations:
            scope = evidence["scope"]
            if (
                scope.get("protocol_id") != numeric["protocol_id"]
                or scope.get("protocol_version") != numeric["protocol_version"]
            ):
                hold_reasons.append(str(numeric["protocol_reason"]))
            if int(scope.get("repetitions", 0)) < int(numeric["min_repetitions"]):
                hold_reasons.append(str(numeric["repetitions_reason"]))
            if bool(numeric["requires_preregistration"]) and not scope.get("preregistered"):
                hold_reasons.append(str(numeric["preregistration_reason"]))
            if int(scope.get("precision_bits", 0)) < int(numeric["min_precision_bits"]):
                hold_reasons.append(str(numeric["precision_reason"]))
            required_domain = context.get("required_domain")
            if required_domain is not None and not interval_covers(
                scope.get("domain", {}), required_domain
            ):
                hold_reasons.append(str(numeric["domain_reason"]))

    formal_axis = axes["formal_status"]
    if newly_elevated["formal_status"]:
        evidence_type = formal_axis["root_evidence_type"]
        certificates = [
            evidence_by_id[eid] for eid in closure if evidence_by_id[eid]["type"] == evidence_type
        ]
        if not certificates:
            hold_reasons.append(str(formal_axis["evidence_required_reason"]))
        if not any(evidence_by_id.get(root, {}).get("type") == evidence_type for root in roots):
            hold_reasons.append(str(formal_axis["root_type_mismatch_reason"]))
        formal = policy["formal"]
        for evidence in certificates:
            scope = evidence["scope"]
            if evidence["provenance"]["actor_role"] != formal["required_actor_role"]:
                hold_reasons.append(str(formal["provenance_reason"]))
            if scope.get("verifier") != formal["verifier"]:
                hold_reasons.append(str(formal["verifier_reason"]))
            if scope.get("toolchain_lock_sha256") != formal["toolchain_lock_sha256"]:
                hold_reasons.append(str(formal["toolchain_reason"]))

    review_axis = axes["review_status"]
    if newly_elevated["review_status"]:
        evidence_type = review_axis["root_evidence_type"]
        reviews = [
            evidence_by_id[eid] for eid in closure if evidence_by_id[eid]["type"] == evidence_type
        ]
        if not reviews:
            hold_reasons.append(str(review_axis["evidence_required_reason"]))
        if not any(evidence_by_id.get(root, {}).get("type") == evidence_type for root in roots):
            hold_reasons.append(str(review_axis["root_type_mismatch_reason"]))
        independence = policy["review_independence"]
        for evidence in reviews:
            provenance = evidence["provenance"]
            if provenance["actor_role"] != independence["required_actor_role"]:
                hold_reasons.append(str(independence["role_reason"]))
            if (
                independence["actor_must_differ_from_author"]
                and provenance["actor_id"] == context["author_id"]
            ):
                hold_reasons.append(str(independence["actor_reason"]))
            if (
                independence["environment_must_differ_from_author"]
                and provenance["environment_sha256"] == context["author_environment_sha256"]
            ):
                hold_reasons.append(str(independence["environment_reason"]))
            if independence["cold_start_required"] and not provenance.get("cold_start"):
                hold_reasons.append(str(independence["cold_start_reason"]))

    invalid_basis_axes: set[str] = set()
    current_basis = item.get("current_state_basis", {})
    basis_rules = policy["current_state_basis"]
    for axis, axis_rules in axes.items():
        if current[axis] != axis_rules["elevated_value"]:
            if axis in current_basis:
                raise DatasetIntegrityError(f"bottom current axis has an unexpected basis: {axis}")
            continue
        basis_record = current_basis.get(axis)
        if not isinstance(basis_record, dict):
            invalid_basis_axes.add(axis)
            continue
        basis_ids = [str(value) for value in basis_record.get(basis_rules["basis_ids_field"], [])]
        bound_hash = basis_record.get(basis_rules["bound_artifact_hash_field"])
        if not basis_ids or not isinstance(bound_hash, str):
            invalid_basis_axes.add(axis)
            continue
        basis_closure, basis_missing, basis_cycle = _closure(
            basis_ids, evidence_by_id, dependency_rules
        )
        basis_invalid = bool(basis_missing or basis_cycle)
        for evidence_id in basis_closure:
            evidence = evidence_by_id[evidence_id]
            scope = evidence.get("scope", {})
            timestamp = parse_timestamp(str(evidence["timestamp"]))
            age_days = (frozen_time - timestamp).total_seconds() / 86_400
            if (
                evidence.get("tool_exit") != validity["root_runtime"]["required_tool_exit"]
                or evidence.get("verifier_result")
                != validity["root_runtime"]["required_verifier_result"]
                or scope.get(validity["claim_id_scope_field"]) != context["claim_id"]
                or scope.get(validity["statement_hash_scope_field"]) != context["statement_sha256"]
                or not 0 <= age_days <= max_age_days
            ):
                basis_invalid = True
        for basis_id in basis_ids:
            evidence = evidence_by_id.get(basis_id)
            if (
                evidence is None
                or evidence.get("type") != axis_rules["root_evidence_type"]
                or evidence.get(basis_rules["evidence_artifact_hash_field"]) != bound_hash
            ):
                basis_invalid = True
                continue
            scope = evidence["scope"]
            if axis == "computation_status":
                numeric = policy["numerical"]
                required_domain = context.get("required_domain")
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
                    evidence["provenance"]["actor_role"] != formal["required_actor_role"]
                    or scope.get("verifier") != formal["verifier"]
                    or scope.get("toolchain_lock_sha256") != formal["toolchain_lock_sha256"]
                ):
                    basis_invalid = True
            elif axis == "review_status" and not _independence_satisfied(
                evidence["provenance"], context, policy["review_independence"]
            ):
                basis_invalid = True
        if basis_invalid:
            invalid_basis_axes.add(axis)
    if invalid_basis_axes:
        demote_reasons.append(str(basis_rules["invalid_reason"]))

    buckets = {
        "DEMOTE": _ordered_unique(demote_reasons),
        "ESCALATE": _ordered_unique(escalate_reasons),
        "HOLD": _ordered_unique(hold_reasons),
    }
    action_rules = policy["action_policy"]
    precedence = [str(value) for value in action_rules["precedence"]]
    action = "ALLOW"
    for candidate in precedence:
        if candidate != "ALLOW" and buckets[candidate]:
            action = candidate
            break
    if action == "ALLOW":
        reasons = [str(action_rules["allow_reason"])]
    else:
        selected = precedence.index(action)
        reasons = _ordered_reasons(
            (
                reason
                for candidate in precedence[selected:]
                if candidate != "ALLOW"
                for reason in buckets[candidate]
            ),
            policy,
        )

    outcome = action_rules["outcomes"][action]
    state_source = outcome["proposed_state_source"]
    if state_source == "DEMOTED_CURRENT":
        proposed_state = _demoted_state(item, invalid_basis_axes, policy)
    elif state_source == "CURRENT":
        proposed_state = deepcopy(current)
    elif state_source == "TARGET":
        proposed_state = deepcopy(target)
    else:
        raise DatasetIntegrityError(f"unknown proposed_state_source: {state_source}")

    return {
        "action": action,
        "proposed_state": proposed_state,
        "p_admissible": float(outcome["p_admissible"]),
        "used_evidence_ids": closure,
        "reason_codes": reasons,
        "missing_evidence_ids": missing,
        "minimal_missing_evidence": sorted(set(minimal_missing)),
    }
