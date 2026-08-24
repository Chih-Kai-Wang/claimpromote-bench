#!/usr/bin/env python3
"""Validate the frozen Trivy policy-revision evidence offline."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file

ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = ROOT / "v2" / "trivy-policy-revision-v1"
ACCOUNT_MARKERS = ("f0909172434", "wangzhikai", "Chih-Kai")
Json = dict[str, Any]


def fail(message: str) -> None:
    raise ValueError(f"trivy-policy-revision-validation: {message}")


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
        ("library_source", "library_sha256"),
        ("compat_source", "compat_sha256"),
    ):
        path = ROOT / str(registry[path_key])
        if not path.is_file() or sha256_file(path) != registry[digest_key]:
            fail(f"source digest differs: {path_key}")
    if registry.get("license") != "MIT":
        fail("upstream license boundary differs")

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

    cases = load_object(root / "cases.json")
    rows = cases.get("cases")
    if not isinstance(rows, list) or len(rows) != 4 or cases.get("model_calls") != 0:
        fail("case boundary differs")
    if {row.get("origin") for row in rows if isinstance(row, dict)} != {
        "UPSTREAM_REGRESSION_TEST_SEMANTICS"
    }:
        fail("all cases must bind upstream regression-test semantics")
    if {row.get("upstream_test_name") for row in rows if isinstance(row, dict)} != set(
        registry["upstream_test_names"]
    ):
        fail("upstream test bindings differ")

    result_payload = load_object(root / "results.json")
    results = result_payload.get("results")
    if not isinstance(results, list) or len(results) != 4:
        fail("results must contain four rows")
    transitions = Counter(str(row["transition"]) for row in results if isinstance(row, dict))
    if transitions != Counter({"ALLOW->HOLD": 2, "HOLD->ALLOW": 2}):
        fail(f"transition support differs: {dict(transitions)}")
    if any(row["old_action"] == row["new_action"] for row in results if isinstance(row, dict)):
        fail("every case must expose the historical fault")

    minimum = load_object(root / "minimum-suite.json")
    if (
        minimum.get("witness_cases") != 2
        or len(minimum.get("selected_case_ids", [])) != 2
        or minimum.get("coverage", {}).get("action_edges") != {"covered": 2, "total": 2}
        or minimum.get("coverage", {}).get("documented_fault_modes") != {"covered": 1, "total": 1}
    ):
        fail("minimum-suite certificate differs")

    receipt = load_object(root / "source-validation-receipt.json")
    if (
        receipt.get("status") != "HISTORICAL_TRIVY_POLICY_FAULT_REPRODUCED"
        or receipt.get("model_calls") != 0
        or receipt.get("source_bytes_match_registry") is not True
        or receipt.get("credentials_retained") is not False
        or receipt.get("upstream_test_names") != registry["upstream_test_names"]
    ):
        fail("source-validation receipt differs")
    compatibility = receipt.get("compatibility_boundary")
    if not isinstance(compatibility, dict) or compatibility.get("adaptation") != (
        "INSERT_IMPORT_DATA_LIB_RESULT_ONCE"
    ):
        fail("host-function compatibility boundary differs")

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
        "cases": len(rows),
        "minimum_cases": int(minimum["witness_cases"]),
        "repositories": 1,
        "transitions": dict(sorted(transitions.items())),
        "upstream_regression_fixtures": len(rows),
    }


def main() -> int:
    report = validate()
    print(
        "trivy-policy-revision-validation: "
        f"cases={report['cases']} minimum={report['minimum_cases']} "
        f"upstream={report['upstream_regression_fixtures']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
