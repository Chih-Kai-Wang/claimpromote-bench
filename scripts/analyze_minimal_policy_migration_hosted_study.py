#!/usr/bin/env python3
"""Derive frozen metrics for the hosted minimum policy-migration smoke study."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_balanced_public_challenge import derive_reporting_metrics  # noqa: E402
from freeze_minimal_policy_migration_hosted_study import MINIMAL_SUITE_PATH  # noqa: E402
from validate_minimal_policy_migration_hosted_study import validate_freeze  # noqa: E402

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"minimal-policy-migration-hosted-analysis: {message}")


def selected_evaluation(dataset_root: Path) -> tuple[list[Json], list[Json], set[str]]:
    suite = load_json(MINIMAL_SUITE_PATH)
    selected_ids = {str(value) for value in suite["selected_item_ids"]}
    selected_pair_ids = {str(value) for value in suite["selected_pair_ids"]}
    gold = [
        row
        for row in load_jsonl(dataset_root / "evaluation-gold.jsonl")
        if str(row["id"]) in selected_ids
    ]
    pairs_value = load_json(dataset_root / "evaluation-pairs.json")
    if not isinstance(pairs_value, list):
        fail("evaluation pairs must be a list")
    pairs = [row for row in pairs_value if str(row["pair_id"]) in selected_pair_ids]
    if (
        len(gold) != 20
        or len(pairs) != 10
        or {str(row["id"]) for row in gold} != selected_ids
        or {str(row["pair_id"]) for row in pairs} != selected_pair_ids
    ):
        fail("selected gold or pair coverage differs from the frozen minimum suite")
    return gold, pairs, selected_ids


def baseline_records(predictions: list[Json], selected_ids: set[str]) -> list[Json]:
    rows = [row for row in predictions if str(row["item_id"]) in selected_ids]
    if len(rows) != 20:
        fail("baseline does not cover the frozen minimum suite")
    return [
        {
            "item_id": row["item_id"],
            "pair_id": row["pair_id"],
            "parse_status": "OK",
            "raw_decision": {"action": row["predicted_action"]},
        }
        for row in rows
    ]


def analyze(
    plan_path: Path,
    schedule_path: Path,
    dataset_root: Path,
    baseline_root: Path,
    execution_receipt_path: Path,
    run_paths: list[Path],
) -> Json:
    validate_freeze(plan_path, schedule_path, dataset_root, baseline_root)
    plan = load_json(plan_path)
    receipt = load_json(execution_receipt_path)
    if (
        receipt.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or receipt.get("planned_cells") != 40
        or receipt.get("durable_terminal_records") != 40
        or receipt.get("client_retry_count") != 0
        or receipt.get("partial_resume_used") is not False
        or receipt.get("study_id") != plan.get("study_id")
    ):
        fail("execution receipt does not seal all 40 zero-retry cells")

    gold, pairs, selected_ids = selected_evaluation(dataset_root)
    packet = load_json(dataset_root / "evaluation-prompt-packet.json")
    planned_lanes = {str(row["lane_id"]): row for row in plan["formal_lanes"]}
    receipt_hashes = receipt.get("lane_output_sha256")
    if not isinstance(receipt_hashes, dict):
        fail("execution receipt lacks lane-output hashes")
    seen_lanes: set[str] = set()
    frozen_commits: set[str] = set()
    lanes: list[Json] = []
    for run_path in run_paths:
        records = load_jsonl(run_path)
        if len(records) != 20 or {str(row["item_id"]) for row in records} != selected_ids:
            fail(f"run does not cover the frozen minimum suite: {run_path}")
        lane_values = {str(row["lane_id"]) for row in records}
        if len(lane_values) != 1:
            fail(f"run contains multiple lane IDs: {run_path}")
        lane_id = next(iter(lane_values))
        if lane_id not in planned_lanes or lane_id in seen_lanes:
            fail(f"unexpected or duplicate lane: {lane_id}")
        seen_lanes.add(lane_id)
        run_hash = sha256_file(run_path)
        if receipt_hashes.get(run_path.name) != run_hash:
            fail(f"run digest differs from execution receipt: {lane_id}")
        if any(row["packet_sha256"] != packet["packet_sha256"] for row in records):
            fail(f"run packet digest differs: {lane_id}")
        frozen_commits.update(str(row["frozen_plan_commit"]) for row in records)
        quota_values = [
            float(row["actual_cost_usd"])
            for row in records
            if isinstance(row.get("actual_cost_usd"), (int, float))
        ]
        metrics = derive_reporting_metrics(gold, pairs, records)
        lane = planned_lanes[lane_id]
        lanes.append(
            {
                "lane_id": lane_id,
                "repeated_configuration": lane["repeated_configuration"],
                "provider": lane["provider"],
                "model_requested": lane["model"],
                "run_sha256": run_hash,
                "host_usage_derived_quota_value_usd": (
                    sum(quota_values) if len(quota_values) == len(records) else None
                ),
                "strict_smoke_gate_pass": (
                    metrics["parseable_items"] == 20
                    and metrics["correct_items"] == 20
                    and metrics["correct_pairs"] == 10
                ),
                "metrics": metrics,
            }
        )
    if seen_lanes != set(planned_lanes):
        fail("run lanes differ from the frozen plan")
    if len(frozen_commits) != 1 or next(iter(frozen_commits)) != receipt.get("frozen_plan_commit"):
        fail("run records and execution receipt do not share one frozen commit")

    comparator_metrics: Json = {}
    for comparator_id in ("policy_aware", "profile_blind"):
        predictions_path = baseline_root / f"{comparator_id}-predictions.jsonl"
        records = baseline_records(load_jsonl(predictions_path), selected_ids)
        metrics = derive_reporting_metrics(gold, pairs, records)
        comparator_metrics[comparator_id] = {
            "scope": (
                "STRUCTURED_CLASSIFIER_WITH_ACTIVE_PROFILE"
                if comparator_id == "policy_aware"
                else "FEATURE_ABLATED_CLASSIFIER_WITHOUT_ACTIVE_PROFILE"
            ),
            "full_prediction_file_sha256": sha256_file(predictions_path),
            "strict_smoke_gate_pass": (
                metrics["correct_items"] == 20 and metrics["correct_pairs"] == 10
            ),
            "metrics": metrics,
        }
    return {
        "schema_version": "1.0.0",
        "status": "COMPLETE",
        "truth_status": "COMPUTATIONAL",
        "study_id": plan["study_id"],
        "design": "PROSPECTIVELY_FROZEN_MINIMUM_GRAPH_AND_RULE_COMPLETE_SMOKE_STUDY",
        "interpretation": (
            "The twenty selected items preserve all ten reachable action edges and all twelve "
            "authored policy-difference rules. One context per edge makes this an operational "
            "smoke gate, not an estimate of stochastic route reliability or generalization."
        ),
        "freeze": {
            "frozen_plan_commit": next(iter(frozen_commits)),
            "plan_sha256": sha256_file(plan_path),
            "schedule_sha256": load_json(schedule_path)["schedule_sha256"],
            "dataset_fingerprint": load_json(dataset_root / "manifest.json")["dataset_fingerprint"],
            "packet_sha256": packet["packet_sha256"],
            "minimum_suite_sha256": sha256_file(MINIMAL_SUITE_PATH),
            "execution_receipt_sha256": sha256_file(execution_receipt_path),
        },
        "adequacy": {
            "selected_items": 20,
            "selected_pairs": 10,
            "reachable_edges_covered": 10,
            "authored_policy_difference_rules_covered": 12,
            "source_diagnostic_items": 120,
            "item_call_reduction_fraction": 5 / 6,
        },
        "lanes": sorted(lanes, key=lambda row: str(row["lane_id"])),
        "structured_random_forest_comparators": comparator_metrics,
        "deterministic_policy_executor": {
            "items": 20,
            "pairs": 10,
            "end_to_end_item_accuracy": 1.0,
            "end_to_end_pair_accuracy": 1.0,
            "strict_smoke_gate_pass": True,
            "label": "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_BASELINE",
        },
        "failure_rule": (
            "Every service, syntax, schema, semantic, quota, and adapter failure remains in the "
            "scheduled end-to-end denominator."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--execution-receipt", type=Path, required=True)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(
        args.plan.resolve(),
        args.schedule.resolve(),
        args.dataset_root.resolve(),
        args.baseline_root.resolve(),
        args.execution_receipt.resolve(),
        [path.resolve() for path in args.run],
    )
    if args.out.exists():
        fail("refusing to overwrite an aggregate")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(canonical_json({"status": result["status"], "lanes": len(result["lanes"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
