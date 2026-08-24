#!/usr/bin/env python3
"""Reproduce a historical Sigstore Cosign policy-verifier fault and its fix."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
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
STUDY_ROOT = ROOT / "v2" / "sigstore-policy-verifier-revision-v1"
SOURCE_ROOT = STUDY_ROOT / "sources"
REGISTRY_PATH = SOURCE_ROOT / "registry.json"
GENERATED = (
    "cases.json",
    "results.json",
    "minimum-suite.json",
    "source-validation-receipt.json",
    "artifact-manifest.json",
)
INPUT = {
    "_type": "https://in-toto.io/Statement/v0.1",
    "predicateType": "https://slsa.dev/provenance/v0.2",
}


def fail(message: str) -> None:
    raise SystemExit(f"sigstore-policy-verifier-build: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def opa_metadata(opa: Path) -> Json:
    completed = subprocess.run(
        [str(opa), "version"],
        check=False,
        capture_output=True,
        text=True,
    )
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


def cases() -> list[Json]:
    return [
        {
            "case_id": "sigstore-01",
            "fault_mode": "UNDEFINED_RESULT_ACCEPTED",
            "origin": "UPSTREAM_REGRESSION_TEST_SEMANTICS",
            "upstream_test_name": "undefined result due to no matching rules",
            "policy_source": (
                "package signature\n\n"
                "allow {\n"
                '    input.predicateType == "https://slsa.dev/provenance/v99.9"\n'
                "}\n"
            ),
        },
        {
            "case_id": "sigstore-02",
            "fault_mode": "NONTRUE_RESULT_ACCEPTED",
            "origin": "UPSTREAM_REGRESSION_TEST_SEMANTICS",
            "upstream_test_name": "policy query evaluates to false",
            "policy_source": "package signature\n\ndefault allow = false\n",
        },
        {
            "case_id": "sigstore-03",
            "fault_mode": "DENY_TRUE_ACCEPTED",
            "origin": "UPSTREAM_COMMIT_MESSAGE_FAILURE_MODE",
            "policy_source": (
                "package signature\n\n"
                "deny {\n"
                '    input.predicateType == "https://slsa.dev/provenance/v0.2"\n'
                "}\n"
            ),
        },
        {
            "case_id": "sigstore-04",
            "fault_mode": "DENY_TRUE_ACCEPTED",
            "origin": "AUTHOR_VARIANT_OF_DOCUMENTED_FAILURE_MODE",
            "policy_source": (
                "package signature\n\n"
                "deny {\n"
                '    input._type == "https://in-toto.io/Statement/v0.1"\n'
                "}\n"
            ),
        },
        {
            "case_id": "sigstore-05",
            "fault_mode": "QUERY_TARGET_CHANGES_PRECEDENCE",
            "origin": "AUTHOR_CONTRAST_FOR_CHANGED_QUERY",
            "policy_source": (
                "package signature\n\n"
                "allow {\n"
                '    input.predicateType == "https://slsa.dev/provenance/v0.2"\n'
                "}\n\n"
                "deny[msg] {\n"
                '    input._type == "https://in-toto.io/Statement/v0.1"\n'
                '    msg := "legacy type denial"\n'
                "}\n"
            ),
        },
        {
            "case_id": "sigstore-06",
            "fault_mode": "QUERY_TARGET_CHANGES_PRECEDENCE",
            "origin": "AUTHOR_CONTRAST_FOR_CHANGED_QUERY",
            "policy_source": (
                "package signature\n\n"
                "allow {\n"
                '    input._type == "https://in-toto.io/Statement/v0.1"\n'
                "}\n\n"
                "deny[msg] {\n"
                '    input.predicateType == "https://slsa.dev/provenance/v0.2"\n'
                '    msg := "legacy predicate denial"\n'
                "}\n"
            ),
        },
    ]


def evaluate_query(opa: Path, policy_source: str, query: str) -> Json:
    with tempfile.TemporaryDirectory(prefix="cpb-sigstore-opa-") as directory:
        policy_path = Path(directory) / "policy.rego"
        policy_path.write_text(policy_source, encoding="utf-8")
        completed = subprocess.run(
            [
                str(opa),
                "eval",
                "--v0-compatible",
                "--format=json",
                "--stdin-input",
                "--data",
                str(policy_path),
                query,
            ],
            input=canonical_json(INPUT),
            check=False,
            capture_output=True,
            text=True,
        )
    if completed.returncode != 0:
        fail(f"OPA query failed for {query}: {completed.stderr.strip()}")
    payload = json.loads(completed.stdout)
    result = payload.get("result")
    if result == [] or result is None:
        return {"defined": False, "value": None}
    try:
        value = result[0]["expressions"][0]["value"]
    except (IndexError, KeyError, TypeError) as exc:
        fail(f"OPA returned a malformed query result: {exc}")
    return {"defined": True, "value": value}


def old_action(observation: Json) -> str:
    if observation["defined"] is False or observation["value"] is True:
        return "ALLOW"
    value = observation["value"]
    if isinstance(value, list):
        return "HOLD" if value else "ALLOW"
    fail(f"old verifier fixture reaches unsupported legacy result: {value!r}")


def new_action(observation: Json) -> str:
    return "ALLOW" if observation == {"defined": True, "value": True} else "HOLD"


def validate_sources(registry: Json) -> None:
    for revision in ("old", "new"):
        path = ROOT / str(registry[f"{revision}_source"])
        if sha256_file(path) != str(registry[f"{revision}_sha256"]):
            fail(f"{revision} Sigstore source digest differs")
    license_path = ROOT / str(registry["license_path"])
    if not license_path.is_file():
        fail("Apache-2.0 license copy is absent")
    test_path = ROOT / str(registry["test_source"])
    if sha256_file(test_path) != str(registry["test_sha256"]):
        fail("Sigstore regression-test source digest differs")


def build(opa: Path, output_root: Path) -> None:
    registry = load_object(REGISTRY_PATH)
    validate_sources(registry)
    case_rows = cases()
    results: list[Json] = []
    differences: list[PolicyDifference] = []
    transitions: Counter[str] = Counter()
    fault_modes: Counter[str] = Counter()
    for case in case_rows:
        deny = evaluate_query(opa, str(case["policy_source"]), "data.signature.deny")
        allow = evaluate_query(opa, str(case["policy_source"]), "data.signature.allow")
        before = old_action(deny)
        after = new_action(allow)
        if before == after:
            fail(f"{case['case_id']} does not expose the historical verifier change")
        transition = f"{before}->{after}"
        transitions[transition] += 1
        fault_modes[str(case["fault_mode"])] += 1
        results.append(
            {
                "case_id": case["case_id"],
                "fault_mode": case["fault_mode"],
                "new_action": after,
                "new_query_observation": allow,
                "old_action": before,
                "old_query_observation": deny,
                "transition": transition,
            }
        )
        differences.append(
            PolicyDifference(
                context_id=str(case["case_id"]),
                left_action=before,
                right_action=after,
                witnessed_rules=frozenset({str(case["fault_mode"])}),
            )
        )
    if transitions != Counter({"ALLOW->HOLD": 4, "HOLD->ALLOW": 2}):
        fail(f"unexpected transition support: {dict(transitions)}")
    if fault_modes != Counter(
        {
            "UNDEFINED_RESULT_ACCEPTED": 1,
            "NONTRUE_RESULT_ACCEPTED": 1,
            "DENY_TRUE_ACCEPTED": 2,
            "QUERY_TARGET_CHANGES_PRECEDENCE": 2,
        }
    ):
        fail(f"unexpected fault-mode support: {dict(fault_modes)}")

    required_rules = sorted(fault_modes)
    required_edges = sorted({row.edge for row in differences})
    selected = minimum_complete_suite(
        differences,
        required_rules=required_rules,
        required_edges=required_edges,
    )
    if selected is None:
        fail("no complete historical-fault witness exists")
    report = adequacy(
        selected,
        required_rules=required_rules,
        required_edges=required_edges,
    )
    if len(selected) != 4 or not report.complete:
        fail("expected four cases to cover four fault modes and both action directions")

    output_root.mkdir(parents=True, exist_ok=True)
    write_json(
        output_root / "cases.json",
        {
            "cases": case_rows,
            "context_input": INPUT,
            "model_calls": 0,
            "schema_version": "1.0.0",
            "status": "FROZEN_EXTERNAL_FAULT_CONTEXTS",
        },
    )
    write_json(
        output_root / "results.json",
        {
            "fault_mode_support": dict(sorted(fault_modes.items())),
            "results": results,
            "schema_version": "1.0.0",
            "transition_support": dict(sorted(transitions.items())),
        },
    )
    write_json(
        output_root / "minimum-suite.json",
        {
            "candidate_cases": len(case_rows),
            "coverage": {
                "action_edges": {
                    "covered": len(report.covered_edges),
                    "total": len(required_edges),
                },
                "documented_fault_modes": {
                    "covered": len(report.covered_rules),
                    "total": len(required_rules),
                },
            },
            "lower_bound_cases": len(required_rules),
            "schema_version": "1.0.0",
            "selected_case_ids": [row.context_id for row in selected],
            "status": "EXACT_MINIMUM_RELATIVE_TO_COMMITTED_CASES",
            "witness_cases": len(selected),
        },
    )
    receipt: Json = {
        "change_commit": registry["change_commit"],
        "change_url": registry["change_url"],
        "credentials_retained": False,
        "model_calls": 0,
        "new_source_sha256": registry["new_sha256"],
        "old_commit": registry["old_commit"],
        "old_source_sha256": registry["old_sha256"],
        "opa_runtime": opa_metadata(opa),
        "repository": registry["repository"],
        "schema_version": "1.0.0",
        "source_bytes_match_registry": True,
        "status": "HISTORICAL_SIGSTORE_POLICY_VERIFIER_FAULT_REPRODUCED",
        "test_source_sha256": registry["test_sha256"],
        "upstream_test_names": registry["upstream_test_names"],
        "upstream_test_path": registry["upstream_test_path"],
    }
    write_json(output_root / "source-validation-receipt.json", receipt)
    bound_paths = tuple(path for path in GENERATED if path != "artifact-manifest.json")
    manifest: Json = {
        "files": {path: sha256_file(output_root / path) for path in bound_paths},
        "schema_version": "1.0.0",
        "source_files": {
            str(registry["old_source"]): registry["old_sha256"],
            str(registry["new_source"]): registry["new_sha256"],
            str(registry["test_source"]): registry["test_sha256"],
        },
        "status": "COMPLETE_DETERMINISTIC_BUILD",
    }
    manifest["self_digest"] = sha256_bytes(canonical_json(manifest).encode("utf-8"))
    write_json(output_root / "artifact-manifest.json", manifest)


def compare_build(candidate: Path) -> None:
    differences = [
        relative
        for relative in GENERATED
        if not (STUDY_ROOT / relative).is_file()
        or (STUDY_ROOT / relative).read_bytes() != (candidate / relative).read_bytes()
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
        with tempfile.TemporaryDirectory(prefix="cpb-sigstore-build-") as directory:
            candidate = Path(directory) / STUDY_ROOT.name
            build(opa, candidate)
            compare_build(candidate)
    else:
        existing = [relative for relative in GENERATED if (STUDY_ROOT / relative).exists()]
        if existing:
            fail(f"refusing to overwrite generated artifacts: {existing}")
        build(opa, STUDY_ROOT)
    print(
        "sigstore-policy-verifier-build: "
        f"cases=6 minimum=4 opa={opa_metadata(opa)['version']} check={args.check}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
