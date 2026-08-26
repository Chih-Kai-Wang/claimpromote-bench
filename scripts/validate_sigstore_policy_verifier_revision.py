#!/usr/bin/env python3
"""Validate the deterministic Sigstore policy-verifier fault addendum offline."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file

ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = ROOT / "v2" / "sigstore-policy-verifier-revision-v1"
ACCOUNT_MARKERS = ("f0909172434", "wangzhikai", "Chih-Kai")
Json = dict[str, Any]


def fail(message: str) -> None:
    raise ValueError(f"sigstore-policy-verifier-validation: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def validate(root: Path = STUDY_ROOT) -> Json:
    registry = load_object(root / "sources" / "registry.json")
    for revision in ("old", "new"):
        path = ROOT / str(registry[f"{revision}_source"])
        if not path.is_file() or sha256_file(path) != registry[f"{revision}_sha256"]:
            fail(f"{revision} source digest differs")
    test_path = ROOT / str(registry["test_source"])
    if not test_path.is_file() or sha256_file(test_path) != registry["test_sha256"]:
        fail("upstream regression-test source digest differs")
    if len(str(registry["old_commit"])) != 40 or len(str(registry["change_commit"])) != 40:
        fail("registry commits must be full hashes")
    if not str(registry["change_url"]).endswith(str(registry["change_commit"])):
        fail("registry change URL differs from the commit")

    manifest = load_object(root / "artifact-manifest.json")
    files = manifest.get("files")
    if not isinstance(files, dict) or len(files) != 4:
        fail("manifest must bind four generated artifacts")
    for relative, expected in files.items():
        path = root / str(relative)
        if not path.is_file() or sha256_file(path) != expected:
            fail(f"generated artifact digest differs: {relative}")
    payload = {key: value for key, value in manifest.items() if key != "self_digest"}
    if manifest.get("self_digest") != sha256_bytes(canonical_json(payload).encode("utf-8")):
        fail("manifest self digest differs")

    case_payload = load_object(root / "cases.json")
    case_rows = case_payload.get("cases")
    if (
        not isinstance(case_rows, list)
        or len(case_rows) != 6
        or case_payload.get("model_calls") != 0
    ):
        fail("case freeze must contain six zero-call contexts")
    case_ids = {str(row["case_id"]) for row in case_rows if isinstance(row, dict)}
    if len(case_ids) != 6:
        fail("case IDs must be unique")
    upstream_rows = [
        row
        for row in case_rows
        if isinstance(row, dict) and row.get("origin") == "UPSTREAM_REGRESSION_TEST_SEMANTICS"
    ]
    if {row.get("upstream_test_name") for row in upstream_rows} != set(
        registry["upstream_test_names"]
    ):
        fail("upstream regression-test bindings differ")

    result_payload = load_object(root / "results.json")
    results = result_payload.get("results")
    if not isinstance(results, list) or len(results) != 6:
        fail("results must contain six rows")
    transitions = Counter(str(row["transition"]) for row in results if isinstance(row, dict))
    fault_modes = Counter(str(row["fault_mode"]) for row in results if isinstance(row, dict))
    if transitions != Counter({"ALLOW->HOLD": 4, "HOLD->ALLOW": 2}):
        fail(f"transition support differs: {dict(transitions)}")
    if fault_modes != Counter(
        {
            "DENY_TRUE_ACCEPTED": 2,
            "NONTRUE_RESULT_ACCEPTED": 1,
            "QUERY_TARGET_CHANGES_PRECEDENCE": 2,
            "UNDEFINED_RESULT_ACCEPTED": 1,
        }
    ):
        fail(f"fault-mode support differs: {dict(fault_modes)}")
    if {str(row["case_id"]) for row in results if isinstance(row, dict)} != case_ids:
        fail("result IDs differ from frozen case IDs")
    if any(row["old_action"] == row["new_action"] for row in results if isinstance(row, dict)):
        fail("every case must expose a changed verifier action")

    minimum = load_object(root / "minimum-suite.json")
    if (
        minimum.get("witness_cases") != 4
        or len(minimum.get("selected_case_ids", [])) != 4
        or minimum.get("coverage", {}).get("action_edges") != {"covered": 2, "total": 2}
        or minimum.get("coverage", {}).get("documented_fault_modes") != {"covered": 4, "total": 4}
    ):
        fail("minimum-suite certificate differs")
    receipt = load_object(root / "source-validation-receipt.json")
    if (
        receipt.get("status") != "HISTORICAL_SIGSTORE_POLICY_VERIFIER_FAULT_REPRODUCED"
        or receipt.get("model_calls") != 0
        or receipt.get("credentials_retained") is not False
        or receipt.get("source_bytes_match_registry") is not True
        or receipt.get("test_source_sha256") != registry["test_sha256"]
        or receipt.get("upstream_test_names") != registry["upstream_test_names"]
    ):
        fail("source-validation boundary differs")

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
        "repositories": 1,
        "transitions": dict(sorted(transitions.items())),
        "upstream_regression_fixtures": len(upstream_rows),
    }


def main() -> int:
    report = validate()
    print(
        "sigstore-policy-verifier-validation: "
        f"cases={report['cases']} minimum={report['minimum_cases']} "
        f"upstream={report['upstream_regression_fixtures']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
