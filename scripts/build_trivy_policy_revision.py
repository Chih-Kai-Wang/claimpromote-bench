#!/usr/bin/env python3
"""Reproduce the Trivy KCV0030 inverted-predicate policy revision."""

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
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.hashing import (  # noqa: E402
    canonical_json,
    sha256_bytes,
    sha256_file,
)
from claimpromotebench.policy_difference import (  # noqa: E402
    PolicyDifference,
    adequacy,
    minimum_complete_suite,
)

Json = dict[str, Any]
STUDY_ROOT = ROOT / "v2" / "trivy-policy-revision-v1"
SOURCE_ROOT = STUDY_ROOT / "sources"
REGISTRY_PATH = SOURCE_ROOT / "registry.json"
GENERATED = (
    "cases.json",
    "results.json",
    "minimum-suite.json",
    "source-validation-receipt.json",
    "artifact-manifest.json",
)
QUERY = "data.builtin.kubernetes.KCV0030.deny"
IMPORT_LINE = "import data.lib.kubernetes\n"
ADAPTED_IMPORTS = "import data.lib.kubernetes\n\nimport data.lib.result\n"


def fail(message: str) -> NoReturn:
    raise SystemExit(f"trivy-policy-revision-build: {message}")


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


def api_server(*, configured_in: str | None) -> Json:
    command = ["kube-apiserver"]
    args: list[str] | None = None
    option = (
        "--encryption-provider-config=<filename>"
        if configured_in is not None
        else "--anonymous-auth=false"
    )
    if configured_in == "command" or configured_in is None:
        command.extend(["--advertise-address=192.168.49.2", option])
    elif configured_in == "args":
        args = ["--advertise-address=192.168.49.2", option]
    elif configured_in == "missing_args":
        args = ["--advertise-address=192.168.49.2", "--anonymous-auth=false"]
    else:
        fail(f"unknown API-server fixture: {configured_in}")
    container: Json = {"command": command, "image": "busybox", "name": "hello"}
    if args is not None:
        container["args"] = args
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "apiserver",
            "labels": {"component": "kube-apiserver", "tier": "control-plane"},
        },
        "spec": {"containers": [container]},
    }


def cases() -> list[Json]:
    return [
        {
            "case_id": "trivy-01",
            "configured": True,
            "input": api_server(configured_in="command"),
            "origin": "UPSTREAM_REGRESSION_TEST_SEMANTICS",
            "upstream_test_name": "test_encryption_provider_config_is_set",
        },
        {
            "case_id": "trivy-02",
            "configured": False,
            "input": api_server(configured_in=None),
            "origin": "UPSTREAM_REGRESSION_TEST_SEMANTICS",
            "upstream_test_name": "test_encryption_provider_config_is_not_set",
        },
        {
            "case_id": "trivy-03",
            "configured": True,
            "input": api_server(configured_in="args"),
            "origin": "UPSTREAM_REGRESSION_TEST_SEMANTICS",
            "upstream_test_name": "test_encryption_provider_config_is_set_args",
        },
        {
            "case_id": "trivy-04",
            "configured": False,
            "input": api_server(configured_in="missing_args"),
            "origin": "UPSTREAM_REGRESSION_TEST_SEMANTICS",
            "upstream_test_name": "test_encryption_provider_config_is_not_set_args",
        },
    ]


def adapted_policy(source: str) -> str:
    if source.count(IMPORT_LINE) != 1:
        fail("upstream policy import boundary differs")
    return source.replace(IMPORT_LINE, ADAPTED_IMPORTS)


def evaluate(opa: Path, policy_source: str, input_value: Json, registry: Json) -> int:
    with tempfile.TemporaryDirectory(prefix="cpb-trivy-opa-") as directory:
        root = Path(directory)
        policy_path = root / "policy.rego"
        policy_path.write_text(adapted_policy(policy_source), encoding="utf-8")
        completed = subprocess.run(
            [
                str(opa),
                "eval",
                "--v0-compatible",
                "--format=json",
                "--stdin-input",
                "--data",
                str(policy_path),
                "--data",
                str(ROOT / str(registry["library_source"])),
                "--data",
                str(ROOT / str(registry["compat_source"])),
                QUERY,
            ],
            input=canonical_json(input_value),
            check=False,
            capture_output=True,
            text=True,
        )
    if completed.returncode != 0:
        fail(f"OPA evaluation failed: {completed.stderr.strip()}")
    payload = json.loads(completed.stdout)
    result = payload.get("result")
    if result == [] or result is None:
        return 0
    try:
        value = result[0]["expressions"][0]["value"]
    except (IndexError, KeyError, TypeError) as exc:
        fail(f"OPA returned malformed output: {exc}")
    if not isinstance(value, list):
        fail(f"deny query must return a set encoded as a list: {value!r}")
    return len(value)


def validate_sources(registry: Json) -> None:
    bindings = (
        ("old_source", "old_sha256"),
        ("new_source", "new_sha256"),
        ("test_source", "test_sha256"),
        ("library_source", "library_sha256"),
        ("compat_source", "compat_sha256"),
    )
    for path_key, digest_key in bindings:
        path = ROOT / str(registry[path_key])
        if not path.is_file() or sha256_file(path) != registry[digest_key]:
            fail(f"source digest differs: {path_key}")
    if not (ROOT / str(registry["license_path"])).is_file():
        fail("upstream MIT license copy is absent")
    test_source = (ROOT / str(registry["test_source"])).read_text(encoding="utf-8")
    if any(str(name) not in test_source for name in registry["upstream_test_names"]):
        fail("registered upstream test name is absent from the test source")


def build(opa: Path, output_root: Path) -> None:
    registry = load_object(REGISTRY_PATH)
    validate_sources(registry)
    old_source = (ROOT / str(registry["old_source"])).read_text(encoding="utf-8")
    new_source = (ROOT / str(registry["new_source"])).read_text(encoding="utf-8")
    case_rows = cases()
    if {row["upstream_test_name"] for row in case_rows} != set(registry["upstream_test_names"]):
        fail("case-to-upstream-test binding differs")

    results: list[Json] = []
    transitions: Counter[str] = Counter()
    differences: list[PolicyDifference] = []
    for case in case_rows:
        old_denials = evaluate(opa, old_source, case["input"], registry)
        new_denials = evaluate(opa, new_source, case["input"], registry)
        old_action = "HOLD" if old_denials else "ALLOW"
        new_action = "HOLD" if new_denials else "ALLOW"
        expected_new = "ALLOW" if case["configured"] else "HOLD"
        if new_action != expected_new or old_action == new_action:
            fail(f"historical policy behavior differs for {case['case_id']}")
        transition = f"{old_action}->{new_action}"
        transitions[transition] += 1
        results.append(
            {
                "case_id": case["case_id"],
                "new_action": new_action,
                "new_denial_count": new_denials,
                "old_action": old_action,
                "old_denial_count": old_denials,
                "transition": transition,
                "upstream_test_name": case["upstream_test_name"],
            }
        )
        differences.append(
            PolicyDifference(
                context_id=str(case["case_id"]),
                left_action=old_action,
                right_action=new_action,
                witnessed_rules=frozenset({"INVERTED_FLAG_PREDICATE"}),
            )
        )
    if transitions != Counter({"ALLOW->HOLD": 2, "HOLD->ALLOW": 2}):
        fail(f"unexpected transition support: {dict(transitions)}")

    required_rules = ["INVERTED_FLAG_PREDICATE"]
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
    if len(selected) != 2 or not report.complete:
        fail("two cases must cover the fault mode and both action directions")

    output_root.mkdir(parents=True, exist_ok=True)
    write_json(
        output_root / "cases.json",
        {
            "cases": case_rows,
            "model_calls": 0,
            "schema_version": "1.0.0",
            "status": "FROZEN_UPSTREAM_REGRESSION_TEST_SEMANTICS",
        },
    )
    write_json(
        output_root / "results.json",
        {
            "documented_fault_mode": "INVERTED_FLAG_PREDICATE",
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
                "action_edges": {"covered": 2, "total": 2},
                "documented_fault_modes": {"covered": 1, "total": 1},
            },
            "lower_bound_cases": 2,
            "schema_version": "1.0.0",
            "selected_case_ids": [row.context_id for row in selected],
            "status": "EXACT_MINIMUM_RELATIVE_TO_UPSTREAM_TEST_CASES",
            "witness_cases": len(selected),
        },
    )
    receipt: Json = {
        "change_commit": registry["change_commit"],
        "change_url": registry["change_url"],
        "compatibility_boundary": {
            "adaptation": "INSERT_IMPORT_DATA_LIB_RESULT_ONCE",
            "compat_source_sha256": registry["compat_sha256"],
            "purpose": (
                "Construct the host-provided result payload after the upstream predicate matches."
            ),
            "upstream_policy_bytes_modified_on_disk": False,
        },
        "credentials_retained": False,
        "library_sha256": registry["library_sha256"],
        "model_calls": 0,
        "new_source_sha256": registry["new_sha256"],
        "old_commit": registry["old_commit"],
        "old_source_sha256": registry["old_sha256"],
        "opa_runtime": opa_metadata(opa),
        "repository": registry["repository"],
        "schema_version": "1.0.0",
        "source_bytes_match_registry": True,
        "status": "HISTORICAL_TRIVY_POLICY_FAULT_REPRODUCED",
        "test_source_sha256": registry["test_sha256"],
        "upstream_test_names": registry["upstream_test_names"],
    }
    write_json(output_root / "source-validation-receipt.json", receipt)
    bound_paths = tuple(name for name in GENERATED if name != "artifact-manifest.json")
    manifest: Json = {
        "files": {name: sha256_file(output_root / name) for name in bound_paths},
        "schema_version": "1.0.0",
        "source_files": {
            str(registry[key]): registry[digest]
            for key, digest in (
                ("old_source", "old_sha256"),
                ("new_source", "new_sha256"),
                ("test_source", "test_sha256"),
                ("library_source", "library_sha256"),
                ("compat_source", "compat_sha256"),
            )
        },
        "status": "COMPLETE_DETERMINISTIC_BUILD",
    }
    manifest["self_digest"] = sha256_bytes(canonical_json(manifest).encode("utf-8"))
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
        with tempfile.TemporaryDirectory(prefix="cpb-trivy-build-") as directory:
            candidate = Path(directory) / STUDY_ROOT.name
            build(opa, candidate)
            compare_build(candidate)
    else:
        existing = [name for name in GENERATED if (STUDY_ROOT / name).exists()]
        if existing:
            fail(f"refusing to overwrite generated artifacts: {existing}")
        build(opa, STUDY_ROOT)
    print(
        "trivy-policy-revision-build: "
        f"cases=4 minimum=2 opa={opa_metadata(opa)['version']} check={args.check}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
