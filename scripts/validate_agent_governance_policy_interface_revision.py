#!/usr/bin/env python3
"""Validate the frozen agent-governance policy-interface fault evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file

ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = ROOT / "v2" / "agent-governance-policy-interface-revision-v1"
ACCOUNT_MARKERS = ("f0909172434", "wangzhikai", "Chih-Kai")
Json = dict[str, Any]


def fail(message: str) -> None:
    raise ValueError(f"agent-governance-policy-interface-validation: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def validate(root: Path = STUDY_ROOT) -> Json:
    registry = load_object(root / "sources" / "registry.json")
    for path_key, digest_key in (
        ("old_source", "old_sha256"),
        ("new_source", "new_sha256"),
        ("test_source", "test_sha256"),
        ("license_path", "license_sha256"),
    ):
        path = ROOT / str(registry[path_key])
        if not path.is_file() or sha256_file(path) != registry[digest_key]:
            fail(f"source digest differs: {path_key}")
    if registry.get("license") != "MIT":
        fail("upstream license boundary differs")
    if not str(registry["change_url"]).endswith(str(registry["change_commit"])):
        fail("change URL differs from the fixed commit")

    manifest = load_object(root / "artifact-manifest.json")
    files = manifest.get("files")
    if not isinstance(files, dict) or len(files) != 4:
        fail("manifest must bind four generated artifacts")
    for relative, expected in files.items():
        path = root / str(relative)
        if not path.is_file() or sha256_file(path) != expected:
            fail(f"generated artifact digest differs: {relative}")
    payload = {key: value for key, value in manifest.items() if key != "self_digest"}
    if manifest.get("self_digest") != sha256_bytes(canonical_json(payload).encode()):
        fail("manifest self digest differs")

    cases = load_object(root / "cases.json")
    case_rows = cases.get("cases")
    if (
        not isinstance(case_rows, list)
        or len(case_rows) != 2
        or cases.get("model_calls") != 0
        or cases.get("human_annotators") != 0
    ):
        fail("case boundary differs")
    if {row.get("upstream_test_name") for row in case_rows if isinstance(row, dict)} != set(
        registry["decision_regression_test_names"]
    ):
        fail("decision-test bindings differ")

    results = load_object(root / "results.json")
    result_rows = results.get("results")
    if not isinstance(result_rows, list) or len(result_rows) != 2:
        fail("result rows differ")
    for row in result_rows:
        if not isinstance(row, dict) or (
            row.get("old_matches_any"),
            row.get("old_deny_decision"),
            row.get("old_action"),
            row.get("new_matches_any"),
            row.get("new_deny_decision"),
            row.get("new_action"),
        ) != (True, None, "ALLOW", True, "deny", "HOLD"):
            fail("historical verdict behavior differs")
    old_tests = results.get("old_upstream_tests")
    new_tests = results.get("new_upstream_tests")
    if not isinstance(old_tests, dict) or (old_tests.get("passed"), old_tests.get("total")) != (
        11,
        15,
    ):
        fail("old-source upstream test counts differ")
    if not isinstance(new_tests, dict) or (new_tests.get("passed"), new_tests.get("total")) != (
        15,
        15,
    ):
        fail("new-source upstream test counts differ")
    if set(old_tests.get("failed", [])) != set(registry["all_new_regression_test_names"]):
        fail("old-source failure names differ")

    minimum = load_object(root / "minimum-suite.json")
    if (
        minimum.get("witness_cases") != 1
        or len(minimum.get("selected_case_ids", [])) != 1
        or minimum.get("coverage", {}).get("action_edges") != {"covered": 1, "total": 1}
    ):
        fail("minimum-suite certificate differs")
    receipt = load_object(root / "source-validation-receipt.json")
    if (
        receipt.get("status") != "HISTORICAL_AGENT_GOVERNANCE_POLICY_INTERFACE_FAULT_REPRODUCED"
        or receipt.get("model_calls") != 0
        or receipt.get("credentials_retained") is not False
        or receipt.get("source_bytes_match_registry") is not True
        or receipt.get("action_mapping_is_author_mapping") is not True
    ):
        fail("source-validation receipt differs")

    for path in (
        root / "cases.json",
        root / "results.json",
        root / "minimum-suite.json",
        root / "source-validation-receipt.json",
    ):
        text = path.read_text(encoding="utf-8").lower()
        for marker in ACCOUNT_MARKERS:
            if marker.lower() in text:
                fail(f"account marker in release-facing artifact: {path}: {marker}")
    return {
        "cases": len(case_rows),
        "minimum_cases": int(minimum["witness_cases"]),
        "new_tests_passed": int(new_tests["passed"]),
        "old_tests_failed": len(old_tests["failed"]),
        "repositories": 1,
    }


def main() -> int:
    report = validate()
    print(
        "agent-governance-policy-interface-validation: "
        f"cases={report['cases']} old_fail={report['old_tests_failed']} "
        f"new_pass={report['new_tests_passed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
