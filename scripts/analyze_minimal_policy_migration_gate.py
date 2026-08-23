#!/usr/bin/env python3
"""Score a prospectively selected minimum policy-migration subset without new route calls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_balanced_public_challenge import derive_reporting_metrics  # noqa: E402

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> NoReturn:
    raise SystemExit(f"minimum-policy-migration-gate: {message}")


def self_digest(value: Json) -> str:
    payload = {key: child for key, child in value.items() if key != "self_digest"}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def bound_path(plan: Json, key: str) -> Path:
    bindings = plan.get("source_bindings")
    if not isinstance(bindings, dict) or not isinstance(bindings.get(key), dict):
        fail(f"analysis plan lacks source binding: {key}")
    binding = bindings[key]
    path = ROOT / str(binding.get("path"))
    if not path.is_file() or binding.get("sha256") != sha256_file(path):
        fail(f"analysis source binding changed: {key}")
    return path


def strict_gate_pass(metrics: Json) -> bool:
    return (
        metrics.get("items") == 20
        and metrics.get("pairs") == 10
        and metrics.get("parseable_items") == 20
        and metrics.get("correct_items") == 20
        and metrics.get("covered_pairs") == 10
        and metrics.get("correct_pairs") == 10
    )


def analyze(plan_path: Path, results_root: Path) -> Json:
    plan = load_json(plan_path)
    if (
        plan.get("status") != "PROSPECTIVELY_FROZEN_MINIMUM_MIGRATION_SUBSET_ANALYSIS"
        or plan.get("selection", {}).get("model_outputs_consulted") is not False
        or plan.get("selection", {}).get("selected_before_route_execution") is not True
        or plan.get("execution", {}).get("additional_model_or_client_calls") != 0
        or plan.get("gate", {}).get("pass_rule")
        != "ALL_20_ITEMS_VALID_AND_CORRECT_AND_ALL_10_PAIRS_CORRECT"
    ):
        fail("analysis plan boundary changed")

    minimum_path = bound_path(plan, "minimum_suite")
    gold_path = bound_path(plan, "evaluation_gold")
    pairs_path = bound_path(plan, "evaluation_pairs")
    local_plan_path = bound_path(plan, "local_study_plan")
    schedule_path = bound_path(plan, "local_request_schedule")
    script_binding = plan.get("source_bindings", {}).get("analysis_script", {})
    if script_binding.get("sha256") != sha256_file(Path(__file__).resolve()):
        fail("analysis script changed after freeze")

    minimum = load_json(minimum_path)
    local_plan = load_json(local_plan_path)
    schedule = load_json(schedule_path)
    execution_path = results_root / "execution-receipt.json"
    execution = load_json(execution_path)
    if (
        execution.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or execution.get("study_id") != local_plan.get("study_id")
        or execution.get("planned_cells") != 240
        or execution.get("durable_terminal_records") != 240
        or execution.get("client_retry_count") != 0
        or execution.get("partial_resume_used") is not False
        or execution.get("schedule_sha256") != schedule.get("schedule_sha256")
    ):
        fail("full transition-graph execution is not sealed")

    selected_items = tuple(str(value) for value in minimum.get("selected_item_ids", []))
    selected_pairs = tuple(str(value) for value in minimum.get("selected_pair_ids", []))
    if (
        selected_items != tuple(plan.get("selection", {}).get("selected_item_ids", []))
        or selected_pairs != tuple(plan.get("selection", {}).get("selected_pair_ids", []))
        or len(selected_items) != 20
        or len(set(selected_items)) != 20
        or len(selected_pairs) != 10
        or len(set(selected_pairs)) != 10
    ):
        fail("minimum-suite selection changed")

    full_gold = load_jsonl(gold_path)
    full_pairs = load_json(pairs_path)
    if not isinstance(full_pairs, list):
        fail("evaluation pairs must be a list")
    full_item_ids = {str(row["id"]) for row in full_gold}
    subset_gold = [row for row in full_gold if str(row["id"]) in set(selected_items)]
    subset_pairs = [row for row in full_pairs if str(row["pair_id"]) in set(selected_pairs)]
    if len(full_gold) != 120 or len(full_pairs) != 60:
        fail("full transition graph changed")
    if len(subset_gold) != 20 or len(subset_pairs) != 10:
        fail("minimum subset does not resolve against the frozen graph")

    output_hashes = execution.get("lane_output_sha256")
    if not isinstance(output_hashes, dict):
        fail("execution receipt lacks lane output hashes")
    lanes: list[Json] = []
    for lane in local_plan.get("formal_lanes", []):
        lane_id = str(lane["lane_id"])
        run_path = results_root / f"{lane_id}.jsonl"
        records = load_jsonl(run_path)
        if (
            len(records) != 120
            or {str(row["item_id"]) for row in records} != full_item_ids
            or output_hashes.get(run_path.name) != sha256_file(run_path)
        ):
            fail(f"sealed full-lane records changed: {lane_id}")
        subset_records = [row for row in records if str(row["item_id"]) in set(selected_items)]
        if len(subset_records) != 20:
            fail(f"minimum subset lane coverage changed: {lane_id}")
        metrics = derive_reporting_metrics(subset_gold, subset_pairs, subset_records)
        lanes.append(
            {
                "lane_id": lane_id,
                "model_family": lane["model_family"],
                "full_run_sha256": sha256_file(run_path),
                "metrics": metrics,
                "strict_gate_pass": strict_gate_pass(metrics),
            }
        )

    result: Json = {
        "schema_version": "1.0.0",
        "status": "COMPLETE_PROSPECTIVE_MINIMUM_MIGRATION_SUBSET_ANALYSIS",
        "truth_status": "COMPUTATIONAL",
        "study_id": local_plan["study_id"],
        "analysis_plan_sha256": sha256_file(plan_path),
        "minimum_suite_sha256": sha256_file(minimum_path),
        "execution_receipt_sha256": sha256_file(execution_path),
        "selection": {
            "selected_pair_ids": list(selected_pairs),
            "selected_item_ids": list(selected_items),
            "pairs": 10,
            "items": 20,
            "changed_rules_covered": 12,
            "reachable_edges_covered": 10,
            "selected_before_route_execution": True,
            "model_outputs_consulted": False,
        },
        "gate": {
            "pass_rule": "ALL_20_ITEMS_VALID_AND_CORRECT_AND_ALL_10_PAIRS_CORRECT",
            "failure_rule": "EVERY_SERVICE_SYNTAX_SCHEMA_OR_SEMANTIC_FAILURE_IS_INCORRECT",
        },
        "lanes": sorted(lanes, key=lambda row: str(row["lane_id"])),
        "scope": {
            "additional_model_or_client_calls": 0,
            "reuses_full_transition_graph_terminal_records": True,
            "independent_model_sample": False,
            "natural_input_distribution_claimed": False,
            "deployment_reliability_claimed": False,
            "replaces_balanced_diagnostic_suite": False,
        },
    }
    result["self_digest"] = self_digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.plan.resolve(), args.results_root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(canonical_json({"status": result["status"], "lanes": len(result["lanes"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
