from __future__ import annotations

from copy import deepcopy

from claimpromotebench.oracle import evaluate


def by_fragment(inputs, fragment: str):
    return next(item for item in inputs if fragment in str(item["id"]))


def test_oracle_matches_all_gold(inputs, gold, policy, manifest) -> None:
    gold_by_id = {record["id"]: record["decision"] for record in gold}
    for item in inputs:
        assert evaluate(item, policy, manifest["evaluation_time"]) == gold_by_id[item["id"]]


def test_evidence_order_does_not_change_oracle(inputs, policy, manifest) -> None:
    item = deepcopy(next(item for item in inputs if len(item["evidence"]) > 1))
    original = evaluate(item, policy, manifest["evaluation_time"])
    item["evidence"] = list(reversed(item["evidence"]))
    assert evaluate(item, policy, manifest["evaluation_time"]) == original


def test_transitive_dependency_is_checked(inputs, policy, manifest) -> None:
    item = deepcopy(by_fragment(inputs, "dep-02"))
    dependency_ids = {
        dependency
        for evidence in item["evidence"]
        for dependency in evidence.get("dependencies", [])
    }
    known_ids = {evidence["id"] for evidence in item["evidence"]}
    if dependency_ids <= known_ids:
        leaf = next(
            evidence
            for evidence in item["evidence"]
            if evidence["id"] in dependency_ids
            and evidence["id"] not in item["requested_transition"]["basis_evidence_ids"]
        )
        item["evidence"].remove(leaf)
    result = evaluate(item, policy, manifest["evaluation_time"])
    assert result["action"] == "HOLD"
    assert "MISSING_DEPENDENCY" in result["reason_codes"]


def test_numeric_boundaries(inputs, policy, manifest) -> None:
    valid = deepcopy(
        next(item for item in inputs if "num-01" in item["id"] and item["id"].endswith("a"))
    )
    if evaluate(valid, policy, manifest["evaluation_time"])["action"] != "ALLOW":
        valid = deepcopy(
            next(item for item in inputs if "num-01" in item["id"] and item["id"].endswith("b"))
        )
    computation = next(e for e in valid["evidence"] if e["type"] == "COMPUTATION")
    computation["scope"]["repetitions"] = 3
    computation["scope"]["precision_bits"] = 53
    assert evaluate(valid, policy, manifest["evaluation_time"])["action"] == "ALLOW"
    computation["scope"]["repetitions"] = 2
    assert (
        "INSUFFICIENT_REPETITIONS"
        in evaluate(valid, policy, manifest["evaluation_time"])["reason_codes"]
    )


def test_formal_certificate_cannot_resolve_research_claim(inputs, policy, manifest) -> None:
    valid = next(
        item
        for item in inputs
        if "formal-01" in item["id"]
        and evaluate(item, policy, manifest["evaluation_time"])["action"] == "ALLOW"
    )
    item = deepcopy(valid)
    item["requested_transition"]["target_state"]["research_status"] = "RESOLVED"
    result = evaluate(item, policy, manifest["evaluation_time"])
    assert result["action"] == "HOLD"
    assert "RESEARCH_STATUS_TRANSITION_NOT_SUPPORTED_BY_ALPHA_POLICY" in result["reason_codes"]


def test_dependency_must_finish_and_pass(inputs, policy, manifest) -> None:
    valid = next(
        item
        for item in inputs
        if "dep-03" in item["id"]
        and evaluate(item, policy, manifest["evaluation_time"])["action"] == "ALLOW"
    )
    item = deepcopy(valid)
    dependency = next(
        evidence
        for evidence in item["evidence"]
        if evidence["id"] not in item["requested_transition"]["basis_evidence_ids"]
    )
    dependency["tool_exit"] = None
    dependency["verifier_result"] = "UNKNOWN"
    result = evaluate(item, policy, manifest["evaluation_time"])
    assert result["action"] == "HOLD"
    assert "DEPENDENCY_RUNTIME_FAILURE" in result["reason_codes"]
    assert "DEPENDENCY_NOT_VERIFIED" in result["reason_codes"]


def test_review_role_must_be_independent(inputs, policy, manifest) -> None:
    valid = next(
        item
        for item in inputs
        if "prov-01" in item["id"]
        and evaluate(item, policy, manifest["evaluation_time"])["action"] == "ALLOW"
    )
    item = deepcopy(valid)
    review = next(evidence for evidence in item["evidence"] if evidence["type"] == "REVIEW")
    review["provenance"]["actor_role"] = "CLAIM_AUTHOR"
    result = evaluate(item, policy, manifest["evaluation_time"])
    assert result["action"] == "HOLD"
    assert "REVIEWER_ROLE_NOT_INDEPENDENT" in result["reason_codes"]


def test_transition_root_type_cannot_be_spoofed(inputs, policy, manifest) -> None:
    valid = next(
        item
        for item in inputs
        if "formal-03" in item["id"]
        and evaluate(item, policy, manifest["evaluation_time"])["action"] == "ALLOW"
    )
    item = deepcopy(valid)
    certificate_id = item["requested_transition"]["basis_evidence_ids"][0]
    artifact = deepcopy(next(e for e in item["evidence"] if e["id"] == certificate_id))
    artifact["id"] = "generic-root"
    artifact["type"] = "ARTIFACT"
    artifact["dependencies"] = [certificate_id]
    item["evidence"].append(artifact)
    item["requested_transition"]["basis_evidence_ids"] = ["generic-root"]
    result = evaluate(item, policy, manifest["evaluation_time"])
    assert result["action"] == "HOLD"
    assert "FORMAL_BASIS_TYPE_MISMATCH" in result["reason_codes"]


def test_formal_scope_and_provenance_fail_closed(inputs, policy, manifest) -> None:
    valid = next(
        item
        for item in inputs
        if "formal-03" in item["id"]
        and evaluate(item, policy, manifest["evaluation_time"])["action"] == "ALLOW"
    )
    item = deepcopy(valid)
    certificate = next(e for e in item["evidence"] if e["type"] == "FORMAL_CERTIFICATE")
    certificate["scope"].pop("statement_sha256")
    certificate["provenance"]["actor_role"] = "CLAIM_AUTHOR"
    result = evaluate(item, policy, manifest["evaluation_time"])
    assert result["action"] == "HOLD"
    assert "STATEMENT_HASH_MISMATCH" in result["reason_codes"]
    assert "FORMAL_PROVENANCE_NOT_TOOL" in result["reason_codes"]


def test_elevated_current_axis_requires_typed_bound_basis(inputs, policy, manifest) -> None:
    valid = next(
        item
        for item in inputs
        if "stale-02" in item["id"]
        and evaluate(item, policy, manifest["evaluation_time"])["action"] == "ALLOW"
    )
    missing = deepcopy(valid)
    missing["current_state_basis"] = {}
    missing_result = evaluate(missing, policy, manifest["evaluation_time"])
    assert missing_result["action"] == "DEMOTE"
    spoofed = deepcopy(valid)
    basis_id = spoofed["current_state_basis"]["computation_status"][0]
    next(e for e in spoofed["evidence"] if e["id"] == basis_id)["type"] = "REVIEW"
    spoofed_result = evaluate(spoofed, policy, manifest["evaluation_time"])
    assert spoofed_result["action"] == "DEMOTE"


def test_only_authoritative_contradiction_escalates(inputs, policy, manifest) -> None:
    invalid = next(
        item
        for item in inputs
        if "stale-03" in item["id"]
        and evaluate(item, policy, manifest["evaluation_time"])["action"] == "ESCALATE"
    )
    item = deepcopy(invalid)
    contradiction = next(e for e in item["evidence"] if e["type"] == "CONTRADICTION")
    contradiction["provenance"]["actor_role"] = "CLAIM_AUTHOR"
    result = evaluate(item, policy, manifest["evaluation_time"])
    assert result["action"] == "ALLOW"
    assert "UNRESOLVED_CONTRADICTION" not in result["reason_codes"]
