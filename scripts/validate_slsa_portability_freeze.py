#!/usr/bin/env python3
"""Validate the complete SLSA portability execution freeze without credentials."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from freeze_slsa_portability_study import request_body  # noqa: E402
from validate_slsa_portability_study import validate_dataset  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"slsa-portability-freeze-validate: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def load_jsonl(path: Path) -> list[Json]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not all(isinstance(row, dict) for row in rows):
        fail(f"{path} contains a non-object row")
    return rows


def validate_freeze(
    plan_path: Path, schedule_path: Path, dataset_root: Path, baseline_root: Path
) -> Json:
    dataset_report = validate_dataset(dataset_root, verify_upstream=False)
    plan = load_object(plan_path)
    schedule = load_object(schedule_path)
    manifest = load_object(dataset_root / "manifest.json")
    packet = load_object(dataset_root / "evaluation-prompt-packet.json")
    catalog_path = ROOT / str(plan["catalog"]["path"])
    catalog = load_object(catalog_path)
    if plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE":
        fail("plan status is not frozen")
    if plan.get("truth_status") != "SEALED_UNTIL_ALL_TERMINAL_RECORDS_EXIST":
        fail("plan truth status is invalid")
    if plan.get("study_id") != manifest.get("study_id"):
        fail("plan and dataset study IDs differ")
    if packet.get("study_id") != plan.get("study_id"):
        fail("plan and prompt-packet study IDs differ")
    if plan["prompt"].get("protocol_version") != "v2":
        fail("replacement prompt protocol is not v2")
    if plan["prompt"].get("complete_decision_schema_visible_to_every_lane") is not True:
        fail("complete decision schema is not declared visible to every lane")
    if plan["prompt"].get("numeric_probability_type_visible_to_every_lane") is not True:
        fail("numeric probability type is not declared visible to every lane")
    if plan["dataset"]["dataset_fingerprint"] != manifest["dataset_fingerprint"]:
        fail("plan dataset fingerprint differs")
    if plan["dataset"]["manifest_file_sha256"] != sha256_file(dataset_root / "manifest.json"):
        fail("plan dataset-manifest hash differs")
    if plan["prompt"]["packet_sha256"] != packet["packet_sha256"]:
        fail("plan packet hash differs")
    if plan["prompt"]["packet_file_sha256"] != sha256_file(
        dataset_root / "evaluation-prompt-packet.json"
    ):
        fail("plan packet-file hash differs")
    if plan["catalog"]["file_sha256"] != sha256_file(catalog_path):
        fail("plan catalog hash differs")
    source_receipt = ROOT / str(plan["sources"]["validation_receipt_path"])
    if plan["sources"]["validation_receipt_sha256"] != sha256_file(source_receipt):
        fail("plan source-validation receipt hash differs")
    if load_object(source_receipt).get("upstream_sources_verified") is not True:
        fail("source-validation receipt did not verify upstream bytes")
    replacement = plan.get("replacement_boundary")
    if not isinstance(replacement, dict):
        fail("replacement boundary is absent")
    void_receipt_path = ROOT / str(replacement["predecessor_void_receipt_path"])
    void_receipt = load_object(void_receipt_path)
    if replacement.get("predecessor_void_receipt_sha256") != sha256_file(void_receipt_path):
        fail("predecessor void-receipt hash differs")
    if void_receipt.get("status") != "VOID_INCOMPLETE_PROTOCOL_DEFECT":
        fail("predecessor attempt is not void")
    if replacement.get("predecessor_records_eligible_for_manuscript_metrics") is not False:
        fail("predecessor records are not excluded from manuscript metrics")
    if replacement.get("predecessor_records_eligible_for_model_or_item_selection") is not False:
        fail("predecessor records are not excluded from selection")
    if replacement.get("v1_prompts_reissued") is not False:
        fail("replacement permits v1 prompt reissue")
    if catalog.get("selected_model_ids") != ["qwen3.7-max", "deepseek-v4-flash"]:
        fail("catalog selected models differ")
    if catalog.get("credentials_retained") is not False:
        fail("catalog credential boundary differs")

    baseline_report = load_object(baseline_root / "report.json")
    predictions = load_jsonl(baseline_root / "predictions.jsonl")
    if baseline_report.get("evaluation_gold_loaded") is not False:
        fail("baseline reports evaluation-label access")
    if baseline_report.get("model_outputs_loaded") is not False:
        fail("baseline reports model-output access")
    baseline_requirements = ROOT / str(plan["baseline"]["requirements_path"])
    if plan["baseline"]["requirements_sha256"] != sha256_file(baseline_requirements):
        fail("plan baseline-requirements hash differs")
    if plan["baseline"]["report_sha256"] != sha256_file(baseline_root / "report.json"):
        fail("plan baseline-report hash differs")
    if plan["baseline"]["predictions_sha256"] != sha256_file(baseline_root / "predictions.jsonl"):
        fail("plan baseline-prediction hash differs")
    evaluation_ids = {str(row["id"]) for row in load_jsonl(dataset_root / "evaluation-items.jsonl")}
    prediction_ids = {str(row["item_id"]) for row in predictions}
    if len(predictions) != 120 or prediction_ids != evaluation_ids:
        fail("baseline predictions do not cover the evaluation set exactly")

    lane_ids = [str(lane["lane_id"]) for lane in plan["formal_lanes"]]
    if lane_ids != plan["execution"]["base_lane_order"] or len(lane_ids) != 2:
        fail("formal lanes differ from the base lane order")
    if [str(lane["model"]) for lane in plan["formal_lanes"]] != [
        "qwen3.7-max",
        "deepseek-v4-flash",
    ]:
        fail("formal model configurations differ")
    if schedule.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE":
        fail("schedule status is invalid")
    if schedule.get("study_id") != plan.get("study_id"):
        fail("schedule and plan study IDs differ")
    schedule_without_hash = {
        key: value for key, value in schedule.items() if key != "schedule_sha256"
    }
    actual_schedule_hash = sha256_bytes(canonical_json(schedule_without_hash).encode("utf-8"))
    if schedule.get("schedule_sha256") != actual_schedule_hash:
        fail("schedule content hash differs")
    if plan["execution"]["schedule_sha256"] != actual_schedule_hash:
        fail("plan schedule hash differs")
    cells = schedule.get("cells")
    if not isinstance(cells, list) or len(cells) != 240:
        fail("schedule must contain 240 cells")
    if len({str(cell["cell_id"]) for cell in cells}) != 240:
        fail("schedule contains duplicate cell IDs")
    if Counter(str(cell["lane_id"]) for cell in cells) != Counter(
        {lane_id: 120 for lane_id in lane_ids}
    ):
        fail("schedule lane coverage differs")
    packet_by_id = {str(row["item_id"]): row for row in packet["records"]}
    lanes = {str(lane["lane_id"]): lane for lane in plan["formal_lanes"]}
    for cell in cells:
        record = packet_by_id[str(cell["item_id"])]
        body = request_body(lanes[str(cell["lane_id"])], str(record["prompt"]))
        if cell["request_body_sha256"] != sha256_bytes(canonical_json(body).encode("utf-8")):
            fail(f"request body hash differs: {cell['cell_id']}")
    for path, expected in plan["runtime_source_sha256"].items():
        if sha256_file(ROOT / path) != expected:
            fail(f"runtime source hash differs: {path}")
    if plan["execution"]["client_retry_count"] != 0:
        fail("client retries must remain zero")
    return {
        "status": "SLSA_PORTABILITY_EXECUTION_FREEZE_VALID",
        "credentials_loaded": False,
        "dataset": dataset_report["status"],
        "items": 120,
        "lanes": 2,
        "cells": 240,
        "baseline_predictions": len(predictions),
        "schedule_sha256": actual_schedule_hash,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    args = parser.parse_args()
    report = validate_freeze(
        args.plan.resolve(),
        args.schedule.resolve(),
        args.dataset_root.resolve(),
        args.baseline_root.resolve(),
    )
    print(canonical_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
