#!/usr/bin/env python3
"""Derive failure-aware metrics for one frozen local-model replacement study."""

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
from local_model_replication import CATALOG_PATH, DATASETS, VOID_RECEIPT_PATH  # noqa: E402
from validate_local_model_replications import validate_all  # noqa: E402

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"local-model-analysis: {message}")


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
    dataset_key: str,
    freeze_root: Path,
    catalog_path: Path,
    snapshot_path: Path,
    qualification_path: Path,
    void_receipt_path: Path,
    results_root: Path,
) -> Json:
    validate_all(
        freeze_root,
        catalog_path,
        snapshot_path,
        qualification_path,
        void_receipt_path,
    )
    spec = DATASETS[dataset_key]
    study_root = freeze_root / dataset_key
    plan_path = study_root / "study-plan.json"
    schedule_path = study_root / "request-schedule.json"
    plan = load_json(plan_path)
    schedule = load_json(schedule_path)
    execution_path = results_root / "execution-receipt.json"
    execution = load_json(execution_path)
    if (
        execution.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or execution.get("study_id") != plan.get("study_id")
        or execution.get("planned_cells") != 240
        or execution.get("durable_terminal_records") != 240
        or execution.get("client_retry_count") != 0
        or execution.get("partial_resume_used") is not False
        or execution.get("schedule_sha256") != schedule.get("schedule_sha256")
    ):
        fail("execution receipt does not seal all 240 local cells")

    dataset_root = Path(spec["dataset_root"])
    baseline_root = Path(spec["baseline_root"])
    gold = load_jsonl(dataset_root / "evaluation-gold.jsonl")
    pairs = load_json(dataset_root / "evaluation-pairs.json")
    packet = load_json(dataset_root / "evaluation-prompt-packet.json")
    if not isinstance(pairs, list):
        fail("evaluation pairs must be a list")
    expected_ids = {str(row["id"]) for row in gold}
    planned_lanes = {str(row["lane_id"]): row for row in plan["formal_lanes"]}
    receipt_hashes = execution.get("lane_output_sha256")
    if not isinstance(receipt_hashes, dict):
        fail("execution receipt lacks lane output hashes")
    seen_lanes: set[str] = set()
    frozen_commits: set[str] = set()
    lanes: list[Json] = []
    for lane_id, lane in planned_lanes.items():
        run_path = results_root / f"{lane_id}.jsonl"
        records = load_jsonl(run_path)
        if (
            len(records) != 120
            or {str(row["item_id"]) for row in records} != expected_ids
            or {str(row["lane_id"]) for row in records} != {lane_id}
        ):
            fail(f"run does not cover the frozen item set: {lane_id}")
        run_hash = sha256_file(run_path)
        if receipt_hashes.get(run_path.name) != run_hash:
            fail(f"run digest differs from execution receipt: {lane_id}")
        if any(row["packet_sha256"] != packet["packet_sha256"] for row in records):
            fail(f"packet digest differs in run: {lane_id}")
        frozen_commits.update(str(row["frozen_plan_commit"]) for row in records)
        seen_lanes.add(lane_id)
        lanes.append(
            {
                "lane_id": lane_id,
                "provider": lane["provider"],
                "model_requested": lane["model"],
                "model_revision": lane["model_revision"],
                "model_family": lane["model_family"],
                "quantization": "4-bit MLX community snapshot",
                "generation": {
                    "sampler": lane["sampler"],
                    "temperature": lane["temperature"],
                    "top_p": lane["top_p"],
                    "max_output_tokens": lane["max_output_tokens"],
                },
                "run_sha256": run_hash,
                "metrics": derive_reporting_metrics(gold, pairs, records),
            }
        )
    if seen_lanes != set(planned_lanes) or len(frozen_commits) != 1:
        fail("local run lane set or frozen commit is inconsistent")

    aggregate: Json = {
        "schema_version": "1.0.0",
        "status": "COMPLETE",
        "truth_status": "COMPUTATIONAL",
        "study_id": plan["study_id"],
        "design": plan["design"],
        "interpretation": plan["interpretation_boundary"],
        "freeze": {
            "frozen_plan_commit": next(iter(frozen_commits)),
            "plan_sha256": sha256_file(plan_path),
            "schedule_sha256": schedule["schedule_sha256"],
            "dataset_fingerprint": plan["dataset"]["dataset_fingerprint"],
            "packet_sha256": packet["packet_sha256"],
            "catalog_sha256": sha256_file(catalog_path),
            "snapshot_receipt_sha256": sha256_file(snapshot_path),
            "qualification_receipt_sha256": sha256_file(qualification_path),
            "void_attempt_receipt_sha256": sha256_file(void_receipt_path),
            "execution_receipt_sha256": sha256_file(execution_path),
        },
        "lanes": sorted(lanes, key=lambda row: str(row["lane_id"])),
        "deterministic_policy_executor": {
            "items": 120,
            "pairs": 60,
            "end_to_end_item_accuracy": 1.0,
            "end_to_end_pair_accuracy": 1.0,
            "label": "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_BASELINE",
        },
        "failure_rule": plan["statistics"]["failure_rule"],
    }
    if dataset_key == "slsa":
        predictions = load_jsonl(baseline_root / "predictions.jsonl")
        aggregate["structured_random_forest_action_baseline"] = {
            "report_sha256": sha256_file(baseline_root / "report.json"),
            "predictions_sha256": sha256_file(baseline_root / "predictions.jsonl"),
            "scope": "ACTION_ONLY_POLICY_BLIND_STRUCTURED_CLASSIFIER",
            "metrics": derive_reporting_metrics(gold, pairs, baseline_records(predictions)),
        }
    else:
        comparators: Json = {}
        for comparator_id in ("policy_aware", "profile_blind"):
            predictions_path = baseline_root / f"{comparator_id}-predictions.jsonl"
            predictions = load_jsonl(predictions_path)
            comparators[comparator_id] = {
                "scope": (
                    "STRUCTURED_CLASSIFIER_WITH_ACTIVE_PROFILE"
                    if comparator_id == "policy_aware"
                    else "FEATURE_ABLATED_CLASSIFIER_WITHOUT_ACTIVE_PROFILE"
                ),
                "predictions_sha256": sha256_file(predictions_path),
                "metrics": derive_reporting_metrics(gold, pairs, baseline_records(predictions)),
            }
        aggregate["structured_random_forest_comparators"] = comparators
        aggregate["registered_shortcut_result"] = (
            "The profile-blind comparator receives identical features for both members. Its "
            "end-to-end pair accuracy tests the frozen shortcut boundary."
        )
    return aggregate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-key", choices=tuple(DATASETS), required=True)
    parser.add_argument("--freeze-root", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--snapshot-receipt", type=Path, required=True)
    parser.add_argument("--qualification-receipt", type=Path, required=True)
    parser.add_argument("--void-receipt", type=Path, default=VOID_RECEIPT_PATH)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    aggregate = analyze(
        args.dataset_key,
        args.freeze_root.resolve(),
        args.catalog.resolve(),
        args.snapshot_receipt.resolve(),
        args.qualification_receipt.resolve(),
        args.void_receipt.resolve(),
        args.results_root.resolve(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(canonical_json({"status": aggregate["status"], "lanes": len(aggregate["lanes"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
