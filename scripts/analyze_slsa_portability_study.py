#!/usr/bin/env python3
"""Derive registered failure-aware metrics for the SLSA portability study."""

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
from validate_slsa_portability_freeze import validate_freeze  # noqa: E402

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"slsa-portability-analysis: {message}")


def baseline_records(predictions: list[Json]) -> list[Json]:
    return [
        {
            "item_id": row["item_id"],
            "pair_id": row["pair_id"],
            "parse_status": "OK",
            "raw_decision": {"action": row["predicted_action"]},
        }
        for row in predictions
    ]


def analyze(
    plan_path: Path,
    schedule_path: Path,
    dataset_root: Path,
    baseline_root: Path,
    run_paths: list[Path],
) -> Json:
    validate_freeze(plan_path, schedule_path, dataset_root, baseline_root)
    plan = load_json(plan_path)
    gold = load_jsonl(dataset_root / "evaluation-gold.jsonl")
    pairs = load_json(dataset_root / "evaluation-pairs.json")
    if not isinstance(pairs, list):
        fail("evaluation pairs must be a list")
    packet = load_json(dataset_root / "evaluation-prompt-packet.json")
    expected_ids = {str(row["id"]) for row in gold}
    planned_lanes = {str(row["lane_id"]): row for row in plan["formal_lanes"]}
    seen_lanes: set[str] = set()
    frozen_commits: set[str] = set()
    lanes: list[Json] = []
    for run_path in run_paths:
        records = load_jsonl(run_path)
        if len(records) != 120 or {str(row["item_id"]) for row in records} != expected_ids:
            fail(f"run does not cover the frozen evaluation set: {run_path}")
        lane_values = {str(row["lane_id"]) for row in records}
        if len(lane_values) != 1:
            fail(f"run contains multiple lane IDs: {run_path}")
        lane_id = next(iter(lane_values))
        if lane_id not in planned_lanes or lane_id in seen_lanes:
            fail(f"unexpected or duplicate lane: {lane_id}")
        seen_lanes.add(lane_id)
        if any(row["packet_sha256"] != packet["packet_sha256"] for row in records):
            fail(f"run packet hash differs: {lane_id}")
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
                "run_sha256": sha256_file(run_path),
                "host_usage_derived_quota_value_usd": (
                    sum(quota_values) if len(quota_values) == len(records) else None
                ),
                "metrics": metrics,
            }
        )
    if seen_lanes != set(planned_lanes):
        fail("run lanes differ from the frozen plan")
    if len(frozen_commits) != 1:
        fail("run records do not share one frozen-plan commit")

    predictions = load_jsonl(baseline_root / "predictions.jsonl")
    baseline_metrics = derive_reporting_metrics(gold, pairs, baseline_records(predictions))
    return {
        "schema_version": "1.0.0",
        "status": "COMPLETE",
        "truth_status": "COMPUTATIONAL",
        "study_id": plan["study_id"],
        "design": "PROSPECTIVELY_FROZEN_SECOND_POLICY_PORTABILITY_STUDY",
        "interpretation": (
            "The study tests the same conformance protocol on an author operationalization of "
            "SLSA and in-toto evidence fields. It is not a SLSA certification, external policy "
            "consensus, natural-distribution estimate, or causal model comparison."
        ),
        "freeze": {
            "frozen_plan_commit": next(iter(frozen_commits)),
            "plan_sha256": sha256_file(plan_path),
            "schedule_sha256": load_json(schedule_path)["schedule_sha256"],
            "dataset_fingerprint": load_json(dataset_root / "manifest.json")["dataset_fingerprint"],
            "packet_sha256": packet["packet_sha256"],
        },
        "lanes": sorted(lanes, key=lambda row: str(row["lane_id"])),
        "structured_random_forest_action_baseline": {
            "report_sha256": sha256_file(baseline_root / "report.json"),
            "predictions_sha256": sha256_file(baseline_root / "predictions.jsonl"),
            "scope": "ACTION_ONLY_POLICY_BLIND_STRUCTURED_CLASSIFIER",
            "metrics": baseline_metrics,
        },
        "deterministic_policy_executor": {
            "items": 120,
            "pairs": 60,
            "end_to_end_item_accuracy": 1.0,
            "end_to_end_pair_accuracy": 1.0,
            "label": "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_BASELINE",
        },
        "failure_rule": (
            "Every service, syntax, schema, and semantic failure remains in the scheduled "
            "end-to-end denominator."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(
        args.plan.resolve(),
        args.schedule.resolve(),
        args.dataset_root.resolve(),
        args.baseline_root.resolve(),
        [path.resolve() for path in args.run],
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(canonical_json({"status": result["status"], "lanes": len(result["lanes"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
