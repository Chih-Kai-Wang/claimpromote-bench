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
    assert "RESOLUTION_NOT_SUPPORTED_BY_ALPHA_POLICY" in result["reason_codes"]
