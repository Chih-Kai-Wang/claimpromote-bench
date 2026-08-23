#!/usr/bin/env python3
"""Validate the frozen hosted minimum policy-migration study without credentials."""

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

from derive_minimal_policy_migration_suite import derive as derive_minimal_suite  # noqa: E402
from freeze_minimal_policy_migration_hosted_study import (  # noqa: E402
    BASELINE_REQUIREMENTS,
    CATALOG_PATH,
    COVERAGE_PATH,
    MINIMAL_SUITE_PATH,
    RESOURCE_EXHAUSTION_RULE,
    RUNTIME_SOURCES,
    SOURCE_HOSTED_PLAN,
    STUDY_ID,
    build_schedule,
    self_digest,
)
from validate_policy_switch_study import validate_baselines  # noqa: E402
from validate_policy_transition_graph_study import validate as validate_graph  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"minimal-policy-migration-hosted-validate: {message}")


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
    baseline = validate_baselines(dataset_root, baseline_root)
    plan = load_object(plan_path)
    schedule = load_object(schedule_path)
    manifest = load_object(dataset_root / "manifest.json")
    packet = load_object(dataset_root / "evaluation-prompt-packet.json")
    suite = load_object(MINIMAL_SUITE_PATH)
    recomputed_suite = derive_minimal_suite(dataset_root / "evaluation-pairs.json", COVERAGE_PATH)
    if canonical_json(suite) != canonical_json(recomputed_suite):
        fail("minimum suite differs from a clean deterministic derivation")

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
    ):
        fail("dataset or prompt binding changed")

    suite_binding = plan.get("minimum_suite", {})
    if (
        suite_binding.get("path") != MINIMAL_SUITE_PATH.relative_to(ROOT).as_posix()
        or suite_binding.get("file_sha256") != sha256_file(MINIMAL_SUITE_PATH)
        or suite_binding.get("self_digest") != suite.get("self_digest")
        or suite_binding.get("optimality_certificate") != suite.get("optimality_certificate")
        or suite_binding.get("coverage") != suite.get("coverage")
        or suite.get("model_or_client_calls_to_derive") != 0
    ):
        fail("minimum-suite binding or zero-call derivation boundary changed")
    graph = plan.get("transition_graph", {})
    if (
        graph.get("coverage_path") != COVERAGE_PATH.relative_to(ROOT).as_posix()
        or graph.get("coverage_sha256") != sha256_file(COVERAGE_PATH)
        or graph.get("directed_nonself_transitions_possible") != 12
        or graph.get("directed_transitions_semantically_reachable") != 10
        or graph.get("structurally_unreachable_transitions") != ["HOLD->DEMOTE", "DEMOTE->HOLD"]
        or coverage.get("authored_profile_difference_rules_covered") != 12
    ):
        fail("transition-graph adequacy binding changed")

    catalog = load_object(CATALOG_PATH)
    if (
        plan["catalog"].get("path") != CATALOG_PATH.relative_to(ROOT).as_posix()
        or plan["catalog"].get("file_sha256") != sha256_file(CATALOG_PATH)
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
        path = baseline_root / f"{comparator_id}-predictions.jsonl"
        if plan["baselines"]["comparators"][comparator_id].get("predictions_sha256") != sha256_file(
            path
        ):
            fail(f"baseline prediction binding changed: {comparator_id}")

    lanes = plan.get("formal_lanes")
    source_lanes = load_object(SOURCE_HOSTED_PLAN).get("formal_lanes")
    if not isinstance(lanes, list) or not isinstance(source_lanes, list) or len(lanes) != 2:
        fail("formal lanes are malformed")
    lane_ids = [str(row["lane_id"]) for row in lanes]
    if (
        lane_ids != plan["execution"].get("base_lane_order")
        or [str(row["model"]) for row in lanes] != ["qwen3.7-max", "deepseek-v4-flash"]
        or any(not lane_id.endswith("minimal-policy-migration-hosted-v1") for lane_id in lane_ids)
    ):
        fail("formal lane identity changed")
    for lane, source_lane in zip(lanes, source_lanes, strict=True):
        lane_payload = {key: value for key, value in lane.items() if key != "lane_id"}
        source_payload = {key: value for key, value in source_lane.items() if key != "lane_id"}
        if lane_payload != source_payload:
            fail("model, adapter, endpoint, or decoding protocol changed")

    design = plan.get("design", {})
    execution = plan.get("execution", {})
    statistics = plan.get("statistics", {})
    if (
        design.get("selected_pairs") != 10
        or design.get("selected_items") != 20
        or design.get("reachable_directed_nonself_transitions_covered") != 10
        or design.get("authored_policy_difference_rules_covered") != 12
        or design.get("planned_model_item_cells") != 40
        or design.get("selection_uses_model_outputs") is not False
        or execution.get("application_posts_per_cell") != 1
        or execution.get("client_retry_count") != 0
        or execution.get("partial_resume") != "FORBIDDEN"
        or execution.get("planned_application_posts") != 40
        or execution.get("resource_exhaustion_eligibility_rule") != RESOURCE_EXHAUSTION_RULE
        or "all 40 terminal outcomes" not in str(plan.get("promotion_rule"))
        or "all 20 items" not in str(statistics.get("strict_smoke_pass_rule"))
    ):
        fail("minimum-study protocol changed")

    selection_path = ROOT / str(plan["selection_receipt"]["path"])
    selection = load_object(selection_path)
    if (
        plan["selection_receipt"].get("file_sha256") != sha256_file(selection_path)
        or plan["selection_receipt"].get("self_digest") != selection.get("self_digest")
        or selection.get("self_digest") != self_digest(selection)
        or selection.get("outcomes_used_for_selection") is not False
        or selection.get("conditional_success_subset_allowed") is not False
        or selection.get("minimal_suite_sha256") != sha256_file(MINIMAL_SUITE_PATH)
        or selection.get("selected_item_ids") != suite.get("selected_item_ids")
        or selection.get("resource_exhaustion_rule") != RESOURCE_EXHAUSTION_RULE
    ):
        fail("preinference selection receipt changed")

    schedule_payload = {key: value for key, value in schedule.items() if key != "schedule_sha256"}
    schedule_hash = sha256_bytes(canonical_json(schedule_payload).encode("utf-8"))
    cells = schedule.get("cells")
    selected_ids = {str(value) for value in suite["selected_item_ids"]}
    if (
        schedule.get("schedule_sha256") != schedule_hash
        or execution.get("schedule_sha256") != schedule_hash
        or execution.get("schedule_path") != schedule_path.relative_to(ROOT).as_posix()
        or schedule.get("packet_sha256") != packet.get("packet_sha256")
        or schedule.get("dataset_fingerprint") != manifest.get("dataset_fingerprint")
        or schedule.get("minimal_suite_sha256") != sha256_file(MINIMAL_SUITE_PATH)
        or not isinstance(cells, list)
        or len(cells) != 40
        or [int(cell["sequence"]) for cell in cells] != list(range(40))
        or len({str(cell["cell_id"]) for cell in cells}) != 40
        or {str(cell["item_id"]) for cell in cells} != selected_ids
        or Counter(str(cell["lane_id"]) for cell in cells)
        != Counter({lane_id: 20 for lane_id in lane_ids})
    ):
        fail("request schedule changed")
    expected_schedule = build_schedule(plan, packet, suite)
    if canonical_json(schedule) != canonical_json(expected_schedule):
        fail("request schedule differs from a clean deterministic rebuild")

    runtime = plan.get("runtime_source_sha256")
    if not isinstance(runtime, dict) or set(runtime) != set(RUNTIME_SOURCES):
        fail("runtime-source inventory changed")
    for path, expected in runtime.items():
        if sha256_file(ROOT / path) != expected:
            fail(f"runtime source changed after freeze: {path}")
    return {
        "status": "MINIMAL_POLICY_MIGRATION_HOSTED_FREEZE_VALID",
        "credentials_loaded": False,
        "dataset": coverage["status"],
        "baselines": baseline["status"],
        "items": 20,
        "pairs": 10,
        "reachable_transitions": 10,
        "changed_rules": 12,
        "lanes": 2,
        "cells": 40,
        "schedule_sha256": schedule_hash,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
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
