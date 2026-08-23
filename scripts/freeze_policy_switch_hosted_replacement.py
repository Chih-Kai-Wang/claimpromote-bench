#!/usr/bin/env python3
"""Freeze a fresh hosted replacement for the quota-confounded policy-switch run."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from freeze_policy_switch_study import build_schedule  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
STUDY_ID = "claimpromotebench-policy-profile-switch-hosted-replacement-2026-08-v2"
SOURCE_PLAN = ROOT / "v2" / "policy-switch-v1" / "frozen" / "study-plan.json"
SOURCE_EXCLUSION = (
    ROOT / "v2" / "policy-switch-v1" / "frozen" / "results" / "manuscript-exclusion-receipt.json"
)
LOCAL_POLICY_ROOT = (
    ROOT / "v2" / "local-model-replication-v1" / "replacement-v2" / "frozen" / "policy-switch"
)
RUNTIME_SOURCES = (
    "scripts/analyze_balanced_public_challenge.py",
    "scripts/analyze_policy_switch_hosted_replacement.py",
    "scripts/analyze_policy_switch_study.py",
    "scripts/build_policy_switch_study.py",
    "scripts/derive_policy_switch_hosted_replacement_eligibility.py",
    "scripts/finalize_synthetic_policy_results.py",
    "scripts/freeze_policy_switch_hosted_replacement.py",
    "scripts/freeze_policy_switch_study.py",
    "scripts/freeze_slsa_portability_study.py",
    "scripts/policy_switch.py",
    "scripts/run_policy_switch_hosted_replacement.py",
    "scripts/run_policy_switch_study.py",
    "scripts/run_public_model_breadth_study.py",
    "scripts/run_slsa_portability_study.py",
    "scripts/run_stronger_model_study.py",
    "scripts/slsa_policy.py",
    "scripts/validate_policy_switch_hosted_replacement.py",
    "scripts/validate_policy_switch_study.py",
    "src/claimpromotebench/dataset.py",
    "src/claimpromotebench/decision_validation.py",
    "src/claimpromotebench/hashing.py",
    "v2/policy-switch-v1/policy-contract.json",
    "v2/schemas/slsa-agent-decision.schema.json",
    "v2/schemas/stronger-model-run-record.schema.json",
    "v2/slsa-portability-v1/policy-contract.json",
)
EXPECTED_ROOT = ROOT / "v2" / "policy-switch-v1" / "hosted-replacement-v2"
RESOURCE_EXHAUSTION_RULE = (
    "Ordinary service, syntax, schema, semantic, adapter, and rate-limit failures remain "
    "incorrect in the complete end-to-end denominator. If a terminal provider error "
    "explicitly states that the shared subscription quota or usage allowance is exhausted, "
    "at least 20 scheduled cells remain, and every later cell is a transport failure, the "
    "complete hosted replacement is ineligible for model-efficacy reporting. In that case, "
    "retain only a redacted full-study exclusion receipt; never select a successful subset."
)


def fail(message: str) -> None:
    raise SystemExit(f"policy-switch-hosted-replacement-freeze: {message}")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        fail(f"path is outside the repository: {path}")


def replacement_lanes(source_plan: Json) -> list[Json]:
    lanes = deepcopy(source_plan["formal_lanes"])
    if [str(row.get("model")) for row in lanes] != ["qwen3.7-max", "deepseek-v4-flash"]:
        fail("predecessor model configurations changed")
    suffixes = ("qwen3.7-max", "deepseek-v4-flash")
    for lane, suffix in zip(lanes, suffixes, strict=True):
        lane["lane_id"] = f"opencode-go-{suffix}-policy-switch-hosted-replacement-v2"
    return lanes


def make_selection_audit(
    *,
    source_plan: Json,
    exclusion: Json,
    catalog: Json,
    dataset_root: Path,
    replacement_root: Path,
) -> Json:
    local_journal = LOCAL_POLICY_ROOT / "journal" / "terminal-records.jsonl"
    local_results = LOCAL_POLICY_ROOT / "results" / "aggregate.json"
    if local_journal.exists() or local_results.exists():
        fail("local policy-switch outcomes already exist; replacement selection is no longer clean")
    replacement_journal = replacement_root / "journal" / "terminal-records.jsonl"
    replacement_results = replacement_root / "results" / "aggregate.json"
    if replacement_journal.exists() or replacement_results.exists():
        fail("hosted replacement outcomes already exist")
    audit: Json = {
        "schema_version": "1.0.0",
        "status": "HOSTED_RESOURCE_FAILURE_REPLACEMENT_SELECTED_BEFORE_NEW_OUTCOMES",
        "recorded_at_utc": utc_now(),
        "replacement_study_id": STUDY_ID,
        "predecessor_study_id": source_plan["study_id"],
        "predecessor_outputs_available_and_inspected": True,
        "predecessor_exclusion_status": exclusion["status"],
        "selection_reason": (
            "Repeat the unchanged complete hosted protocol after the user replenished the shared "
            "subscription allowance; the predecessor was excluded in full because quota failures "
            "persisted through the end of its frozen schedule."
        ),
        "changes_permitted": [
            "new study and lane identifiers",
            "new freeze timestamp and Git commit",
            "new request schedule hashes induced only by new lane identifiers",
            "fresh authenticated model-catalog snapshot",
        ],
        "changes_forbidden": [
            "dataset items, gold labels, pairs, or prompts",
            "models, adapters, output contracts, decoding, or request limit",
            "primary or secondary endpoints",
            "zero-retry and end-to-end denominator rules",
            "adaptive stopping or successful-subset selection",
        ],
        "source_dataset_fingerprint": load_object(dataset_root / "manifest.json")[
            "dataset_fingerprint"
        ],
        "source_packet_sha256": load_object(dataset_root / "evaluation-prompt-packet.json")[
            "packet_sha256"
        ],
        "catalog_selected_model_ids": catalog["selected_model_ids"],
        "new_replacement_terminal_records_before_freeze": 0,
        "local_policy_switch_terminal_records_before_freeze": 0,
        "new_model_calls_for_selection": 0,
        "resource_exhaustion_rule": RESOURCE_EXHAUSTION_RULE,
    }
    audit["self_digest"] = sha256_bytes(canonical_json(audit).encode("utf-8"))
    return audit


def freeze(
    *,
    dataset_root: Path,
    baseline_root: Path,
    catalog_path: Path,
    plan_path: Path,
    schedule_path: Path,
    selection_audit_path: Path,
) -> Json:
    targets = (plan_path, schedule_path, selection_audit_path)
    if any(path.exists() for path in targets):
        fail("refusing to overwrite a plan, schedule, or selection audit")
    if (
        plan_path.parent != EXPECTED_ROOT
        or schedule_path.parent != EXPECTED_ROOT
        or selection_audit_path.parent != EXPECTED_ROOT
        or catalog_path.parent != EXPECTED_ROOT
    ):
        fail("replacement freeze files must use the designated hosted-replacement-v2 root")
    source_plan = load_object(SOURCE_PLAN)
    exclusion = load_object(SOURCE_EXCLUSION)
    catalog = load_object(catalog_path)
    manifest = load_object(dataset_root / "manifest.json")
    packet = load_object(dataset_root / "evaluation-prompt-packet.json")
    if (
        source_plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE"
        or exclusion.get("status")
        != "HOSTED_POLICY_SWITCH_EXCLUDED_IN_FULL_SHARED_QUOTA_EXHAUSTION"
        or exclusion.get("decision", {}).get("hosted_model_rows_enter_manuscript") is not False
        or exclusion.get("decision", {}).get("successful_row_subset_selected") is not False
    ):
        fail("predecessor exclusion boundary changed")
    if catalog.get("selected_model_ids") != ["qwen3.7-max", "deepseek-v4-flash"]:
        fail("fresh catalog does not contain the repeated configurations")
    if catalog.get("recorded_at_utc") is None or catalog.get("credentials_retained") is not False:
        fail("fresh catalog is malformed")
    if manifest.get("study_id") != source_plan.get("study_id"):
        fail("source dataset and predecessor plan differ")
    if repo_relative(dataset_root) != source_plan.get("dataset", {}).get("root"):
        fail("replacement dataset root differs from the predecessor")
    if repo_relative(baseline_root) != source_plan.get("baselines", {}).get("root"):
        fail("replacement baseline root differs from the predecessor")
    if source_plan.get("baselines", {}).get("report_sha256") != sha256_file(
        baseline_root / "report.json"
    ):
        fail("replacement baseline report differs from the predecessor")

    audit = make_selection_audit(
        source_plan=source_plan,
        exclusion=exclusion,
        catalog=catalog,
        dataset_root=dataset_root,
        replacement_root=plan_path.parent,
    )
    selection_audit_path.parent.mkdir(parents=True, exist_ok=True)
    selection_audit_path.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lanes = replacement_lanes(source_plan)
    plan = deepcopy(source_plan)
    plan.update(
        {
            "study_id": STUDY_ID,
            "frozen_at_utc": utc_now(),
            "purpose": (
                "Run the unchanged complete hosted policy-profile protocol after the shared "
                "subscription allowance was replenished."
            ),
            "promotion_rule": (
                "Only all 240 replacement terminal outcomes may enter the manuscript. No "
                "successful subset or predecessor output is eligible. The prospectively "
                "specified shared-resource exhaustion rule may instead exclude the complete "
                "replacement from model-efficacy reporting."
            ),
            "formal_lanes": lanes,
            "runtime_source_sha256": {path: sha256_file(ROOT / path) for path in RUNTIME_SOURCES},
        }
    )
    plan["design"]["selection_uses_new_study_outputs"] = False
    plan["dataset"]["source_study_id"] = manifest["study_id"]
    plan["prompt"]["source_study_id"] = packet["study_id"]
    plan["catalog"] = {
        "path": repo_relative(catalog_path),
        "file_sha256": sha256_file(catalog_path),
        "selected_model_ids": catalog["selected_model_ids"],
        "selected_before_new_study_outputs": True,
    }
    plan["execution"].update(
        {
            "base_lane_order": [str(lane["lane_id"]) for lane in lanes],
            "partial_resume": "FORBIDDEN",
            "client_retry_count": 0,
            "planned_application_posts": 240,
            "resource_exhaustion_eligibility_rule": RESOURCE_EXHAUSTION_RULE,
        }
    )
    plan["replacement"] = {
        "kind": "RESOURCE_FAILURE_REPLACEMENT_WITH_UNCHANGED_PROTOCOL",
        "predecessor_plan_path": repo_relative(SOURCE_PLAN),
        "predecessor_plan_sha256": sha256_file(SOURCE_PLAN),
        "predecessor_exclusion_path": repo_relative(SOURCE_EXCLUSION),
        "predecessor_exclusion_sha256": sha256_file(SOURCE_EXCLUSION),
        "predecessor_outputs_eligible": False,
        "selection_audit_path": repo_relative(selection_audit_path),
        "selection_audit_sha256": sha256_file(selection_audit_path),
        "dataset_prompt_and_endpoint_protocol_unchanged": True,
        "prior_hosted_outputs_known_before_replacement": True,
        "local_policy_switch_outputs_known_before_replacement": False,
    }
    schedule = build_schedule(plan, packet)
    plan["execution"]["schedule_path"] = repo_relative(schedule_path)
    plan["execution"]["schedule_sha256"] = schedule["schedule_sha256"]
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    schedule_path.write_text(
        json.dumps(schedule, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--plan-out", type=Path, required=True)
    parser.add_argument("--schedule-out", type=Path, required=True)
    parser.add_argument("--selection-audit-out", type=Path, required=True)
    args = parser.parse_args()
    plan = freeze(
        dataset_root=args.dataset_root.resolve(),
        baseline_root=args.baseline_root.resolve(),
        catalog_path=args.catalog.resolve(),
        plan_path=args.plan_out.resolve(),
        schedule_path=args.schedule_out.resolve(),
        selection_audit_path=args.selection_audit_out.resolve(),
    )
    print(
        canonical_json(
            {
                "status": plan["status"],
                "study_id": plan["study_id"],
                "planned_cells": plan["design"]["planned_model_item_cells"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
