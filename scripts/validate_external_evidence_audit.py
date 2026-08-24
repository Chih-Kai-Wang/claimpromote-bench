#!/usr/bin/env python3
"""Validate the frozen zero-call external-evidence discovery audit."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from claimpromotebench.hashing import sha256_file

ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "v2" / "external-evidence-audit-v1"
AGT_ROOT = ROOT / "v2" / "agent-governance-policy-interface-revision-v1"
ACCOUNT_MARKERS = ("f0909172434", "wangzhikai", "Chih-Kai")
Json = dict[str, Any]


def fail(message: str) -> None:
    raise ValueError(f"external-evidence-audit-validation: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def validate(root: Path = AUDIT_ROOT) -> Json:
    plan = load_object(root / "study-plan.json")
    if plan.get("status") != "FROZEN_BEFORE_FORMAL_SEARCH" or plan.get("model_calls") != 0:
        fail("study plan was not frozen as a zero-call audit")
    seeds = load_object(root / "formal-search-seeds.json")
    if (
        seeds.get("repository_seed_count") != 465
        or seeds.get("code_seed_count") != 10
        or seeds.get("model_calls") != 0
        or seeds.get("private_results_retained") is not False
    ):
        fail("formal seed boundary differs")
    repository_rows = seeds.get("repository_seeds")
    code_rows = seeds.get("code_seeds")
    if not isinstance(repository_rows, list) or len(repository_rows) != 465:
        fail("repository seed rows differ")
    if not isinstance(code_rows, list) or len(code_rows) != 10:
        fail("code seed rows differ")
    if len({row.get("repository") for row in repository_rows if isinstance(row, dict)}) != 465:
        fail("repository seed keys are not unique")
    repository_statuses = Counter(
        str(row.get("screening_status")) for row in repository_rows if isinstance(row, dict)
    )
    if repository_statuses != Counter(
        {
            "ADVANCED_TO_SOURCE_LEVEL_REVIEW": 11,
            "NOT_ADVANCED_AFTER_METADATA_SCREEN": 454,
        }
    ):
        fail(f"repository screening counts differ: {dict(repository_statuses)}")
    if any(row.get("screening_reason") in (None, "") for row in repository_rows):
        fail("every repository seed must retain a screening reason")
    if any(row.get("screening_reason") in (None, "") for row in code_rows):
        fail("every code seed must retain a screening reason")

    registry = load_object(root / "candidate-registry.json")
    candidates = registry.get("deep_screened_candidates")
    if not isinstance(candidates, list) or len(candidates) != 11:
        fail("source-level candidate count differs")
    outcomes = Counter(str(row.get("outcome")) for row in candidates if isinstance(row, dict))
    expected_outcomes = Counter(
        {"QUALIFYING_ROUTE_REVISION": 2, "ARCHITECTURE_ONLY": 6, "EXCLUDED": 3}
    )
    if outcomes != expected_outcomes:
        fail(f"candidate outcomes differ: {dict(outcomes)}")
    qualified = [row for row in candidates if row.get("outcome") == "QUALIFYING_ROUTE_REVISION"]
    if {row.get("repository") for row in qualified} != {
        "agentgateway/agentgateway",
        "microsoft/agent-governance-toolkit",
    }:
        fail("qualifying repositories differ")
    for row in qualified:
        criteria = row.get("criteria")
        if not isinstance(criteria, dict) or set(criteria) != {f"I{i}" for i in range(1, 8)}:
            fail("qualifying criteria are incomplete")
        if any(value is not True for value in criteria.values()):
            fail("qualifying candidate has an unsatisfied criterion")

    agentgateway = load_object(root / "source-checks" / "agentgateway-bedrock-guardrail.json")
    if (
        agentgateway.get("status") != "EXACT_CHANGE_COMMIT_OFFLINE_REGRESSION_TESTS_PASS"
        or agentgateway.get("model_calls") != 0
        or agentgateway.get("aws_calls") != 0
        or agentgateway.get("test_run", {}).get("passed") != 33
        or agentgateway.get("test_run", {}).get("failed") != 0
    ):
        fail("agentgateway source check differs")
    microsoft = load_object(AGT_ROOT / "source-validation-receipt.json")
    if (
        microsoft.get("status") != "HISTORICAL_AGENT_GOVERNANCE_POLICY_INTERFACE_FAULT_REPRODUCED"
        or microsoft.get("model_calls") != 0
        or microsoft.get("upstream_test_results", {}).get("old", {}).get("passed") != 11
        or microsoft.get("upstream_test_results", {}).get("new", {}).get("passed") != 15
    ):
        fail("Microsoft source check differs")

    receipt = load_object(root / "audit-receipt.json")
    expected_status = (
        "GO_FOR_EXTERNAL_BOUNDARY_FAULT_EVIDENCE__NO_GO_FOR_NATURALISTIC_"
        "MODEL_POLICY_INTERPRETATION"
    )
    if (
        receipt.get("status") != expected_status
        or receipt.get("model_calls") != 0
        or receipt.get("naturalistic_model_policy_interpretation_cases") != 0
        or receipt.get("outcome_counts") != registry.get("outcome_counts")
    ):
        fail("audit conclusion differs")
    digest_paths = {
        "study_plan": root / "study-plan.json",
        "formal_search_seeds": root / "formal-search-seeds.json",
        "candidate_registry": root / "candidate-registry.json",
        "agentgateway_source_check": root / "source-checks" / "agentgateway-bedrock-guardrail.json",
        "microsoft_source_receipt": AGT_ROOT / "source-validation-receipt.json",
    }
    for key, path in digest_paths.items():
        if receipt.get("sha256", {}).get(key) != sha256_file(path):
            fail(f"receipt digest differs: {key}")

    for path in (
        root / "formal-search-seeds.json",
        root / "candidate-registry.json",
        root / "source-checks" / "agentgateway-bedrock-guardrail.json",
        root / "audit-receipt.json",
    ):
        text = path.read_text(encoding="utf-8").lower()
        for marker in ACCOUNT_MARKERS:
            if marker.lower() in text:
                fail(f"account marker in evidence artifact: {path}: {marker}")
    return {
        "architecture_only": outcomes["ARCHITECTURE_ONLY"],
        "code_seeds": len(code_rows),
        "model_calls": int(receipt["model_calls"]),
        "qualifying_revisions": outcomes["QUALIFYING_ROUTE_REVISION"],
        "repository_seeds": len(repository_rows),
        "source_level_reviewed": len(candidates),
    }


def main() -> int:
    report = validate()
    print(
        "external-evidence-audit-validation: "
        f"seeds={report['repository_seeds']} reviewed={report['source_level_reviewed']} "
        f"qualifying={report['qualifying_revisions']} model_calls={report['model_calls']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
