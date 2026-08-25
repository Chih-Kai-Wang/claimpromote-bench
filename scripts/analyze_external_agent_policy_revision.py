#!/usr/bin/env python3
"""Publish privacy-safe metrics for the external agent-policy revision study."""

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
from analyze_factor_complete_route_breadth import (  # noqa: E402
    stability_metrics,
    usage_summary,
)
from external_agent_policy_revision import (  # noqa: E402
    CONFIGURATIONS,
    DATASET_ROOT,
    MAX_OUTPUT_TOKENS,
    PACKET_PATH,
    REPLICATIONS,
    RUN_SCHEMA,
    STUDY_ID,
    lane_id,
)
from run_factor_complete_route_breadth import atomic_output_directory  # noqa: E402
from validate_external_agent_policy_revision import validate_study  # noqa: E402

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
    raise SystemExit(f"external-agent-policy-analysis: {message}")


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def selected_support() -> tuple[list[Json], list[Json], list[str]]:
    gold = load_jsonl(DATASET_ROOT / "gold.jsonl")
    pairs = load_json(DATASET_ROOT / "pairs.json")
    if not isinstance(pairs, list) or len(gold) != 20 or len(pairs) != 10:
        fail("external agent-policy support changed")
    return gold, pairs, sorted(str(row["id"]) for row in gold)


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
            if detail == "DETERMINISTIC_SINGLE_JSON_OBJECT_EXTRACTION"
            else None
        )
    else:
        sanitized["parse_error_detail"] = f"{sanitized['parse_status']}_DETAIL_WITHHELD"
    validate_with_schema(sanitized, RUN_SCHEMA, str(record["item_id"]))
    return sanitized


def _pair_subset(
    pairs: list[Json],
    gold_by_id: dict[str, Json],
    record_by_id: dict[str, Json],
    *,
    changed: bool | None = None,
    source_id: str | None = None,
) -> Json:
    selected = [
        pair
        for pair in pairs
        if (changed is None or bool(pair["changed"]) is changed)
        and (source_id is None or pair["source_id"] == source_id)
    ]
    covered = 0
    correct = 0
    exact = 0
    same_action = 0
    for pair in selected:
        members = [str(value) for value in pair["member_ids"]]
        records = [record_by_id[item_id] for item_id in members]
        if not all(row["parse_status"] == "OK" for row in records):
            continue
        covered += 1
        same_action += len({str(row["raw_decision"]["action"]) for row in records}) == 1
        correct += all(
            row["raw_decision"]["action"] == gold_by_id[item_id]["decision"]["action"]
            for item_id, row in zip(members, records, strict=True)
        )
        exact += all(
            row["raw_decision"] == gold_by_id[item_id]["decision"]
            for item_id, row in zip(members, records, strict=True)
        )
    return {
        "pairs": len(selected),
        "covered_pairs": covered,
        "correct_action_pairs": correct,
        "exact_decision_pairs": exact,
        "same_action_pairs": same_action,
        "pair_coverage": _rate(covered, len(selected)),
        "end_to_end_action_pair_accuracy": _rate(correct, len(selected)),
        "conditional_action_pair_accuracy": _rate(correct, covered),
        "end_to_end_exact_pair_accuracy": _rate(exact, len(selected)),
        "conditional_exact_pair_accuracy": _rate(exact, covered),
        "end_to_end_same_action_pair_rate": _rate(same_action, len(selected)),
        "conditional_same_action_pair_rate": _rate(same_action, covered),
    }


def derive_metrics(gold: list[Json], pairs: list[Json], records: list[Json]) -> Json:
    base = derive_reporting_metrics(gold, pairs, records)
    gold_by_id = {str(row["id"]): row for row in gold}
    record_by_id = {str(row["item_id"]): row for row in records}
    exact_items = sum(
        row["parse_status"] == "OK"
        and row["raw_decision"] == gold_by_id[str(row["item_id"])]["decision"]
        for row in records
    )
    supported_actions = sorted({str(row["decision"]["action"]) for row in gold})
    source_ids = sorted({str(pair["source_id"]) for pair in pairs})
    version_rows: list[Json] = []
    for version in ("BEFORE", "AFTER"):
        ids = {str(row["id"]) for row in gold if row["decision"]["policy_version"] == version}
        valid = sum(record_by_id[item_id]["parse_status"] == "OK" for item_id in ids)
        correct = sum(
            record_by_id[item_id]["parse_status"] == "OK"
            and record_by_id[item_id]["raw_decision"]["action"]
            == gold_by_id[item_id]["decision"]["action"]
            for item_id in ids
        )
        version_rows.append(
            {
                "policy_version": version,
                "items": len(ids),
                "parseable_items": valid,
                "correct_action_items": correct,
                "decision_coverage": _rate(valid, len(ids)),
                "end_to_end_action_accuracy": _rate(correct, len(ids)),
                "conditional_action_accuracy": _rate(correct, valid),
            }
        )
    return {
        **base,
        "exact_decision_items": exact_items,
        "end_to_end_exact_decision_accuracy": _rate(exact_items, len(records)),
        "conditional_exact_decision_accuracy": _rate(exact_items, base["parseable_items"]),
        "supported_actions": supported_actions,
        "supported_action_macro_recall": sum(
            base["per_action"][action]["end_to_end_recall"] for action in supported_actions
        )
        / len(supported_actions),
        "changed_pairs": _pair_subset(pairs, gold_by_id, record_by_id, changed=True),
        "stable_control_pairs": _pair_subset(pairs, gold_by_id, record_by_id, changed=False),
        "source_metrics": [
            {
                "source_id": source_id,
                **_pair_subset(pairs, gold_by_id, record_by_id, source_id=source_id),
            }
            for source_id in source_ids
        ],
        "policy_version_metrics": version_rows,
    }


def combine_metrics(metrics: list[Json]) -> Json:
    base = combine_lane_metrics(metrics)
    exact_items = sum(int(row["exact_decision_items"]) for row in metrics)
    supported_actions = list(metrics[0]["supported_actions"])

    def combine_pair_field(name: str) -> Json:
        rows = [row[name] for row in metrics]
        pairs = sum(int(row["pairs"]) for row in rows)
        covered = sum(int(row["covered_pairs"]) for row in rows)
        correct = sum(int(row["correct_action_pairs"]) for row in rows)
        exact = sum(int(row["exact_decision_pairs"]) for row in rows)
        same_action = sum(int(row["same_action_pairs"]) for row in rows)
        return {
            "pairs": pairs,
            "covered_pairs": covered,
            "correct_action_pairs": correct,
            "exact_decision_pairs": exact,
            "same_action_pairs": same_action,
            "pair_coverage": _rate(covered, pairs),
            "end_to_end_action_pair_accuracy": _rate(correct, pairs),
            "conditional_action_pair_accuracy": _rate(correct, covered),
            "end_to_end_exact_pair_accuracy": _rate(exact, pairs),
            "conditional_exact_pair_accuracy": _rate(exact, covered),
            "end_to_end_same_action_pair_rate": _rate(same_action, pairs),
            "conditional_same_action_pair_rate": _rate(same_action, covered),
        }

    source_ids = [str(row["source_id"]) for row in metrics[0]["source_metrics"]]
    source_metrics = []
    for source_id in source_ids:
        rows = [
            next(row for row in metric["source_metrics"] if row["source_id"] == source_id)
            for metric in metrics
        ]
        pairs = sum(int(row["pairs"]) for row in rows)
        covered = sum(int(row["covered_pairs"]) for row in rows)
        correct = sum(int(row["correct_action_pairs"]) for row in rows)
        exact = sum(int(row["exact_decision_pairs"]) for row in rows)
        same_action = sum(int(row["same_action_pairs"]) for row in rows)
        source_metrics.append(
            {
                "source_id": source_id,
                "pairs": pairs,
                "covered_pairs": covered,
                "correct_action_pairs": correct,
                "exact_decision_pairs": exact,
                "same_action_pairs": same_action,
                "pair_coverage": _rate(covered, pairs),
                "end_to_end_action_pair_accuracy": _rate(correct, pairs),
                "conditional_action_pair_accuracy": _rate(correct, covered),
                "end_to_end_exact_pair_accuracy": _rate(exact, pairs),
                "conditional_exact_pair_accuracy": _rate(exact, covered),
                "end_to_end_same_action_pair_rate": _rate(same_action, pairs),
                "conditional_same_action_pair_rate": _rate(same_action, covered),
            }
        )
    return {
        **base,
        "exact_decision_items": exact_items,
        "end_to_end_exact_decision_accuracy": _rate(exact_items, base["items"]),
        "conditional_exact_decision_accuracy": _rate(exact_items, base["parseable_items"]),
        "supported_actions": supported_actions,
        "supported_action_macro_recall": sum(
            base["per_action"][action]["end_to_end_recall"] for action in supported_actions
        )
        / len(supported_actions),
        "changed_pairs": combine_pair_field("changed_pairs"),
        "stable_control_pairs": combine_pair_field("stable_control_pairs"),
        "source_metrics": source_metrics,
    }


def failure_cause_summary(records: list[Json]) -> Json:
    status = Counter(str(row["parse_status"]) for row in records)
    finish_by_status = Counter(
        (str(row["parse_status"]), str(row.get("finish_reason") or "NONE")) for row in records
    )
    return {
        "parse_status_counts": dict(sorted(status.items())),
        "finish_reason_by_parse_status": [
            {"parse_status": key[0], "finish_reason": key[1], "count": count}
            for key, count in sorted(finish_by_status.items())
        ],
        "provider_error_text_released": False,
        "raw_response_text_released": False,
    }


def validate_lane_records(
    records: list[Json], lane: Json, item_ids: list[str], frozen_commit: str, packet: Json
) -> None:
    if len(records) != 20 or {str(row["item_id"]) for row in records} != set(item_ids):
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
            or record.get("postgate_decision") is not None
        ):
            fail(f"lane record binding or privacy changed: {lane['lane_id']}[{index}]")


def analyze(plan_path: Path, schedule_path: Path, private_dir: Path, output_dir: Path) -> Json:
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
        or receipt.get("planned_cells") != 420
        or receipt.get("durable_request_intents") != 420
        or receipt.get("durable_terminal_records") != 420
        or receipt.get("application_posts") != 420
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
            configuration_records: list[Json] = []
            model_returned: set[str] = set()
            routed_providers: set[str] = set()
            for replication in range(1, REPLICATIONS + 1):
                current_lane_id = lane_id(configuration_id, replication)
                records = records_by_lane[current_lane_id]
                records_by_replication[replication] = records
                configuration_records.extend(records)
                all_private_records.extend(records)
                metrics_by_replication[replication] = derive_metrics(gold, pairs, records)
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
            pooled = combine_metrics(
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
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "model_returned_values": sorted(model_returned),
                "routed_provider_values": sorted(routed_providers),
                "per_replication": [
                    {"replication": index, "metrics": metrics_by_replication[index]}
                    for index in range(1, REPLICATIONS + 1)
                ],
                "pooled_three_replications": pooled,
                "stability": stability_metrics(records_by_replication, gold, pairs),
                "failure_causes": failure_cause_summary(configuration_records),
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
                    "source": "FROZEN_REPLICATION_ONE",
                    "route_id": configuration_id,
                    "model_requested": configuration["model"],
                    "model_family": configuration["model_family"],
                    "metrics": metrics_by_replication[1],
                }
            )
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
            "design": "SOURCE_ANCHORED_EXTERNAL_AGENT_POLICY_REVISION",
            "interpretation": (
                "A repeated route study over two independently authored public AGENTS.md "
                "revisions and deterministic author-mapped cases. It does not estimate deployment "
                "effects, prevalence, human agreement, model-family causality, or hidden "
                "generalization."
            ),
            "freeze": {
                "frozen_plan_commit": frozen_commit,
                "plan_sha256": sha256_file(plan_path),
                "schedule_sha256": schedule["schedule_sha256"],
                "packet_sha256": packet["packet_sha256"],
                "dataset_manifest_sha256": packet["dataset_manifest_sha256"],
                "source_receipt_sha256": plan["sources"]["receipt_sha256"],
                "execution_receipt_sha256": sha256_file(receipt_path),
            },
            "coverage": {
                "external_policy_sources": 2,
                "pairs_per_replication": 10,
                "changed_pairs_per_replication": 6,
                "stable_control_pairs_per_replication": 4,
                "items_per_replication": 20,
                "gold_action_counts_per_replication": {
                    "ALLOW": 14,
                    "HOLD": 3,
                    "DEMOTE": 1,
                    "ESCALATE": 2,
                },
                "configurations": len(CONFIGURATIONS),
                "replications_per_configuration": REPLICATIONS,
                "unique_model_families": len({str(row["model_family"]) for row in CONFIGURATIONS}),
            },
            "execution": {
                "scheduled_model_item_cells": 420,
                "application_posts": 420,
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
            "configurations": sorted(configurations, key=lambda row: str(row["configuration_id"])),
            "label_definition": {
                "type": "DETERMINISTIC_AUTHOR_POLICY_MAPPING",
                "human_annotators": 0,
                "agreement_statistic": None,
                "upstream_authors_supplied_labels": False,
            },
            "service_comparison": {
                "scope": "DESCRIPTIVE_ROUTE_STACKS_ONLY",
                "causal_model_ablation_claimed": False,
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
        if len(public_records) != 420:
            fail("public derivative does not contain 420 records")
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
            "status": "EXTERNAL_AGENT_POLICY_PUBLIC_PRIVACY_PASS",
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
                "configurations": len(result["configurations"]),
                "quota_value_usd": result["budget"]["host_usage_derived_quota_value_usd"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
