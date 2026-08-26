#!/usr/bin/env python3
"""Validate the hosted policy-switch replacement freeze without loading credentials."""

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

from freeze_policy_switch_hosted_replacement import (  # noqa: E402
    RESOURCE_EXHAUSTION_RULE,
    RUNTIME_SOURCES,
    SOURCE_EXCLUSION,
    SOURCE_PLAN,
    STUDY_ID,
)
from freeze_slsa_portability_study import request_body  # noqa: E402
from validate_policy_switch_study import validate_baselines, validate_dataset  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"policy-switch-hosted-replacement-validate: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def validate_freeze(
    plan_path: Path, schedule_path: Path, dataset_root: Path, baseline_root: Path
) -> Json:
    dataset_report = validate_dataset(dataset_root)
    baseline_report = validate_baselines(dataset_root, baseline_root)
    plan = load_object(plan_path)
    schedule = load_object(schedule_path)
    manifest = load_object(dataset_root / "manifest.json")
    packet = load_object(dataset_root / "evaluation-prompt-packet.json")
    source_plan = load_object(SOURCE_PLAN)
    catalog_path = ROOT / str(plan["catalog"]["path"])
    catalog = load_object(catalog_path)
    if (
        plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE"
        or plan.get("truth_status") != "SEALED_UNTIL_ALL_TERMINAL_RECORDS_EXIST"
        or plan.get("study_id") != STUDY_ID
        or schedule.get("study_id") != STUDY_ID
        or plan.get("dataset", {}).get("source_study_id") != manifest.get("study_id")
        or plan.get("prompt", {}).get("source_study_id") != packet.get("study_id")
    ):
        fail("replacement study identity or truth status changed")
    if (
        plan["dataset"].get("dataset_fingerprint") != manifest.get("dataset_fingerprint")
        or plan["dataset"].get("manifest_file_sha256")
        != sha256_file(dataset_root / "manifest.json")
        or plan["prompt"].get("packet_sha256") != packet.get("packet_sha256")
        or plan["prompt"].get("packet_file_sha256")
        != sha256_file(dataset_root / "evaluation-prompt-packet.json")
    ):
        fail("source dataset or prompt binding changed")

    replacement = plan.get("replacement", {})
    selection_path = ROOT / str(replacement.get("selection_audit_path"))
    selection = load_object(selection_path)
    selection_payload = {key: value for key, value in selection.items() if key != "self_digest"}
    if (
        replacement.get("kind") != "RESOURCE_FAILURE_REPLACEMENT_WITH_UNCHANGED_PROTOCOL"
        or replacement.get("predecessor_plan_sha256") != sha256_file(SOURCE_PLAN)
        or replacement.get("predecessor_exclusion_sha256") != sha256_file(SOURCE_EXCLUSION)
        or replacement.get("predecessor_outputs_eligible") is not False
        or replacement.get("dataset_prompt_and_endpoint_protocol_unchanged") is not True
        or replacement.get("prior_hosted_outputs_known_before_replacement") is not True
        or replacement.get("local_policy_switch_outputs_known_before_replacement") is not False
        or replacement.get("selection_audit_sha256") != sha256_file(selection_path)
        or selection.get("status")
        != "HOSTED_RESOURCE_FAILURE_REPLACEMENT_SELECTED_BEFORE_NEW_OUTCOMES"
        or selection.get("new_replacement_terminal_records_before_freeze") != 0
        or selection.get("local_policy_switch_terminal_records_before_freeze") != 0
        or selection.get("new_model_calls_for_selection") != 0
        or selection.get("source_dataset_fingerprint") != manifest.get("dataset_fingerprint")
        or selection.get("source_packet_sha256") != packet.get("packet_sha256")
        or selection.get("catalog_selected_model_ids") != catalog.get("selected_model_ids")
        or selection.get("resource_exhaustion_rule") != RESOURCE_EXHAUSTION_RULE
        or selection.get("self_digest")
        != sha256_bytes(canonical_json(selection_payload).encode("utf-8"))
    ):
        fail("replacement selection boundary changed")

    exclusion = load_object(SOURCE_EXCLUSION)
    if (
        exclusion.get("status") != "HOSTED_POLICY_SWITCH_EXCLUDED_IN_FULL_SHARED_QUOTA_EXHAUSTION"
        or exclusion.get("decision", {}).get("hosted_model_rows_enter_manuscript") is not False
        or exclusion.get("decision", {}).get("successful_row_subset_selected") is not False
    ):
        fail("predecessor full-study exclusion changed")

    if (
        plan["catalog"].get("file_sha256") != sha256_file(catalog_path)
        or catalog.get("selected_model_ids") != ["qwen3.7-max", "deepseek-v4-flash"]
        or catalog.get("credentials_retained") is not False
    ):
        fail("replacement catalog binding changed")
    if plan["baselines"].get("report_sha256") != sha256_file(baseline_root / "report.json"):
        fail("baseline report binding changed")

    lanes = plan.get("formal_lanes")
    if not isinstance(lanes, list) or len(lanes) != 2:
        fail("replacement lanes are malformed")
    lane_ids = [str(row["lane_id"]) for row in lanes]
    if (
        lane_ids != plan["execution"].get("base_lane_order")
        or [str(row["model"]) for row in lanes] != ["qwen3.7-max", "deepseek-v4-flash"]
        or any(not lane_id.endswith("policy-switch-hosted-replacement-v2") for lane_id in lane_ids)
    ):
        fail("replacement lane identity changed")
    for lane, predecessor in zip(lanes, source_plan["formal_lanes"], strict=True):
        replacement_payload = {key: value for key, value in lane.items() if key != "lane_id"}
        predecessor_payload = {key: value for key, value in predecessor.items() if key != "lane_id"}
        if replacement_payload != predecessor_payload:
            fail("replacement model, adapter, endpoint, or decoding protocol changed")
    if (
        plan["execution"].get("client_retry_count") != 0
        or plan["execution"].get("partial_resume") != "FORBIDDEN"
        or plan["execution"].get("planned_application_posts") != 240
        or plan["execution"].get("resource_exhaustion_eligibility_rule") != RESOURCE_EXHAUSTION_RULE
        or "all 240 replacement terminal outcomes" not in str(plan.get("promotion_rule"))
    ):
        fail("replacement one-shot promotion rule changed")
    for field in ("budget", "statistics", "sources", "baselines", "interpretation_boundary"):
        if plan.get(field) != source_plan.get(field):
            fail(f"replacement protocol field changed: {field}")

    schedule_payload = {key: value for key, value in schedule.items() if key != "schedule_sha256"}
    schedule_hash = sha256_bytes(canonical_json(schedule_payload).encode("utf-8"))
    cells = schedule.get("cells")
    if (
        schedule.get("schedule_sha256") != schedule_hash
        or plan["execution"].get("schedule_sha256") != schedule_hash
        or not isinstance(cells, list)
        or len(cells) != 240
        or len({str(cell["cell_id"]) for cell in cells}) != 240
        or Counter(str(cell["lane_id"]) for cell in cells)
        != Counter({lane_id: 120 for lane_id in lane_ids})
    ):
        fail("replacement request schedule changed")
    packet_by_id = {str(row["item_id"]): row for row in packet["records"]}
    lanes_by_id = {str(row["lane_id"]): row for row in lanes}
    for cell in cells:
        record = packet_by_id[str(cell["item_id"])]
        body = request_body(lanes_by_id[str(cell["lane_id"])], str(record["prompt"]))
        expected = sha256_bytes(canonical_json(body).encode("utf-8"))
        if cell.get("request_body_sha256") != expected:
            fail(f"replacement request body differs: {cell['cell_id']}")
    if set(plan.get("runtime_source_sha256", {})) != set(RUNTIME_SOURCES):
        fail("replacement runtime-source inventory changed")
    for path, expected in plan["runtime_source_sha256"].items():
        if sha256_file(ROOT / path) != expected:
            fail(f"replacement runtime source differs: {path}")
    return {
        "status": "POLICY_SWITCH_HOSTED_REPLACEMENT_FREEZE_VALID",
        "credentials_loaded": False,
        "dataset": dataset_report["status"],
        "baselines": baseline_report["status"],
        "items": 120,
        "lanes": 2,
        "cells": 240,
        "schedule_sha256": schedule_hash,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    args = parser.parse_args()
    print(
        canonical_json(
            validate_freeze(
                args.plan.resolve(),
                args.schedule.resolve(),
                args.dataset_root.resolve(),
                args.baseline_root.resolve(),
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
