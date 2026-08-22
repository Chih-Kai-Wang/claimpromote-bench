#!/usr/bin/env python3
"""Validate the frozen public model-breadth supplement without model credentials."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_public_model_breadth_study import request_body  # noqa: E402

from claimpromotebench.dataset import load_json  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
EXPECTED_MODELS = (
    "qwen3.8-max",
    "deepseek-v4-pro",
    "glm-5.3",
    "kimi-k3",
    "mimo-v2.5-pro",
    "minimax-m3",
    "hy3",
)
EXPECTED_FAMILIES = (
    "Qwen",
    "DeepSeek",
    "GLM",
    "Kimi",
    "MiMo",
    "MiniMax",
    "Tencent Hunyuan",
)
REQUIRED_RUNTIME_SOURCES = {
    "schemas/agent-decision.schema.json",
    "scripts/analyze_balanced_public_challenge.py",
    "scripts/analyze_public_model_breadth_study.py",
    "scripts/build_public_model_breadth_study.py",
    "scripts/finalize_public_model_breadth_study.py",
    "scripts/run_public_model_breadth_study.py",
    "scripts/run_stronger_model_study.py",
    "scripts/validate_public_model_breadth_study.py",
    "v2/schemas/stronger-model-run-record.schema.json",
}


def fail(message: str) -> None:
    raise ValueError(f"public model breadth validation: {message}")


def validate_study(plan_path: Path, schedule_path: Path, packet_path: Path) -> Json:
    plan = load_json(plan_path)
    schedule = load_json(schedule_path)
    packet = load_json(packet_path)

    if plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE" or plan.get("truth_status") != "OPEN":
        fail("plan is not frozen with unopened result truth")
    design = plan.get("design", {})
    if (
        design.get("analysis_split") != "PUBLIC_PRECOMMITTED_MODEL_BREADTH_SUPPLEMENT"
        or design.get("public_before_inference") is not True
        or design.get("held_out_generalization_claim") is not False
        or design.get("breadth_dimension_added") != "MODEL_FAMILY_ONLY"
        or design.get("planned_lanes") != 7
        or design.get("planned_instances") != 180
        or design.get("planned_model_item_cells") != 1260
        or design.get("naturalistic_case_count") != 0
    ):
        fail("design boundary changed")

    lanes = plan.get("formal_lanes")
    if not isinstance(lanes, list) or len(lanes) != 7:
        fail("exactly seven formal lanes are required")
    if tuple(str(lane.get("model")) for lane in lanes) != EXPECTED_MODELS:
        fail("selected model list or order changed")
    if tuple(str(lane.get("model_family")) for lane in lanes) != EXPECTED_FAMILIES:
        fail("selected model-family list changed")
    lane_ids = [str(lane.get("lane_id")) for lane in lanes]
    if lane_ids != plan.get("execution", {}).get("base_lane_order"):
        fail("formal lane order differs from the frozen execution order")
    for lane in lanes:
        if (
            lane.get("provider") != "OpenCode Go"
            or lane.get("base_url") != "https://opencode.ai/zen/go/v1"
            or lane.get("auth_env") != "OPENCODE_GO_API_KEY"
            or lane.get("response_format") != "prompt_only_json"
            or lane.get("allow_single_json_object_extraction") is not True
            or lane.get("max_output_tokens") != 1536
            or lane.get("billing_mode") != "PREEXISTING_SUBSCRIPTION_INCLUDED_QUOTA"
            or lane.get("data_training") is not False
            or lane.get("data_retention_days") != 0
        ):
            fail(f"lane contract changed: {lane.get('lane_id')}")
        if lane.get("api_kind") not in {"openai_compatible", "anthropic_messages"}:
            fail(f"unsupported lane adapter: {lane.get('lane_id')}")

    catalog_path = ROOT / str(plan["catalog"]["path"])
    if sha256_file(catalog_path) != plan["catalog"].get("file_sha256"):
        fail("catalog snapshot digest changed")
    catalog = load_json(catalog_path)
    if (
        catalog.get("http_status") != 200
        or catalog.get("account_identifiers_retained") is not False
        or catalog.get("provider_response_identifiers_retained") is not False
        or tuple(catalog.get("selected_model_ids", [])) != EXPECTED_MODELS
        or not set(EXPECTED_MODELS).issubset(set(catalog.get("model_ids", [])))
    ):
        fail("catalog selection receipt changed")

    if sha256_file(packet_path) != plan["prompt"].get("packet_file_sha256"):
        fail("prompt packet file digest changed")
    if packet.get("packet_sha256") != plan["prompt"].get("packet_sha256"):
        fail("prompt packet content digest changed")
    manifest = ROOT / str(plan["dataset"]["path"]) / "manifest.json"
    if sha256_file(manifest) != plan["dataset"].get("manifest_sha256"):
        fail("dataset manifest digest changed")
    if packet.get("dataset_manifest_sha256") != plan["dataset"].get("manifest_sha256"):
        fail("packet and dataset binding changed")

    if sha256_file(schedule_path) != plan["execution"].get("schedule_file_sha256"):
        fail("schedule file digest changed")
    digest_payload = deepcopy(schedule)
    observed_schedule_sha = digest_payload.pop("schedule_sha256", None)
    recomputed_schedule_sha = sha256_bytes(canonical_json(digest_payload).encode("utf-8"))
    if observed_schedule_sha != recomputed_schedule_sha:
        fail("schedule self-digest is invalid")
    if observed_schedule_sha != plan["execution"].get("schedule_sha256"):
        fail("plan does not bind the schedule self-digest")
    if (
        schedule.get("study_id") != plan.get("study_id")
        or schedule.get("contains_prompts") is not False
        or schedule.get("contains_gold") is not False
        or schedule.get("contains_credentials") is not False
        or schedule.get("planned_items") != 180
        or schedule.get("planned_lanes") != 7
        or schedule.get("planned_cells") != 1260
        or schedule.get("application_posts_per_cell") != 1
        or schedule.get("client_retry_count") != 0
        or schedule.get("base_lane_order") != lane_ids
    ):
        fail("schedule top-level contract changed")

    packet_by_id = {str(row["item_id"]): row for row in packet.get("records", [])}
    ordered_items = sorted(packet_by_id)
    cells = schedule.get("cells")
    if not isinstance(cells, list) or len(cells) != 1260:
        fail("schedule cell count changed")
    lane_by_id = {str(lane["lane_id"]): lane for lane in lanes}
    seen_cells: set[str] = set()
    counts: Counter[str] = Counter()
    positions: dict[str, Counter[int]] = {lane_id: Counter() for lane_id in lane_ids}
    for sequence, cell in enumerate(cells):
        if not isinstance(cell, dict) or set(cell) != {
            "sequence",
            "item_index",
            "within_item_position",
            "cell_id",
            "lane_id",
            "item_id",
            "pair_id",
            "prompt_sha256",
            "request_body_sha256",
        }:
            fail("schedule cell schema changed")
        item_index = sequence // len(lane_ids)
        within_position = sequence % len(lane_ids)
        rotation = item_index % len(lane_ids)
        rotated = lane_ids[rotation:] + lane_ids[:rotation]
        lane_id = str(cell["lane_id"])
        item_id = str(cell["item_id"])
        expected_item_id = ordered_items[item_index]
        if (
            cell["sequence"] != sequence
            or cell["item_index"] != item_index
            or cell["within_item_position"] != within_position
            or lane_id != rotated[within_position]
            or item_id != expected_item_id
            or cell["cell_id"] != f"{lane_id}/{item_id}"
            or cell["cell_id"] in seen_cells
        ):
            fail(f"schedule order or identity changed at sequence {sequence}")
        seen_cells.add(str(cell["cell_id"]))
        counts[lane_id] += 1
        positions[lane_id][within_position] += 1
        record = packet_by_id[item_id]
        if (
            cell["pair_id"] != record["pair_id"]
            or cell["prompt_sha256"] != record["prompt_sha256"]
            or cell["request_body_sha256"]
            != sha256_bytes(
                canonical_json(request_body(lane_by_id[lane_id], str(record["prompt"]))).encode(
                    "utf-8"
                )
            )
        ):
            fail(f"schedule request binding changed: {cell['cell_id']}")
    if counts != Counter({lane_id: 180 for lane_id in lane_ids}):
        fail("schedule is not exactly 180 cells per lane")
    if any(max(counter.values()) - min(counter.values()) > 1 for counter in positions.values()):
        fail("cyclic lane positions are not balanced within one cell")

    runtime_hashes = plan.get("runtime_source_sha256")
    if not isinstance(runtime_hashes, dict) or set(runtime_hashes) != REQUIRED_RUNTIME_SOURCES:
        fail("runtime source registry is incomplete")
    for relative, expected in runtime_hashes.items():
        if sha256_file(ROOT / relative) != expected:
            fail(f"runtime source digest changed: {relative}")

    budget = plan.get("budget", {})
    if (
        budget.get("incremental_cash_cap_usd") != 0.0
        or budget.get("subscription_quota_only") is not True
        or budget.get("use_balance_after_subscription_limit") is not False
        or budget.get("workflow_initiated_purchase_or_recharge") is not False
        or budget.get("future_quota_resets_authorized") is not False
        or budget.get("adaptive_stop_on_usage_or_results") is not False
    ):
        fail("budget boundary changed")
    return {
        "status": "PUBLIC_MODEL_BREADTH_FREEZE_VALID",
        "study_id": plan["study_id"],
        "models": len(lanes),
        "items": len(ordered_items),
        "cells": len(cells),
        "schedule_sha256": observed_schedule_sha,
        "credentials_loaded": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    args = parser.parse_args()
    result = validate_study(args.plan.resolve(), args.schedule.resolve(), args.packet.resolve())
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
