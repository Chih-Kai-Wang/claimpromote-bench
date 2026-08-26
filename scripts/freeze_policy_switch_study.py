#!/usr/bin/env python3
"""Freeze the counterfactual policy-profile study before scored inference."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from freeze_slsa_portability_study import request_body  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
DECISION_SCHEMA = ROOT / "v2" / "schemas" / "slsa-agent-decision.schema.json"
BASE_POLICY_PATH = ROOT / "v2" / "slsa-portability-v1" / "policy-contract.json"
SWITCH_POLICY_PATH = ROOT / "v2" / "policy-switch-v1" / "policy-contract.json"
SOURCE_REGISTRY = ROOT / "v2" / "slsa-portability-v1" / "source-registry.json"
BASELINE_REQUIREMENTS = ROOT / "v2" / "slsa-portability-v1" / "requirements-baseline.txt"

RUNTIME_SOURCES = (
    "scripts/analyze_balanced_public_challenge.py",
    "scripts/analyze_policy_switch_study.py",
    "scripts/analyze_stronger_model_study.py",
    "scripts/build_policy_switch_study.py",
    "scripts/build_public_model_breadth_study.py",
    "scripts/freeze_policy_switch_study.py",
    "scripts/freeze_slsa_portability_study.py",
    "scripts/policy_switch.py",
    "scripts/run_policy_switch_study.py",
    "scripts/run_public_model_breadth_study.py",
    "scripts/run_slsa_portability_study.py",
    "scripts/run_stronger_model_study.py",
    "scripts/slsa_policy.py",
    "scripts/train_policy_switch_baselines.py",
    "scripts/validate_policy_switch_study.py",
    "src/claimpromotebench/dataset.py",
    "src/claimpromotebench/decision_validation.py",
    "src/claimpromotebench/hashing.py",
    "v2/policy-switch-v1/policy-contract.json",
    "v2/schemas/slsa-agent-decision.schema.json",
    "v2/schemas/stronger-model-run-record.schema.json",
    "v2/slsa-portability-v1/policy-contract.json",
    "v2/slsa-portability-v1/requirements-baseline.txt",
)


def fail(message: str) -> None:
    raise SystemExit(f"policy-switch-freeze: {message}")


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


def formal_lanes() -> list[Json]:
    return [
        {
            "lane_id": "opencode-go-qwen3.7-max-policy-switch-v1",
            "repeated_configuration": "opencode-go-qwen3.7-max",
            "provider": "OpenCode Go",
            "api_kind": "anthropic_messages",
            "base_url": "https://opencode.ai/zen/go/v1",
            "model": "qwen3.7-max",
            "model_family": "Qwen",
            "auth_env": "OPENCODE_GO_API_KEY",
            "response_format": "prompt_only_json",
            "allow_single_json_object_extraction": True,
            "max_output_tokens": 1536,
            "input_usd_per_million": 2.5,
            "cached_input_usd_per_million": 0.5,
            "output_usd_per_million": 7.5,
            "billing_mode": "PREEXISTING_SUBSCRIPTION_INCLUDED_QUOTA",
        },
        {
            "lane_id": "opencode-go-deepseek-v4-flash-policy-switch-v1",
            "repeated_configuration": "opencode-go-deepseek-v4-flash-matched",
            "provider": "OpenCode Go",
            "api_kind": "openai_compatible",
            "base_url": "https://opencode.ai/zen/go/v1",
            "model": "deepseek-v4-flash",
            "model_family": "DeepSeek",
            "auth_env": "OPENCODE_GO_API_KEY",
            "response_format": "json_schema",
            "allow_single_json_object_extraction": True,
            "max_output_tokens": 1536,
            "input_usd_per_million": 0.44,
            "cached_input_usd_per_million": 0.014,
            "output_usd_per_million": 1.32,
            "billing_mode": "PREEXISTING_SUBSCRIPTION_INCLUDED_QUOTA",
        },
    ]


def build_schedule(plan: Json, packet: Json) -> Json:
    lane_ids = [str(value) for value in plan["execution"]["base_lane_order"]]
    lanes = {str(lane["lane_id"]): lane for lane in plan["formal_lanes"]}
    records = sorted(packet["records"], key=lambda row: str(row["item_id"]))
    if len(records) != 120 or lane_ids != list(lanes):
        fail("packet coverage or lane order differs")
    cells: list[Json] = []
    for item_index, record in enumerate(records):
        rotation = item_index % len(lane_ids)
        for lane_id in lane_ids[rotation:] + lane_ids[:rotation]:
            body = request_body(lanes[lane_id], str(record["prompt"]))
            cells.append(
                {
                    "sequence": len(cells),
                    "item_index": item_index,
                    "cell_id": f"{lane_id}/{record['item_id']}",
                    "lane_id": lane_id,
                    "item_id": record["item_id"],
                    "pair_id": record["pair_id"],
                    "prompt_sha256": record["prompt_sha256"],
                    "request_body_sha256": sha256_bytes(canonical_json(body).encode("utf-8")),
                }
            )
    schedule: Json = {
        "schema_version": "1.0.0",
        "study_id": plan["study_id"],
        "status": "FROZEN_BEFORE_SCORED_INFERENCE",
        "contains_prompts": False,
        "contains_gold": False,
        "contains_credentials": False,
        "packet_sha256": packet["packet_sha256"],
        "dataset_fingerprint": packet["dataset_fingerprint"],
        "base_lane_order": lane_ids,
        "order_rule": "ITEM_MAJOR_WITH_CYCLIC_LANE_ROTATION",
        "planned_items": 120,
        "planned_lanes": 2,
        "planned_cells": len(cells),
        "application_posts_per_cell": 1,
        "client_retry_count": 0,
        "cells": cells,
    }
    schedule["schedule_sha256"] = sha256_bytes(canonical_json(schedule).encode("utf-8"))
    return schedule


def freeze(
    dataset_root: Path,
    baseline_root: Path,
    catalog_path: Path,
    source_receipt_path: Path,
    plan_path: Path,
    schedule_path: Path,
) -> Json:
    if plan_path.exists() or schedule_path.exists():
        fail("refusing to overwrite a study plan or request schedule")
    manifest = load_object(dataset_root / "manifest.json")
    packet = load_object(dataset_root / "evaluation-prompt-packet.json")
    baseline = load_object(baseline_root / "report.json")
    catalog = load_object(catalog_path)
    source_receipt = load_object(source_receipt_path)
    if manifest.get("study_id") != packet.get("study_id"):
        fail("dataset manifest and prompt packet study IDs differ")
    if source_receipt.get("upstream_sources_verified") is not True:
        fail("source receipt did not verify upstream source bytes")
    if catalog.get("selected_model_ids") != ["qwen3.7-max", "deepseek-v4-flash"]:
        fail("catalog does not contain the repeated configurations")
    if baseline.get("evaluation_gold_loaded") is not False:
        fail("baseline accessed evaluation labels")
    lanes = formal_lanes()
    plan: Json = {
        "schema_version": "1.0.0",
        "study_id": manifest["study_id"],
        "status": "FROZEN_BEFORE_SCORED_INFERENCE",
        "truth_status": "SEALED_UNTIL_ALL_TERMINAL_RECORDS_EXIST",
        "frozen_at_utc": utc_now(),
        "purpose": (
            "Test whether model-mediated routes change actions when the applicable published "
            "policy profile changes while evidence and states remain fixed."
        ),
        "interpretation_boundary": manifest["interpretation_boundary"],
        "design": {
            "controlled_path": "/active_policy_profile",
            "development_pairs": 36,
            "development_items": 72,
            "evaluation_pairs": 60,
            "evaluation_items": 120,
            "evaluation_factors": 12,
            "evaluation_action_support": {
                "ALLOW": 60,
                "HOLD": 20,
                "DEMOTE": 20,
                "ESCALATE": 20,
            },
            "evaluation_profile_support": {"POLICY_BLUE": 60, "POLICY_AMBER": 60},
            "planned_lanes": 2,
            "planned_model_item_cells": 240,
            "attempts_per_cell": 1,
            "selection_uses_new_study_outputs": False,
            "naturalistic_case_count": 0,
        },
        "sources": {
            "registry_path": repo_relative(SOURCE_REGISTRY),
            "registry_sha256": sha256_file(SOURCE_REGISTRY),
            "validation_receipt_path": repo_relative(source_receipt_path),
            "validation_receipt_sha256": sha256_file(source_receipt_path),
            "base_policy_path": repo_relative(BASE_POLICY_PATH),
            "base_policy_sha256": sha256_file(BASE_POLICY_PATH),
            "switch_policy_path": repo_relative(SWITCH_POLICY_PATH),
            "switch_policy_sha256": sha256_file(SWITCH_POLICY_PATH),
            "external_requirements_author_labels_separated": True,
        },
        "dataset": {
            "root": repo_relative(dataset_root),
            "manifest_file_sha256": sha256_file(dataset_root / "manifest.json"),
            "dataset_fingerprint": manifest["dataset_fingerprint"],
            "pair_contract": manifest["pair_contract"],
            "private_git_freeze_before_inference": True,
            "public_before_inference": False,
        },
        "prompt": {
            "path": repo_relative(dataset_root / "evaluation-prompt-packet.json"),
            "packet_sha256": packet["packet_sha256"],
            "packet_file_sha256": sha256_file(dataset_root / "evaluation-prompt-packet.json"),
            "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
            "complete_decision_schema_visible_to_every_lane": True,
            "numeric_probability_type_visible_to_every_lane": True,
            "same_prompt_bytes_for_every_lane": True,
        },
        "catalog": {
            "path": repo_relative(catalog_path),
            "file_sha256": sha256_file(catalog_path),
            "selected_model_ids": catalog["selected_model_ids"],
            "selected_before_new_study_outputs": True,
        },
        "baselines": {
            "root": repo_relative(baseline_root),
            "requirements_path": repo_relative(BASELINE_REQUIREMENTS),
            "requirements_sha256": sha256_file(BASELINE_REQUIREMENTS),
            "report_sha256": sha256_file(baseline_root / "report.json"),
            "algorithm": baseline["algorithm"],
            "configuration": baseline["configuration"],
            "evaluation_gold_loaded": baseline["evaluation_gold_loaded"],
            "model_outputs_loaded": baseline["model_outputs_loaded"],
            "comparators": baseline["comparators"],
        },
        "execution": {
            "base_lane_order": [str(lane["lane_id"]) for lane in lanes],
            "order_rule": "ITEM_MAJOR_WITH_CYCLIC_LANE_ROTATION",
            "planned_application_posts": 240,
            "application_posts_per_cell": 1,
            "client_retry_count": 0,
            "partial_resume": "FORBIDDEN",
            "minimum_global_request_interval_seconds": 0.75,
            "timeout_seconds": 180,
            "quota_error_rule": "TERMINAL_ERROR_RETAINED_IN_END_TO_END_DENOMINATOR",
            "interruption_rule": "INCOMPLETE_STUDY_INELIGIBLE_FOR_MANUSCRIPT_NO_RESUME",
        },
        "formal_lanes": lanes,
        "budget": {
            "authorization_scope": "USER_AUTHORIZED_CURRENT_AVAILABLE_OPENCODE_GO_QUOTA",
            "incremental_cash_cap_usd": 0.0,
            "subscription_quota_only": True,
            "workflow_initiated_purchase_or_recharge": False,
            "adaptive_stop_on_usage_or_results": False,
        },
        "statistics": {
            "primary_endpoints": [
                "end_to_end_policy_switch_pair_accuracy",
                "end_to_end_item_accuracy",
            ],
            "secondary_endpoints": [
                "decision_coverage",
                "pair_coverage",
                "conditional_item_accuracy",
                "conditional_pair_accuracy",
                "per_action_recall",
                "balanced_action_recall",
                "macro_f1",
            ],
            "failure_rule": (
                "Every service, syntax, schema, semantic, quota, and adapter failure remains "
                "incorrect in the scheduled end-to-end denominator."
            ),
            "pair_rule": (
                "A switch pair is correct only when both policy-profile members are valid and "
                "action-correct."
            ),
            "within_lane_identification": (
                "Within each lane, pair members differ only in active_policy_profile. Pair "
                "correctness therefore tests sensitivity to the published policy switch on the "
                "frozen corpus."
            ),
            "between_lane_boundary": (
                "Model, service adapter, and output-constraining mode differ between lanes; "
                "between-lane differences are descriptive."
            ),
        },
        "promotion_rule": "Only all 240 sealed terminal outcomes may enter the manuscript.",
        "runtime_source_sha256": {path: sha256_file(ROOT / path) for path in RUNTIME_SOURCES},
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
    parser.add_argument("--source-receipt", type=Path, required=True)
    parser.add_argument("--plan-out", type=Path, required=True)
    parser.add_argument("--schedule-out", type=Path, required=True)
    args = parser.parse_args()
    plan = freeze(
        args.dataset_root.resolve(),
        args.baseline_root.resolve(),
        args.catalog.resolve(),
        args.source_receipt.resolve(),
        args.plan_out.resolve(),
        args.schedule_out.resolve(),
    )
    print(
        canonical_json(
            {
                "status": plan["status"],
                "study_id": plan["study_id"],
                "planned_cells": plan["design"]["planned_model_item_cells"],
                "dataset_fingerprint": plan["dataset"]["dataset_fingerprint"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
