#!/usr/bin/env python3
"""Validate every machine-checkable C0 boundary before the salt commitment."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_confirmatory_source_manifest import (  # noqa: E402
    MANIFEST_PATH,
    validate_manifest,
)
from confirmatory_subscription_authorization import (  # noqa: E402
    validate_plan_authorization,
)
from validate_stronger_model_study import validate_plan  # noqa: E402

from claimpromotebench.confirmatory_baseline import validate_model  # noqa: E402
from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def _nested(value: Json, dotted: str) -> Any:
    current: Any = value
    for key in dotted.split("."):
        if not isinstance(current, dict) or key not in current:
            raise ValueError(f"C0 plan lacks registered field: {dotted}")
        current = current[key]
    return current


_HASH_BINDINGS = {
    "protocol_lineage.r4_execution_receipt_file_sha256": (
        "v2/confirmatory/r4-execution/execution-receipt.json"
    ),
    "protocol_lineage.r5_void_receipt_file_sha256": (
        "v2/confirmatory/c1-r5/void-pre-post-receipt.json"
    ),
    "protocol_lineage.r5_prompt_hash_recovery_run_receipt_file_sha256": (
        "v2/confirmatory/c1-r5/prompt-hash-recovery-run-receipt.json"
    ),
    "protocol_lineage.r5_to_r6_change_scope_file_sha256": (
        "v2/confirmatory/r5-to-r6-change-scope.json"
    ),
    "dataset.benchmark_plan_sha256": "configs/v1-benchmark-plan.json",
    "dataset.input_schema_sha256": "schemas/benchmark-input-v1.schema.json",
    "dataset.gold_schema_sha256": "schemas/gold-label.schema.json",
    "prompt.renderer_sha256": "src/claimpromotebench/prompts.py",
    "prompt.policy_sha256": "policies/math-evidence-transition-1.0.0.json",
    "prompt.decision_schema_sha256": "schemas/agent-decision.schema.json",
    "prompt.prior_prompt_hash_denylist_file_sha256": (
        "configs/prior-hidden-prompt-hash-denylist-r6.json"
    ),
    "baselines.shallow_model_file_sha256": "v2/confirmatory/public-dev-text-nb-v1.json",
    "baselines.training_script_sha256": "scripts/train_confirmatory_shallow_baseline.py",
    "baselines.predictor_sha256": "scripts/predict_confirmatory_baselines.py",
    "baselines.feature_module_sha256": "src/claimpromotebench/confirmatory_baseline.py",
    "statistics.analysis_script_sha256": "scripts/analyze_confirmatory_hidden_study.py",
    "statistics.c2_finalizer_sha256": "scripts/finalize_confirmatory_c2.py",
    "statistics.power_analysis_script_sha256": "scripts/confirmatory_power_analysis.py",
    "statistics.power_assumptions_file_sha256": "v2/confirmatory/power-assumptions-r6.json",
    "statistics.power_analysis_report_file_sha256": "v2/confirmatory/power-analysis-r6.json",
    "workflows.c1_freeze_sha256": ".github/workflows/confirmatory-hidden-freeze.yml",
    "workflows.scored_study_sha256": ".github/workflows/confirmatory-hidden-study.yml",
    "runtime_source.manifest_file_sha256": MANIFEST_PATH,
    "runtime_source.manifest_builder_sha256": ("scripts/build_confirmatory_source_manifest.py"),
    "runtime_source.python311_lock_file_sha256": "tools/confirmatory-python311.lock",
    "implementation_sha256.dataset_builder": "scripts/build_v1_dataset.py",
    "implementation_sha256.prior_prompt_denylist_builder": (
        "scripts/build_prior_prompt_hash_denylist.py"
    ),
    "implementation_sha256.formal_templates": "src/claimpromotebench/formal.py",
    "implementation_sha256.dataset_module": "src/claimpromotebench/dataset.py",
    "implementation_sha256.hashing_module": "src/claimpromotebench/hashing.py",
    "implementation_sha256.error_types": "src/claimpromotebench/errors.py",
    "implementation_sha256.policy_module": "src/claimpromotebench/policy.py",
    "implementation_sha256.state_validation": "src/claimpromotebench/state.py",
    "implementation_sha256.oracle_module": "src/claimpromotebench/oracle.py",
    "implementation_sha256.executable_artifacts": "src/claimpromotebench/executable.py",
    "implementation_sha256.decision_validation": ("src/claimpromotebench/decision_validation.py"),
    "implementation_sha256.prompt_novelty_audit": "scripts/audit_hidden_prompt_novelty.py",
    "implementation_sha256.packet_builder": "scripts/build_stronger_model_packet.py",
    "implementation_sha256.c1_builder": "scripts/build_confirmatory_c1.py",
    "implementation_sha256.subscription_authorization": (
        "scripts/confirmatory_subscription_authorization.py"
    ),
    "implementation_sha256.c1_commitment_builder": "scripts/make_confirmatory_hidden_commitment.py",
    "implementation_sha256.prompt_manifest_builder": "scripts/freeze_prompt_manifest.py",
    "implementation_sha256.base_commitment_builder": "scripts/make_hidden_test_commitment.py",
    "implementation_sha256.dataset_validator": "scripts/validate_v1_plan.py",
    "implementation_sha256.packet_validator": "scripts/validate_stronger_model_study.py",
    "implementation_sha256.gold_free_service_runner": "scripts/run_confirmatory_service_study.py",
    "implementation_sha256.seed_derivation": "scripts/derive_confirmatory_seed.py",
    "implementation_sha256.drand_verifier": "tools/drand/fetch_verified_beacon.mjs",
    "implementation_sha256.drand_package_lock": "tools/drand/package-lock.json",
    "implementation_sha256.shortcut_audit": "src/claimpromotebench/shortcuts.py",
    "implementation_sha256.shortcut_report": "src/claimpromotebench/shortcut_report.py",
    "implementation_sha256.shortcut_features": "src/claimpromotebench/shortcut_features.py",
    "implementation_sha256.shortcut_model": "src/claimpromotebench/shortcut_model.py",
    "implementation_sha256.metrics": "src/claimpromotebench/metrics.py",
    "implementation_sha256.invariance_audit": "src/claimpromotebench/invariance.py",
    "implementation_sha256.formal_fixtures": "fixtures/formal/cases.json",
    "implementation_sha256.project_metadata": "pyproject.toml",
    "implementation_sha256.c0_validator": "scripts/validate_confirmatory_c0.py",
}


def validate_c0(plan_path: Path, require_seed_commitment: bool) -> Json:
    plan = load_json(plan_path)
    if "PENDING_C0_HASH" in plan_path.read_text(encoding="utf-8"):
        raise ValueError("C0 plan retains a placeholder digest")
    validate_plan(plan)
    authorization = validate_plan_authorization(plan)
    if authorization.get("status") != "SUBSCRIPTION_AUTHORIZATION_GATE_PASS":
        raise ValueError("C0 subscription authorization gate did not pass")
    if plan.get("design", {}).get("full_requires_pilot") is not False:
        raise ValueError("C0 unexpectedly permits a pilot")
    if plan.get("pilot", {}).get("pairs") != [] or plan.get("pilot", {}).get("instances") != 0:
        raise ValueError("C0 pilot boundary is not empty")
    if len(plan.get("formal_lanes", [])) != 2 or plan.get("exploratory_lanes") != []:
        raise ValueError("C0 must contain exactly two formal service lanes")
    statistics = plan.get("statistics", {})
    if statistics.get("confirmatory_family_size") != 2:
        raise ValueError("C0 primary hypothesis family is not exactly two")
    if len(statistics.get("hypotheses", [])) != 2:
        raise ValueError("C0 does not enumerate both primary hypotheses")
    if statistics.get("confirmatory_baseline_comparators") != ["public_dev_text_nb"]:
        raise ValueError("C0 confirmatory comparator family changed")
    execution = plan.get("execution", {})
    if execution.get("application_posts_per_cell") != 1:
        raise ValueError("C0 permits more than one application POST")
    if execution.get("client_retry_count") != 0 or execution.get("redirect_following") is not False:
        raise ValueError("C0 retry or redirect boundary changed")
    if float(execution.get("per_request_timeout_seconds", 0)) * 300 + 299 > 360 * 60:
        raise ValueError("C0 worst-case request timing exceeds the workflow job")
    for field, relative in _HASH_BINDINGS.items():
        expected = _nested(plan, field)
        if not isinstance(expected, str) or not _DIGEST.fullmatch(expected):
            raise ValueError(f"C0 digest is malformed: {field}")
        observed = sha256_file(ROOT / relative)
        if observed != expected:
            raise ValueError(f"C0 digest mismatch: {field}: {observed} != {expected}")
    runtime_source = plan.get("runtime_source")
    if not isinstance(runtime_source, dict):
        raise ValueError("C0 lacks the exact runtime source closure")
    runtime_manifest = load_json(ROOT / MANIFEST_PATH)
    manifest_report = validate_manifest(runtime_manifest)
    if (
        runtime_source.get("manifest_path") != MANIFEST_PATH
        or runtime_source.get("manifest_sha256") != manifest_report["manifest_sha256"]
        or runtime_source.get("manifest_file_count") != manifest_report["file_count"]
        or runtime_source.get("python_runtime") != "CPYTHON_3_11_16_LINUX_X86_64"
        or runtime_source.get("installation")
        != "PIP_REQUIRE_HASHES_ONLY_BINARY_WITHOUT_EDITABLE_PROJECT_INSTALL"
        or runtime_source.get("post_c0_diff_whitelist")
        != [
            "configs/fresh-confirmatory-seed-commitment.json",
            "configs/fresh-confirmatory-hidden-commitment.json",
            "v2/confirmatory/c1-r6/*.json",
        ]
    ):
        raise ValueError("C0 runtime source registry differs from the exact manifest")
    runtime_files = runtime_manifest.get("files_sha256")
    required_reachable = {
        "src/claimpromotebench/__init__.py",
        "src/claimpromotebench/statistics.py",
        "scripts/build_confirmatory_c1.py",
        "scripts/run_confirmatory_service_study.py",
        "tools/confirmatory-python311.lock",
    }
    if not isinstance(runtime_files, dict) or not required_reachable <= set(runtime_files):
        raise ValueError("C0 runtime manifest omits a reachable runtime dependency")
    for forbidden_startup in (
        "setup.py",
        "sitecustomize.py",
        "usercustomize.py",
        "src/sitecustomize.py",
        "src/usercustomize.py",
    ):
        if (ROOT / forbidden_startup).exists():
            raise ValueError(
                f"C0 forbids pre-verification Python startup code: {forbidden_startup}"
            )
    model = load_json(ROOT / str(plan["baselines"]["shallow_model_path"]))
    validate_model(model)
    if model["model_sha256"] != plan["baselines"]["shallow_model_sha256"]:
        raise ValueError("C0 shallow-model identity mismatch")
    power = load_json(ROOT / str(statistics["power_analysis_report_path"]))
    if (
        power.get("status") != "PRE_HIDDEN_POWER_GATE_PASS"
        or power.get("study_id") != plan.get("study_id")
        or power.get("all_comparisons_pass_0_80") is not True
        or float(power.get("minimum_power", 0.0)) < 0.8
        or power.get("design", {}).get("confirmatory_family_size") != 2
        or power.get("design", {}).get("pairs") != 150
        or power.get("design", {}).get("minimum_action_accuracy_effect") != 0.1
    ):
        raise ValueError("C0 pre-hidden power gate is not satisfied")
    denylist = load_json(ROOT / str(plan["prompt"]["prior_prompt_hash_denylist_path"]))
    denylist_hashes = denylist.get("prompt_sha256")
    denylist_payload = dict(denylist)
    denylist_digest = denylist_payload.pop("denylist_sha256", None)
    if (
        denylist.get("status") != "FROZEN_PRIOR_PROMPT_HASH_DENYLIST"
        or not isinstance(denylist_hashes, list)
        or len(denylist_hashes) != plan["prompt"]["prior_prompt_hash_denylist_count"]
        or len(set(denylist_hashes)) != len(denylist_hashes)
        or denylist.get("contains_prompt_text") is not False
        or denylist.get("contains_gold_labels") is not False
        or denylist_digest != sha256_bytes(canonical_json(denylist_payload).encode("utf-8"))
        or denylist_digest != plan["prompt"]["prior_prompt_hash_denylist_sha256"]
    ):
        raise ValueError("C0 prior prompt-hash denylist is malformed")
    runner_source = (ROOT / "scripts" / "run_confirmatory_service_study.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("postgate_decision", "gold.jsonl", 'add_argument("--dataset"'):
        if forbidden in runner_source:
            raise ValueError(f"gold-free worker contains forbidden dependency: {forbidden}")
    if (
        "claimpromotebench.v2" in runner_source
        or "claimpromotebench.decision_validation" not in runner_source
        or "build_confirmatory_c1" in runner_source
        or "confirmatory_subscription_authorization" in runner_source
        or "_verify_runtime_source_manifest(" not in runner_source
        or 'sha256_bytes(prompt.encode("utf-8"))' not in runner_source
    ):
        raise ValueError("gold-free worker isolation or independent recomputation changed")
    c1_source = (ROOT / "scripts" / "build_confirmatory_c1.py").read_text(encoding="utf-8")
    if (
        "run_confirmatory_service_study" in c1_source
        or "def c1_request_body_for_lane(" not in c1_source
        or "def c1_portable_decision_schema(" not in c1_source
    ):
        raise ValueError("C1 request construction is not isolated from the scored runner")
    decision_source = (ROOT / "src" / "claimpromotebench" / "decision_validation.py").read_text(
        encoding="utf-8"
    )
    if "from .gate" in decision_source or "from .oracle" in decision_source:
        raise ValueError("isolated decision validator imports a gate or oracle")
    workflow_source = (ROOT / ".github/workflows/confirmatory-hidden-study.yml").read_text(
        encoding="utf-8"
    )
    for required in (
        "run-name: claimpromotebench-r6-scored-singleton",
        "actions: read",
        "test \"$GITHUB_RUN_ATTEMPT\" = '1'",
        "Prove this is the only r6 scored workflow dispatch",
        'test "${#singleton_runs[@]}" -eq 1',
        'test "${singleton_runs[0]}" = "$GITHUB_RUN_ID"',
        "Prove the post-C1 source diff contains public JSON evidence only",
        'git merge-base --is-ancestor "$source_c0_commit" "$source_commit"',
        'git merge-base --is-ancestor "$source_commit" "$GITHUB_SHA"',
        'git diff --name-only "$source_c0_commit" "$source_commit"',
        'test "${#c0_to_c1_paths[@]}" -eq 1',
        "test \"${c0_to_c1_paths[0]}\" = 'configs/fresh-confirmatory-seed-commitment.json'",
        'git diff --name-only "$source_commit" "$GITHUB_SHA"',
        "tools/confirmatory-python311.lock",
        "--require-hashes --only-binary=:all:",
        'python-version: "3.11.16"',
        "preflight frozen C1 without model credentials",
        "Validate C0 and the subscription-only authorization before salt access",
        'test -z "${OPENROUTER_API_KEY:-}"',
        "--preflight-only",
        "fetch-depth: 0",
        "run_confirmatory_service_study.py",
        "finalize_confirmatory_c2.py",
        "Remove all gold-bearing and seed-bearing files before inference",
    ):
        if required not in workflow_source:
            raise ValueError(f"scored workflow lacks frozen safety boundary: {required}")
    if workflow_source.count("test \"$GITHUB_RUN_ATTEMPT\" = '1'") != 5:
        raise ValueError("not every scored workflow job rejects a GitHub rerun")
    if workflow_source.count('python-version: "3.11.16"') != 5:
        raise ValueError("not every scored workflow job pins exact CPython 3.11.16")
    model_secret = "${{ secrets.OPENCODE_GO_API_KEY }}"
    if (
        workflow_source.count(model_secret) != 1
        or "secrets.OPENROUTER_API_KEY" in workflow_source
        or workflow_source.index(model_secret)
        < workflow_source.index("needs: [prepare, preflight]")
    ):
        raise ValueError("model credential is not isolated behind the credential-free preflight")
    freeze_source = (ROOT / ".github/workflows/confirmatory-hidden-freeze.yml").read_text(
        encoding="utf-8"
    )
    if (
        "CPB_V1_HIDDEN_SEED" in freeze_source
        or model_secret in freeze_source
        or "secrets.OPENROUTER_API_KEY" in freeze_source
        or "--prior-dataset" in freeze_source
        or "--prior-prompt-manifest configs/prior-hidden-prompt-hash-denylist-r6.json"
        not in freeze_source
        or freeze_source.count("--prior-commitment") != 3
        or "Prove only the public r6 salt commitment differs from C0" not in freeze_source
        or 'git diff --name-only "$source_c0_commit" "$GITHUB_SHA"' not in freeze_source
        or "tools/confirmatory-python311.lock" not in freeze_source
        or "--require-hashes --only-binary=:all:" not in freeze_source
        or 'python-version: "3.11.16"' not in freeze_source
        or "pip install -e" in freeze_source
        or "pip install -e" in workflow_source
    ):
        raise ValueError("C1 freeze source, lock, or prior-prompt boundary changed")
    if freeze_source.count('python-version: "3.11.16"') != 1:
        raise ValueError("C1 freeze does not pin exact CPython 3.11.16")
    workflow_sources = workflow_source + freeze_source
    invoked_scripts = set(re.findall(r"scripts/[A-Za-z0-9_.-]+\.py", workflow_sources))
    unbound_scripts = invoked_scripts - set(_HASH_BINDINGS.values())
    if unbound_scripts:
        raise ValueError(
            f"confirmatory workflow invokes unbound scripts: {sorted(unbound_scripts)}"
        )
    aliases = load_json(ROOT / "configs" / "confirmatory-workflow-dispatch-aliases.json")
    if (
        aliases.get("status") != "BYTE_IDENTICAL_DISPATCH_ALIASES_ONLY"
        or aliases.get("study_id") != plan.get("study_id")
        or aliases.get("c0_plan_sha256") != sha256_file(plan_path)
        or aliases.get("dispatch_alias_adds_protocol_semantics") is not False
        or aliases.get("prior_confirmatory_model_post_count") != 0
    ):
        raise ValueError("confirmatory dispatch-alias registry is not bound to C0")
    alias_rows = aliases.get("aliases")
    if not isinstance(alias_rows, list) or len(alias_rows) != 2:
        raise ValueError("confirmatory dispatch-alias registry is incomplete")
    expected_ids = {335467504, 335516192}
    observed_ids: set[int] = set()
    for row in alias_rows:
        canonical = ROOT / str(row.get("canonical_path"))
        alias = ROOT / str(row.get("dispatch_alias_path"))
        workflow_id = row.get("registered_workflow_id")
        if not isinstance(workflow_id, int):
            raise ValueError("confirmatory dispatch alias lacks a workflow ID")
        observed_ids.add(workflow_id)
        if (
            not canonical.is_file()
            or not alias.is_file()
            or canonical.read_bytes() != alias.read_bytes()
            or row.get("canonical_sha256") != sha256_file(canonical)
            or row.get("dispatch_alias_sha256") != sha256_file(alias)
        ):
            raise ValueError("confirmatory dispatch alias differs from its canonical workflow")
    if observed_ids != expected_ids:
        raise ValueError("confirmatory dispatch-alias workflow IDs changed")
    seed_status = "NOT_REQUIRED_FOR_PRE_SALT_C0"
    seed_path = ROOT / str(plan["seed"]["commitment_path"])
    if require_seed_commitment or seed_path.exists():
        if not seed_path.is_file():
            raise ValueError("required C0 seed commitment is absent")
        seed = load_json(seed_path)
        if seed.get("preregistration_sha256") != sha256_file(plan_path):
            raise ValueError("seed commitment is not bound to the exact C0 plan")
        if not _DIGEST.fullmatch(str(seed.get("private_salt_sha256", ""))):
            raise ValueError("seed commitment salt digest is malformed")
        drand = seed.get("drand")
        if not isinstance(drand, dict) or drand.get("chain_hash") != (
            "52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971"
        ):
            raise ValueError("seed commitment does not pin quicknet")
        if not isinstance(drand.get("round"), int) or int(drand["round"]) < 1:
            raise ValueError("seed commitment drand round is malformed")
        source_c0_commit = str(seed.get("source_c0_commit", ""))
        if not re.fullmatch(r"[0-9a-f]{40}", source_c0_commit):
            raise ValueError("seed commitment lacks the exact C0 source commit")
        frozen_plan = subprocess.run(
            ["git", "show", f"{source_c0_commit}:v2/fresh-confirmatory-study-plan.json"],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        if frozen_plan.returncode != 0 or frozen_plan.stdout != plan_path.read_bytes():
            raise ValueError("seed commitment C0 commit does not contain the exact plan")
        seed_status = "PUBLIC_SALT_HASH_AND_FUTURE_BEACON_BOUND"
    return {
        "status": "C0_PASS",
        "study_id": plan["study_id"],
        "plan_sha256": sha256_file(plan_path),
        "registered_hashes": len(_HASH_BINDINGS),
        "formal_lanes": len(plan["formal_lanes"]),
        "pilot_instances": plan["pilot"]["instances"],
        "hypotheses": len(statistics["hypotheses"]),
        "planned_cells": plan["design"]["planned_model_item_cells"],
        "subscription_authorization": authorization["status"],
        "seed_status": seed_status,
        "go_status": plan["go_gate"]["status"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plan", type=Path, default=ROOT / "v2" / "fresh-confirmatory-study-plan.json"
    )
    parser.add_argument("--require-seed-commitment", action="store_true")
    args = parser.parse_args()
    report = validate_c0(args.plan.resolve(), args.require_seed_commitment)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
