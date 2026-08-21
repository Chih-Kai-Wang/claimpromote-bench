#!/usr/bin/env python3
"""Validate every machine-checkable C0 boundary before the salt commitment."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from validate_stronger_model_study import validate_plan  # noqa: E402

from claimpromotebench.confirmatory_baseline import validate_model  # noqa: E402
from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import sha256_file  # noqa: E402

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
    "dataset.benchmark_plan_sha256": "configs/v1-benchmark-plan.json",
    "dataset.input_schema_sha256": "schemas/benchmark-input-v1.schema.json",
    "dataset.gold_schema_sha256": "schemas/gold-label.schema.json",
    "prompt.renderer_sha256": "src/claimpromotebench/prompts.py",
    "prompt.policy_sha256": "policies/math-evidence-transition-1.0.0.json",
    "prompt.decision_schema_sha256": "schemas/agent-decision.schema.json",
    "baselines.shallow_model_file_sha256": "v2/confirmatory/public-dev-text-nb-v1.json",
    "baselines.training_script_sha256": "scripts/train_confirmatory_shallow_baseline.py",
    "baselines.predictor_sha256": "scripts/predict_confirmatory_baselines.py",
    "baselines.feature_module_sha256": "src/claimpromotebench/confirmatory_baseline.py",
    "statistics.analysis_script_sha256": "scripts/analyze_confirmatory_hidden_study.py",
    "statistics.c2_finalizer_sha256": "scripts/finalize_confirmatory_c2.py",
    "statistics.power_analysis_script_sha256": "scripts/confirmatory_power_analysis.py",
    "statistics.power_assumptions_file_sha256": "v2/confirmatory/power-assumptions-r3.json",
    "statistics.power_analysis_report_file_sha256": "v2/confirmatory/power-analysis-r3.json",
    "workflows.c1_freeze_sha256": ".github/workflows/confirmatory-hidden-freeze.yml",
    "workflows.scored_study_sha256": ".github/workflows/confirmatory-hidden-study.yml",
    "implementation_sha256.dataset_builder": "scripts/build_v1_dataset.py",
    "implementation_sha256.formal_templates": "src/claimpromotebench/formal.py",
    "implementation_sha256.prompt_novelty_audit": "scripts/audit_hidden_prompt_novelty.py",
    "implementation_sha256.packet_builder": "scripts/build_stronger_model_packet.py",
    "implementation_sha256.c1_builder": "scripts/build_confirmatory_c1.py",
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
    runner_source = (ROOT / "scripts" / "run_confirmatory_service_study.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("postgate_decision", "gold.jsonl", 'add_argument("--dataset"'):
        if forbidden in runner_source:
            raise ValueError(f"gold-free worker contains forbidden dependency: {forbidden}")
    workflow_source = (ROOT / ".github/workflows/confirmatory-hidden-study.yml").read_text(
        encoding="utf-8"
    )
    for required in (
        "test \"$GITHUB_RUN_ATTEMPT\" = '1'",
        "run_confirmatory_service_study.py",
        "finalize_confirmatory_c2.py",
        "Remove all gold-bearing and seed-bearing files before inference",
    ):
        if required not in workflow_source:
            raise ValueError(f"scored workflow lacks frozen safety boundary: {required}")
    workflow_sources = workflow_source + (
        ROOT / ".github/workflows/confirmatory-hidden-freeze.yml"
    ).read_text(encoding="utf-8")
    invoked_scripts = set(re.findall(r"scripts/[A-Za-z0-9_.-]+\.py", workflow_sources))
    unbound_scripts = invoked_scripts - set(_HASH_BINDINGS.values())
    if unbound_scripts:
        raise ValueError(
            f"confirmatory workflow invokes unbound scripts: {sorted(unbound_scripts)}"
        )
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
