#!/usr/bin/env python3
"""Reproduce a historical agent-governance Rego verdict-interface fault."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402
from claimpromotebench.policy_difference import (  # noqa: E402
    PolicyDifference,
    adequacy,
    minimum_complete_suite,
)

Json = dict[str, Any]
STUDY_ROOT = ROOT / "v2" / "agent-governance-policy-interface-revision-v1"
SOURCE_ROOT = STUDY_ROOT / "sources"
REGISTRY_PATH = SOURCE_ROOT / "registry.json"
GENERATED = (
    "cases.json",
    "results.json",
    "minimum-suite.json",
    "source-validation-receipt.json",
    "artifact-manifest.json",
)


def fail(message: str) -> None:
    raise SystemExit(f"agent-governance-policy-interface-build: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def opa_metadata(opa: Path) -> Json:
    completed = subprocess.run([str(opa), "version"], check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        fail(f"OPA version failed: {completed.stderr.strip()}")
    fields = {
        key.strip(): value.strip()
        for line in completed.stdout.splitlines()
        if ":" in line
        for key, value in [line.split(":", maxsplit=1)]
    }
    if fields.get("Version") != "1.19.1":
        fail(f"expected OPA 1.19.1, found {fields.get('Version')!r}")
    return {
        "binary_sha256": sha256_file(opa),
        "build_commit": fields.get("Build Commit"),
        "platform": fields.get("Platform"),
        "rego_version": fields.get("Rego Version"),
        "version": fields["Version"],
    }


def validate_sources(registry: Json) -> None:
    for path_key, digest_key in (
        ("old_source", "old_sha256"),
        ("new_source", "new_sha256"),
        ("test_source", "test_sha256"),
        ("license_path", "license_sha256"),
    ):
        path = ROOT / str(registry[path_key])
        if not path.is_file() or sha256_file(path) != registry[digest_key]:
            fail(f"source digest differs: {path_key}")


def eval_query(opa: Path, policy: Path, query: str) -> Any:
    completed = subprocess.run(
        [str(opa), "eval", "--format=json", "--data", str(policy), query],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        fail(f"OPA query failed: {completed.stderr.strip()}")
    payload = json.loads(completed.stdout)
    result = payload.get("result")
    if result in (None, []):
        return None
    try:
        return result[0]["expressions"][0]["value"]
    except (IndexError, KeyError, TypeError) as exc:
        fail(f"OPA returned a malformed query result: {exc}")


def rego_call(name: str, arguments: Sequence[Any], suffix: str = "") -> str:
    encoded = ", ".join(canonical_json(argument) for argument in arguments)
    return f"data.agt.patterns.{name}({encoded}){suffix}"


def run_upstream_tests(opa: Path, policy: Path, tests: Path) -> Json:
    with tempfile.TemporaryDirectory(prefix="cpb-agt-policy-tests-") as directory:
        root = Path(directory)
        shutil.copyfile(policy, root / "patterns.rego")
        shutil.copyfile(tests, root / "patterns_test.rego")
        completed = subprocess.run(
            [str(opa), "test", str(root), "--format=json"],
            check=False,
            capture_output=True,
            text=True,
        )
    rows = json.loads(completed.stdout)
    if not isinstance(rows, list):
        fail("OPA test output must be a list")
    failed = sorted(
        str(row["name"]) for row in rows if isinstance(row, dict) and row.get("fail") is True
    )
    return {"failed": failed, "passed": len(rows) - len(failed), "total": len(rows)}


def cases() -> list[Json]:
    return [
        {
            "case_id": "agt-zero-leftmost",
            "patterns": ["[0-9]*"],
            "text": "card 4111",
            "upstream_test_name": "test_zero_length_leftmost_match_still_denies",
        },
        {
            "case_id": "agt-empty-zero-width",
            "patterns": ["x*"],
            "text": "",
            "upstream_test_name": "test_empty_text_with_zero_width_pattern_denies",
        },
    ]


def build(opa: Path, output_root: Path) -> None:
    registry = load_object(REGISTRY_PATH)
    validate_sources(registry)
    old_policy = ROOT / str(registry["old_source"])
    new_policy = ROOT / str(registry["new_source"])
    test_source = ROOT / str(registry["test_source"])
    old_tests = run_upstream_tests(opa, old_policy, test_source)
    new_tests = run_upstream_tests(opa, new_policy, test_source)
    expected_failures = sorted(registry["all_new_regression_test_names"])
    if old_tests != {"failed": expected_failures, "passed": 11, "total": 15}:
        fail(f"old-source regression result differs: {old_tests}")
    if new_tests != {"failed": [], "passed": 15, "total": 15}:
        fail(f"new-source regression result differs: {new_tests}")

    result_rows: list[Json] = []
    differences: list[PolicyDifference] = []
    for case in cases():
        arguments = [case["text"], case["patterns"]]
        match_query = rego_call("matches_any", arguments)
        decision_query = rego_call("deny_if_pattern", [*arguments, "external_audit"], ".decision")
        old_match = eval_query(opa, old_policy, match_query)
        new_match = eval_query(opa, new_policy, match_query)
        old_decision = eval_query(opa, old_policy, decision_query)
        new_decision = eval_query(opa, new_policy, decision_query)
        if (old_match, new_match, old_decision, new_decision) != (True, True, None, "deny"):
            fail(f"historical behavior differs for {case['case_id']}")
        result_rows.append(
            {
                "case_id": case["case_id"],
                "new_action": "HOLD",
                "new_deny_decision": new_decision,
                "new_matches_any": new_match,
                "old_action": "ALLOW",
                "old_deny_decision": old_decision,
                "old_matches_any": old_match,
                "transition": "ALLOW->HOLD",
                "upstream_test_name": case["upstream_test_name"],
            }
        )
        differences.append(
            PolicyDifference(
                context_id=str(case["case_id"]),
                left_action="ALLOW",
                right_action="HOLD",
                witnessed_rules=frozenset({"ZERO_LENGTH_MATCH_VERDICT_GAP"}),
            )
        )
    selected = minimum_complete_suite(
        differences,
        required_rules=["ZERO_LENGTH_MATCH_VERDICT_GAP"],
        required_edges=[("ALLOW", "HOLD")],
    )
    if selected is None:
        fail("no complete external-fault witness exists")
    coverage = adequacy(
        selected,
        required_rules=["ZERO_LENGTH_MATCH_VERDICT_GAP"],
        required_edges=[("ALLOW", "HOLD")],
    )
    if len(selected) != 1 or not coverage.complete:
        fail("expected one-case exact minimum")

    output_root.mkdir(parents=True, exist_ok=True)
    write_json(
        output_root / "cases.json",
        {
            "action_mapping": (
                "Author mapping of the upstream commit's documented caller fallback: "
                "undefined deny verdict to ALLOW; deny verdict to HOLD."
            ),
            "cases": cases(),
            "human_annotators": 0,
            "model_calls": 0,
            "schema_version": "1.0.0",
            "status": "FROZEN_UPSTREAM_DECISION_REGRESSION_CASES",
        },
    )
    write_json(
        output_root / "results.json",
        {
            "fault_mode": "ZERO_LENGTH_MATCH_VERDICT_GAP",
            "new_upstream_tests": new_tests,
            "old_upstream_tests": old_tests,
            "results": result_rows,
            "schema_version": "1.0.0",
            "transition_support": {"ALLOW->HOLD": len(result_rows)},
        },
    )
    write_json(
        output_root / "minimum-suite.json",
        {
            "candidate_cases": len(result_rows),
            "coverage": {
                "action_edges": {"covered": 1, "total": 1},
                "documented_fault_modes": {"covered": 1, "total": 1},
            },
            "lower_bound_cases": 1,
            "schema_version": "1.0.0",
            "selected_case_ids": [row.context_id for row in selected],
            "status": "EXACT_MINIMUM_RELATIVE_TO_UPSTREAM_DECISION_TESTS",
            "witness_cases": len(selected),
        },
    )
    receipt: Json = {
        "action_mapping_is_author_mapping": True,
        "architecture_boundary": (
            "The upstream deterministic ACS policy point surrounds agent model/tool lifecycle "
            "events; this reproduction contains no model inference."
        ),
        "change_commit": registry["change_commit"],
        "change_url": registry["change_url"],
        "credentials_retained": False,
        "formal_search_query": registry["formal_search_query"],
        "formal_search_rank": registry["formal_search_rank"],
        "model_calls": 0,
        "new_source_sha256": registry["new_sha256"],
        "old_commit": registry["old_commit"],
        "old_source_sha256": registry["old_sha256"],
        "opa_runtime": opa_metadata(opa),
        "repository": registry["repository"],
        "schema_version": "1.0.0",
        "source_bytes_match_registry": True,
        "status": "HISTORICAL_AGENT_GOVERNANCE_POLICY_INTERFACE_FAULT_REPRODUCED",
        "test_source_sha256": registry["test_sha256"],
        "upstream_test_results": {"new": new_tests, "old": old_tests},
    }
    write_json(output_root / "source-validation-receipt.json", receipt)
    bound = tuple(name for name in GENERATED if name != "artifact-manifest.json")
    manifest: Json = {
        "files": {name: sha256_file(output_root / name) for name in bound},
        "schema_version": "1.0.0",
        "source_files": {
            str(registry[path_key]): registry[digest_key]
            for path_key, digest_key in (
                ("old_source", "old_sha256"),
                ("new_source", "new_sha256"),
                ("test_source", "test_sha256"),
                ("license_path", "license_sha256"),
            )
        },
        "status": "COMPLETE_DETERMINISTIC_BUILD",
    }
    manifest["self_digest"] = sha256_bytes(canonical_json(manifest).encode())
    write_json(output_root / "artifact-manifest.json", manifest)


def compare_build(candidate: Path) -> None:
    differences = [
        name
        for name in GENERATED
        if not (STUDY_ROOT / name).is_file()
        or (STUDY_ROOT / name).read_bytes() != (candidate / name).read_bytes()
    ]
    if differences:
        fail(f"deterministic rebuild differs: {differences}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opa", type=Path, default=Path(shutil.which("opa") or "opa"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    opa = args.opa.resolve()
    if not opa.is_file() or not re.fullmatch(r"opa(?:\.v[0-9.]+)?", opa.name):
        fail(f"OPA executable is unavailable or unexpectedly named: {opa}")
    if args.check:
        with tempfile.TemporaryDirectory(prefix="cpb-agt-policy-build-") as directory:
            candidate = Path(directory) / STUDY_ROOT.name
            build(opa, candidate)
            compare_build(candidate)
    else:
        existing = [name for name in GENERATED if (STUDY_ROOT / name).exists()]
        if existing:
            fail(f"refusing to overwrite generated artifacts: {existing}")
        build(opa, STUDY_ROOT)
    print(
        "agent-governance-policy-interface-build: "
        f"cases=2 minimum=1 opa={opa_metadata(opa)['version']} check={args.check}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
