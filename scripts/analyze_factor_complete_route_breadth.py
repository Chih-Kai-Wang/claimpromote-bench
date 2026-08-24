#!/usr/bin/env python3
"""Publish privacy-safe metrics for the factor-complete route-breadth study."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_balanced_public_challenge import (  # noqa: E402
    combine_lane_metrics,
    derive_reporting_metrics,
)
from factor_complete_route_breadth import (  # noqa: E402
    CONFIGURATIONS,
    DATASET_ROOT,
    PACKET_PATH,
    REPLICATIONS,
    RUN_SCHEMA,
    STUDY_ID,
    lane_id,
    selected_item_ids,
    selected_pairs,
)
from run_factor_complete_route_breadth import atomic_output_directory  # noqa: E402
from validate_factor_complete_route_breadth import validate_study  # noqa: E402

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_with_schema,
    write_jsonl,
)
from claimpromotebench.hashing import canonical_json, sha256_file  # noqa: E402

Json = dict[str, Any]
_FORBIDDEN_VALUE = re.compile(
    r"(?i)(/Users/|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|"
    r"\b(?:org|user|acct|account)_[A-Za-z0-9_-]{12,}\b|"
    r"\b(?:sk|key|token)-[A-Za-z0-9_-]{16,}\b)"
)


def fail(message: str) -> None:
    raise SystemExit(f"factor-complete-route-breadth-analysis: {message}")


def selected_support() -> tuple[list[Json], list[Json], list[str]]:
    pairs = load_json(DATASET_ROOT / "pairs.json")
    if not isinstance(pairs, list):
        fail("balanced pair file is not a list")
    item_ids = selected_item_ids(pairs)
    selected_pair_rows = selected_pairs(pairs)
    selected_gold = [
        row for row in load_jsonl(DATASET_ROOT / "gold.jsonl") if str(row["id"]) in item_ids
    ]
    if len(selected_gold) != 30:
        fail("selected gold support is incomplete")
    return selected_gold, selected_pair_rows, item_ids


def usage_summary(records: list[Json]) -> Json:
    keys = (
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "total_tokens",
    )
    return {
        key: (
            sum(int(row["usage"][key]) for row in records)
            if all(isinstance(row["usage"][key], int) for row in records)
            else None
        )
        for key in keys
    }


def public_record(record: Json) -> Json:
    sanitized = json.loads(json.dumps(record))
    sanitized["raw_response_text"] = None
    sanitized["provider_response_id"] = None
    sanitized["system_fingerprint"] = None
    if sanitized["transport_error"] is not None:
        sanitized["transport_error"] = "TRANSPORT_ERROR_DETAIL_WITHHELD"
    if sanitized["parse_status"] == "OK":
        detail = sanitized.get("parse_error_detail")
        sanitized["parse_error_detail"] = (
            "DETERMINISTIC_SINGLE_JSON_OBJECT_EXTRACTION"
            if isinstance(detail, str)
            and detail.startswith("DETERMINISTIC_SINGLE_JSON_OBJECT_EXTRACTION")
            else None
        )
    else:
        sanitized["parse_error_detail"] = f"{sanitized['parse_status']}_DETAIL_WITHHELD"
    validate_with_schema(sanitized, RUN_SCHEMA, str(record["item_id"]))
    return sanitized


def stability_metrics(
    records_by_replication: dict[int, list[Json]],
    gold: list[Json],
    pairs: list[Json],
) -> Json:
    gold_by_id = {str(row["id"]): str(row["decision"]["action"]) for row in gold}
    by_replication = {
        replication: {str(row["item_id"]): row for row in records}
        for replication, records in records_by_replication.items()
    }
    item_ids = sorted(gold_by_id)
    all_valid = 0
    same_action = 0
    all_correct = 0
    for item_id in item_ids:
        rows = [by_replication[replication][item_id] for replication in range(1, 4)]
        valid = all(row["parse_status"] == "OK" for row in rows)
        if valid:
            all_valid += 1
            actions = {str(row["raw_decision"]["action"]) for row in rows}
            same_action += len(actions) == 1
        all_correct += all(
            row["parse_status"] == "OK"
            and str(row["raw_decision"]["action"]) == gold_by_id[item_id]
            for row in rows
        )
    all_valid_pairs = 0
    all_correct_pairs = 0
    factor_all_correct: Counter[str] = Counter()
    factor_totals: Counter[str] = Counter()
    for pair in pairs:
        member_ids = [str(value) for value in pair["member_ids"]]
        rows = [
            by_replication[replication][item_id]
            for replication in range(1, 4)
            for item_id in member_ids
        ]
        valid = all(row["parse_status"] == "OK" for row in rows)
        correct = all(
            row["parse_status"] == "OK"
            and str(row["raw_decision"]["action"]) == gold_by_id[str(row["item_id"])]
            for row in rows
        )
        all_valid_pairs += valid
        all_correct_pairs += correct
        factor = str(pair["factor_id"])
        factor_totals[factor] += 1
        factor_all_correct[factor] += correct
    return {
        "items": len(item_ids),
        "all_three_valid_items": all_valid,
        "all_three_valid_item_rate": all_valid / len(item_ids),
        "same_action_among_all_three_valid_items": same_action,
        "same_action_rate_conditional_on_all_three_valid": (
            same_action / all_valid if all_valid else None
        ),
        "all_three_correct_items": all_correct,
        "all_three_correct_item_rate": all_correct / len(item_ids),
        "pairs": len(pairs),
        "all_three_valid_pairs": all_valid_pairs,
        "all_three_valid_pair_rate": all_valid_pairs / len(pairs),
        "all_three_correct_pairs": all_correct_pairs,
        "all_three_correct_pair_rate": all_correct_pairs / len(pairs),
        "factor_all_three_correct": [
            {
                "factor_id": factor,
                "correct_pairs": factor_all_correct[factor],
                "pairs": factor_totals[factor],
            }
            for factor in sorted(factor_totals)
        ],
    }


def validate_lane_records(
    records: list[Json], lane: Json, item_ids: list[str], frozen_commit: str, packet: Json
) -> None:
    if len(records) != 30 or {str(row["item_id"]) for row in records} != set(item_ids):
        fail(f"lane coverage changed: {lane['lane_id']}")
    for index, record in enumerate(records):
        validate_with_schema(record, RUN_SCHEMA, f"{lane['lane_id']}[{index}]")
        if (
            record.get("study_id") != STUDY_ID
            or record.get("frozen_plan_commit") != frozen_commit
            or record.get("packet_sha256") != packet["packet_sha256"]
            or record.get("dataset_manifest_sha256") != packet["dataset_manifest_sha256"]
            or record.get("phase") != "full"
            or record.get("lane_id") != lane["lane_id"]
            or record.get("provider") != lane["provider"]
            or record.get("model_requested") != lane["model"]
            or record.get("model_family") != lane["model_family"]
            or record.get("provider_response_id") is not None
            or record.get("system_fingerprint") is not None
        ):
            fail(f"lane record binding or privacy changed: {lane['lane_id']}[{index}]")


def analyze(
    plan_path: Path,
    schedule_path: Path,
    private_dir: Path,
    output_dir: Path,
) -> Json:
    validate_study(plan_path, schedule_path)
    plan = load_json(plan_path)
    schedule = load_json(schedule_path)
    packet = load_json(PACKET_PATH)
    receipt_path = private_dir / "execution-receipt.json"
    receipt = load_json(receipt_path)
    if (
        receipt.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or receipt.get("study_id") != STUDY_ID
        or receipt.get("schedule_sha256") != schedule["schedule_sha256"]
        or receipt.get("planned_cells") != 630
        or receipt.get("durable_request_intents") != 630
        or receipt.get("durable_terminal_records") != 630
        or receipt.get("application_posts") != 630
        or receipt.get("client_retry_count") != 0
        or receipt.get("partial_resume_used") is not False
        or receipt.get("credentials_retained") is not False
        or receipt.get("provider_response_identifiers_retained") is not False
        or receipt.get("hidden_reasoning_retained") is not False
    ):
        fail("execution receipt is incomplete or changed")
    frozen_commit = str(receipt["frozen_plan_commit"])
    gold, pairs, item_ids = selected_support()
    lane_by_id = {str(row["lane_id"]): row for row in plan["formal_lanes"]}

    records_by_lane: dict[str, list[Json]] = {}
    for current_lane_id, lane in lane_by_id.items():
        path = private_dir / f"{current_lane_id}.jsonl"
        if receipt["lane_output_sha256"].get(path.name) != sha256_file(path):
            fail(f"private lane output digest changed: {path.name}")
        records = load_jsonl(path)
        validate_lane_records(records, lane, item_ids, frozen_commit, packet)
        records_by_lane[current_lane_id] = records

    with atomic_output_directory(output_dir) as staging:
        runs_dir = staging / "runs"
        runs_dir.mkdir(parents=True)
        public_hashes: Json = {}
        configurations: list[Json] = []
        primary_rows: list[Json] = []
        all_private_records: list[Json] = []
        for configuration in CONFIGURATIONS:
            configuration_id = str(configuration["configuration_id"])
            metrics_by_replication: dict[int, Json] = {}
            records_by_replication: dict[int, list[Json]] = {}
            model_returned: set[str] = set()
            routed_providers: set[str] = set()
            configuration_records: list[Json] = []
            for replication in range(1, REPLICATIONS + 1):
                current_lane_id = lane_id(configuration_id, replication)
                records = records_by_lane[current_lane_id]
                records_by_replication[replication] = records
                configuration_records.extend(records)
                all_private_records.extend(records)
                metrics = derive_reporting_metrics(gold, pairs, records)
                metrics_by_replication[replication] = metrics
                model_returned.update(
                    str(row["model_returned"])
                    for row in records
                    if row.get("model_returned") is not None
                )
                routed_providers.update(
                    str(row["routed_provider"])
                    for row in records
                    if row.get("routed_provider") is not None
                )
                public_path = runs_dir / f"{current_lane_id}.jsonl"
                write_jsonl(public_path, [public_record(row) for row in records])
                public_hashes[public_path.name] = sha256_file(public_path)
            pooled = combine_lane_metrics(
                [metrics_by_replication[index] for index in range(1, REPLICATIONS + 1)]
            )
            actual_costs = [
                float(row["actual_cost_usd"])
                for row in configuration_records
                if isinstance(row.get("actual_cost_usd"), (int, float))
            ]
            row = {
                "configuration_id": configuration_id,
                "provider": "OpenCode Go",
                "model_requested": configuration["model"],
                "model_family": configuration["model_family"],
                "api_kind": configuration["api_kind"],
                "output_contract": "PROMPT_ONLY_JSON_WITH_DETERMINISTIC_LOCAL_VALIDATION",
                "max_output_tokens": 4096,
                "model_returned_values": sorted(model_returned),
                "routed_provider_values": sorted(routed_providers),
                "per_replication": [
                    {"replication": index, "metrics": metrics_by_replication[index]}
                    for index in range(1, REPLICATIONS + 1)
                ],
                "pooled_three_replications": pooled,
                "stability": stability_metrics(records_by_replication, gold, pairs),
                "usage": usage_summary(configuration_records),
                "host_usage_derived_quota_value": {
                    "status": (
                        "COMPLETE" if len(actual_costs) == len(configuration_records) else "PARTIAL"
                    ),
                    "actual_cost_usd": sum(actual_costs) if actual_costs else None,
                    "records_with_computed_cost": len(actual_costs),
                    "records": len(configuration_records),
                },
            }
            configurations.append(row)
            primary_rows.append(
                {
                    "source": "NEW_FROZEN_REPLICATION_ONE",
                    "route_id": configuration_id,
                    "model_requested": configuration["model"],
                    "model_family": configuration["model_family"],
                    "metrics": metrics_by_replication[1],
                }
            )

        anchors: list[Json] = []
        for anchor in plan["historical_anchors"]:
            source_path = ROOT / str(anchor["run_path"])
            source_records = load_jsonl(source_path)
            subset = [row for row in source_records if str(row["item_id"]) in item_ids]
            if len(subset) != 30 or {str(row["item_id"]) for row in subset} != set(item_ids):
                fail(f"historical anchor subset is incomplete: {anchor['lane_id']}")
            metrics = derive_reporting_metrics(gold, pairs, subset)
            anchor_row = {
                "source": "HISTORICAL_BALANCED_CHALLENGE_NO_NEW_CALLS",
                "route_id": anchor["lane_id"],
                "model_requested": anchor["model"],
                "model_family": anchor["model_family"],
                "source_run_path": anchor["run_path"],
                "source_run_sha256": sha256_file(source_path),
                "metrics": metrics,
            }
            anchors.append(anchor_row)
            primary_rows.append(anchor_row)

        quota_values = [
            float(row["actual_cost_usd"])
            for row in all_private_records
            if isinstance(row.get("actual_cost_usd"), (int, float))
        ]
        aggregate: Json = {
            "schema_version": "1.0.0",
            "status": "COMPLETE",
            "truth_status": "COMPUTATIONAL",
            "study_id": STUDY_ID,
            "design": "PUBLIC_PRECOMMITTED_FACTOR_COMPLETE_ROUTE_BREADTH",
            "interpretation": (
                "A repeated public route screen over one fixed witness for each of 15 factors; "
                "not a hidden-generalization estimate, deployment study, model ranking, or "
                "causal ablation."
            ),
            "freeze": {
                "frozen_plan_commit": frozen_commit,
                "plan_sha256": sha256_file(plan_path),
                "schedule_sha256": schedule["schedule_sha256"],
                "packet_sha256": packet["packet_sha256"],
                "dataset_manifest_sha256": packet["dataset_manifest_sha256"],
                "execution_receipt_sha256": sha256_file(receipt_path),
            },
            "coverage": {
                "factors": 15,
                "pairs_per_replication": 15,
                "items_per_replication": 30,
                "gold_action_counts_per_replication": {
                    "ALLOW": 15,
                    "HOLD": 5,
                    "DEMOTE": 5,
                    "ESCALATE": 5,
                },
                "new_configurations": len(CONFIGURATIONS),
                "replications_per_new_configuration": REPLICATIONS,
                "historical_anchor_routes": 2,
                "primary_screen_routes": len(primary_rows),
                "unique_model_families_in_primary_screen": len(
                    {str(row["model_family"]) for row in primary_rows}
                ),
            },
            "execution": {
                "scheduled_model_item_cells": 630,
                "application_posts": 630,
                "client_retries": 0,
                "partial_resume_used": False,
                "concurrent_configuration_width": len(CONFIGURATIONS),
            },
            "budget": {
                "billing_mode": "PREEXISTING_SUBSCRIPTION_INCLUDED_QUOTA",
                "incremental_cash_spend_usd": 0.0,
                "host_usage_derived_quota_value_usd": (
                    sum(quota_values) if len(quota_values) == len(all_private_records) else None
                ),
                "records_with_computed_cost": len(quota_values),
                "quota_value_is_not_incremental_cash_spend": True,
            },
            "primary_replication_one_route_screen": sorted(
                primary_rows, key=lambda row: str(row["route_id"])
            ),
            "new_configurations": sorted(
                configurations, key=lambda row: str(row["configuration_id"])
            ),
            "historical_anchors": sorted(anchors, key=lambda row: str(row["route_id"])),
            "deterministic_policy_executor": {
                "end_to_end_item_accuracy": 1.0,
                "end_to_end_pair_accuracy": 1.0,
                "label": "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_EMPIRICAL_BASELINE",
            },
            "service_comparison": {
                "scope": "DESCRIPTIVE_ROUTE_STACKS_ONLY",
                "causal_model_ablation_claimed": False,
                "reason": (
                    "Model, provider, API adapter, serving state, execution time, and output "
                    "implementation are not jointly controlled. Historical anchors were not "
                    "reissued."
                ),
            },
            "failure_rule": plan["statistics"]["failure_rule"],
            "raw_prompts_or_responses_in_aggregate": False,
        }
        aggregate_path = staging / "aggregate.json"
        aggregate_path.write_text(
            json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        public_receipt = json.loads(json.dumps(receipt))
        public_receipt["private_lane_output_sha256_retained"] = False
        public_receipt["lane_output_sha256"] = public_hashes
        public_receipt["public_run_files"] = len(public_hashes)
        public_receipt_path = staging / "execution-receipt.json"
        public_receipt_path.write_text(
            json.dumps(public_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        public_records = [
            row for path in sorted(runs_dir.glob("*.jsonl")) for row in load_jsonl(path)
        ]
        if len(public_records) != 630:
            fail("public derivative does not contain 630 records")
        if any(
            row.get("raw_response_text") is not None
            or row.get("provider_response_id") is not None
            or row.get("system_fingerprint") is not None
            for row in public_records
        ):
            fail("public derivative retains private response material")
        scanned_paths = [aggregate_path, public_receipt_path, *sorted(runs_dir.glob("*.jsonl"))]
        for path in scanned_paths:
            if _FORBIDDEN_VALUE.search(path.read_text(encoding="utf-8")):
                fail(f"public derivative contains a forbidden identity-shaped value: {path.name}")
        privacy: Json = {
            "schema_version": "1.0.0",
            "status": "FACTOR_COMPLETE_ROUTE_BREADTH_PUBLIC_PRIVACY_PASS",
            "study_id": STUDY_ID,
            "files_scanned": len(scanned_paths),
            "public_run_files": len(public_hashes),
            "public_terminal_records": len(public_records),
            "raw_response_text_retained": False,
            "provider_response_identifiers_retained": False,
            "hidden_reasoning_retained": False,
            "account_identifiers_retained": False,
            "credentials_retained": False,
            "aggregate_sha256": sha256_file(aggregate_path),
            "execution_receipt_sha256": sha256_file(public_receipt_path),
            "public_run_sha256": public_hashes,
        }
        (staging / "privacy-receipt.json").write_text(
            json.dumps(privacy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return aggregate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(
        args.plan.resolve(),
        args.schedule.resolve(),
        args.private_dir.resolve(),
        args.out_dir.resolve(),
    )
    print(
        canonical_json(
            {
                "status": result["status"],
                "study_id": result["study_id"],
                "new_configurations": len(result["new_configurations"]),
                "primary_screen_routes": result["coverage"]["primary_screen_routes"],
                "quota_value_usd": result["budget"]["host_usage_derived_quota_value_usd"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
