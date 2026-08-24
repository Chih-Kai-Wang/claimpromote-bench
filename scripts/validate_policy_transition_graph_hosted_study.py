#!/usr/bin/env python3
"""Validate the hosted policy-transition graph freeze without loading credentials."""

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

from build_policy_switch_study import (  # noqa: E402
    BASE_POLICY_PATH,
    DECISION_SCHEMA,
    SOURCE_REGISTRY,
    SWITCH_POLICY_PATH,
)
from freeze_policy_transition_graph_hosted_study import (  # noqa: E402
    BASELINE_REQUIREMENTS,
    RESOURCE_EXHAUSTION_RULE,
    RUNTIME_SOURCES,
    SOURCE_HOSTED_PLAN,
    STUDY_ID,
    self_digest,
)
from freeze_slsa_portability_study import request_body  # noqa: E402
from validate_policy_switch_study import validate_baselines  # noqa: E402
from validate_policy_transition_graph_study import (  # noqa: E402
    runtime_source_hash_matches,
    validate_coverage_expectation,
)
from validate_policy_transition_graph_study import (  # noqa: E402
    validate as validate_graph,
)

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"policy-transition-graph-hosted-validate: {message}")


def load_object(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def validate_freeze(
    plan_path: Path,
    schedule_path: Path,
    dataset_root: Path,
    baseline_root: Path,
) -> Json:
    coverage = validate_graph(dataset_root)
    baseline_report = validate_baselines(dataset_root, baseline_root)
    plan = load_object(plan_path)
    schedule = load_object(schedule_path)
    manifest = load_object(dataset_root / "manifest.json")
    packet = load_object(dataset_root / "evaluation-prompt-packet.json")
    coverage_path = dataset_root.parent / "transition-coverage.json"
    validate_coverage_expectation(coverage, load_object(coverage_path), coverage_path)
    if (
        plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE"
        or plan.get("truth_status") != "SEALED_UNTIL_ALL_TERMINAL_RECORDS_EXIST"
        or plan.get("study_id") != STUDY_ID
        or schedule.get("study_id") != STUDY_ID
        or plan.get("dataset", {}).get("source_study_id") != manifest.get("study_id")
        or plan.get("prompt", {}).get("source_study_id") != packet.get("study_id")
    ):
        fail("study identity or truth status changed")
    if (
        plan["dataset"].get("dataset_fingerprint") != manifest.get("dataset_fingerprint")
        or plan["dataset"].get("manifest_file_sha256")
        != sha256_file(dataset_root / "manifest.json")
        or plan["dataset"].get("pair_contract") != manifest.get("pair_contract")
        or plan["prompt"].get("packet_sha256") != packet.get("packet_sha256")
        or plan["prompt"].get("packet_file_sha256")
        != sha256_file(dataset_root / "evaluation-prompt-packet.json")
        or plan["prompt"].get("decision_schema_sha256") != sha256_file(DECISION_SCHEMA)
    ):
        fail("dataset or prompt binding changed")

    for key, expected_path in (
        ("base_policy_sha256", BASE_POLICY_PATH),
        ("switch_policy_sha256", SWITCH_POLICY_PATH),
        ("registry_sha256", SOURCE_REGISTRY),
    ):
        if plan["sources"].get(key) != sha256_file(expected_path):
            fail(f"source binding changed: {key}")
    source_receipt_path = ROOT / str(plan["sources"]["validation_receipt_path"])
    if (
        plan["sources"].get("validation_receipt_sha256") != sha256_file(source_receipt_path)
        or load_object(source_receipt_path).get("upstream_sources_verified") is not True
    ):
        fail("source validation receipt changed")

    catalog_path = ROOT / str(plan["catalog"]["path"])
    catalog = load_object(catalog_path)
    if (
        plan["catalog"].get("file_sha256") != sha256_file(catalog_path)
        or catalog.get("selected_model_ids") != ["qwen3.7-max", "deepseek-v4-flash"]
        or catalog.get("credentials_retained") is not False
        or plan["catalog"].get("selected_before_new_study_outputs") is not True
    ):
        fail("catalog or route-selection boundary changed")

    if (
        plan["baselines"].get("report_sha256") != sha256_file(baseline_root / "report.json")
        or plan["baselines"].get("requirements_sha256") != sha256_file(BASELINE_REQUIREMENTS)
        or plan["baselines"].get("evaluation_gold_loaded") is not False
        or plan["baselines"].get("model_outputs_loaded") is not False
    ):
        fail("baseline binding changed")
    for comparator_id in ("policy_aware", "profile_blind"):
        predictions = baseline_root / f"{comparator_id}-predictions.jsonl"
        if plan["baselines"]["comparators"][comparator_id].get("predictions_sha256") != sha256_file(
            predictions
        ):
            fail(f"baseline prediction binding changed: {comparator_id}")

    graph = plan.get("transition_graph", {})
    if (
        graph.get("coverage_path") != coverage_path.relative_to(ROOT).as_posix()
        or graph.get("coverage_sha256") != sha256_file(coverage_path)
        or graph.get("directed_nonself_transitions_possible") != 12
        or graph.get("directed_transitions_semantically_reachable") != 10
        or graph.get("directed_transitions_covered") != 10
        or graph.get("structurally_unreachable_transitions") != ["HOLD->DEMOTE", "DEMOTE->HOLD"]
        or graph.get("authored_profile_difference_rules_covered") != 12
        or graph.get("authored_profile_difference_rules_total") != 12
    ):
        fail("reachable transition-graph binding changed")

    design = plan.get("design", {})
    if (
        design.get("controlled_path") != "/active_policy_profile"
        or design.get("evaluation_pairs") != 60
        or design.get("evaluation_items") != 120
        or design.get("evaluation_factors") != 10
        or design.get("reachable_directed_nonself_transitions") != 10
        or design.get("contexts_per_transition") != 6
        or design.get("planned_model_item_cells") != 240
        or design.get("attempts_per_cell") != 1
        or design.get("selection_uses_new_study_outputs") is not False
    ):
        fail("hosted graph design changed")

    selection_path = ROOT / str(plan["selection_receipt"]["path"])
    selection = load_object(selection_path)
    if (
        plan["selection_receipt"].get("file_sha256") != sha256_file(selection_path)
        or plan["selection_receipt"].get("self_digest") != selection.get("self_digest")
        or selection.get("self_digest") != self_digest(selection)
        or selection.get("status") != "PREINFERENCE_HOSTED_POLICY_TRANSITION_GRAPH_SELECTION"
        or selection.get("outcomes_used_to_choose_graph_edges_or_contexts") is not False
        or selection.get("hosted_transition_graph_terminal_records_before_freeze") != 0
        or selection.get("local_transition_graph_terminal_records_before_freeze") != 0
        or selection.get("new_model_calls_for_selection") != 0
        or selection.get("evaluation_gold_used_to_train_comparators") is not False
        or selection.get("dataset_fingerprint") != manifest.get("dataset_fingerprint")
        or selection.get("packet_sha256") != packet.get("packet_sha256")
        or selection.get("transition_coverage_sha256") != sha256_file(coverage_path)
        or selection.get("catalog_selected_model_ids") != catalog.get("selected_model_ids")
        or selection.get("resource_exhaustion_rule") != RESOURCE_EXHAUSTION_RULE
    ):
        fail("preinference selection receipt changed")

    lanes = plan.get("formal_lanes")
    source_lanes = load_object(SOURCE_HOSTED_PLAN).get("formal_lanes")
    if not isinstance(lanes, list) or not isinstance(source_lanes, list) or len(lanes) != 2:
        fail("formal lanes are malformed")
    lane_ids = [str(row["lane_id"]) for row in lanes]
    if (
        lane_ids != plan["execution"].get("base_lane_order")
        or [str(row["model"]) for row in lanes] != ["qwen3.7-max", "deepseek-v4-flash"]
        or any(not lane_id.endswith("policy-transition-graph-hosted-v1") for lane_id in lane_ids)
    ):
        fail("formal lane identity changed")
    for lane, source_lane in zip(lanes, source_lanes, strict=True):
        lane_payload = {key: value for key, value in lane.items() if key != "lane_id"}
        source_payload = {key: value for key, value in source_lane.items() if key != "lane_id"}
        if lane_payload != source_payload:
            fail("model, adapter, endpoint, or decoding protocol changed")
    execution = plan.get("execution", {})
    if (
        execution.get("application_posts_per_cell") != 1
        or execution.get("client_retry_count") != 0
        or execution.get("partial_resume") != "FORBIDDEN"
        or execution.get("planned_application_posts") != 240
        or execution.get("resource_exhaustion_eligibility_rule") != RESOURCE_EXHAUSTION_RULE
        or "complete set of all 240 terminal outcomes" not in str(plan.get("promotion_rule"))
    ):
        fail("one-shot promotion or failure rule changed")

    schedule_payload = {key: value for key, value in schedule.items() if key != "schedule_sha256"}
    schedule_hash = sha256_bytes(canonical_json(schedule_payload).encode("utf-8"))
    cells = schedule.get("cells")
    if (
        schedule.get("schedule_sha256") != schedule_hash
        or execution.get("schedule_sha256") != schedule_hash
        or execution.get("schedule_path") != schedule_path.relative_to(ROOT).as_posix()
        or schedule.get("packet_sha256") != packet.get("packet_sha256")
        or schedule.get("dataset_fingerprint") != manifest.get("dataset_fingerprint")
        or not isinstance(cells, list)
        or len(cells) != 240
        or [int(cell["sequence"]) for cell in cells] != list(range(240))
        or len({str(cell["cell_id"]) for cell in cells}) != 240
        or Counter(str(cell["lane_id"]) for cell in cells)
        != Counter({lane_id: 120 for lane_id in lane_ids})
    ):
        fail("request schedule changed")
    packet_by_id = {str(row["item_id"]): row for row in packet["records"]}
    lanes_by_id = {str(row["lane_id"]): row for row in lanes}
    for cell in cells:
        item_id = str(cell["item_id"])
        lane_id = str(cell["lane_id"])
        record = packet_by_id.get(item_id)
        if record is None or cell.get("prompt_sha256") != record.get("prompt_sha256"):
            fail(f"schedule prompt binding changed: {cell.get('cell_id')}")
        body = request_body(lanes_by_id[lane_id], str(record["prompt"]))
        expected = sha256_bytes(canonical_json(body).encode("utf-8"))
        if cell.get("request_body_sha256") != expected:
            fail(f"request body changed: {cell.get('cell_id')}")

    runtime = plan.get("runtime_source_sha256")
    if not isinstance(runtime, dict) or set(runtime) != set(RUNTIME_SOURCES):
        fail("runtime-source inventory changed")
    for path, expected in runtime.items():
        if not runtime_source_hash_matches(path, expected):
            fail(f"runtime source changed after freeze: {path}")
    return {
        "status": "POLICY_TRANSITION_GRAPH_HOSTED_FREEZE_VALID",
        "credentials_loaded": False,
        "dataset": coverage["status"],
        "baselines": baseline_report["status"],
        "items": 120,
        "pairs": 60,
        "reachable_transitions": 10,
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
