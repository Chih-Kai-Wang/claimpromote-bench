#!/usr/bin/env python3
"""Recompute and validate public external agent-policy revision results."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_external_agent_policy_revision import (  # noqa: E402
    combine_metrics,
    derive_metrics,
    failure_cause_summary,
    selected_support,
)
from analyze_factor_complete_route_breadth import (  # noqa: E402
    stability_metrics,
)
from external_agent_policy_revision import (  # noqa: E402
    CONFIGURATIONS,
    PLANNED_CELLS,
    PLANNED_LANES,
    REPLICATIONS,
    RUN_SCHEMA,
    STUDY_ID,
    lane_id,
)
from validate_external_agent_policy_revision import validate_study  # noqa: E402

from claimpromotebench.dataset import load_json, load_jsonl, validate_with_schema  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise ValueError(f"external agent-policy result validation: {message}")


def validate_results(plan_path: Path, schedule_path: Path, results_dir: Path) -> Json:
    validate_study(plan_path, schedule_path)
    aggregate_path = results_dir / "aggregate.json"
    receipt_path = results_dir / "execution-receipt.json"
    privacy_path = results_dir / "privacy-receipt.json"
    aggregate = load_json(aggregate_path)
    receipt = load_json(receipt_path)
    privacy = load_json(privacy_path)
    if (
        aggregate.get("status") != "COMPLETE"
        or aggregate.get("truth_status") != "COMPUTATIONAL"
        or aggregate.get("study_id") != STUDY_ID
        or aggregate.get("design") != "SOURCE_ANCHORED_EXTERNAL_AGENT_POLICY_REVISION"
        or aggregate.get("coverage", {}).get("external_policy_sources") != 2
        or aggregate.get("coverage", {}).get("pairs_per_replication") != 10
        or aggregate.get("coverage", {}).get("changed_pairs_per_replication") != 6
        or aggregate.get("coverage", {}).get("stable_control_pairs_per_replication") != 4
        or aggregate.get("coverage", {}).get("gold_action_counts_per_replication")
        != {"ALLOW": 14, "HOLD": 3, "DEMOTE": 1, "ESCALATE": 2}
        or aggregate.get("coverage", {}).get("configurations") != len(CONFIGURATIONS)
        or aggregate.get("coverage", {}).get("replications_per_configuration") != REPLICATIONS
        or aggregate.get("execution", {}).get("scheduled_model_item_cells") != PLANNED_CELLS
        or aggregate.get("execution", {}).get("application_posts") != PLANNED_CELLS
        or aggregate.get("execution", {}).get("client_retries") != 0
        or aggregate.get("raw_prompts_or_responses_in_aggregate") is not False
        or aggregate.get("label_definition", {}).get("human_annotators") != 0
        or aggregate.get("label_definition", {}).get("agreement_statistic") is not None
    ):
        fail("aggregate identity or scope changed")
    if (
        receipt.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or receipt.get("study_id") != STUDY_ID
        or receipt.get("planned_cells") != PLANNED_CELLS
        or receipt.get("application_posts") != PLANNED_CELLS
        or receipt.get("client_retry_count") != 0
        or receipt.get("partial_resume_used") is not False
        or receipt.get("credentials_retained") is not False
        or receipt.get("provider_response_identifiers_retained") is not False
        or receipt.get("hidden_reasoning_retained") is not False
        or receipt.get("private_lane_output_sha256_retained") is not False
        or receipt.get("public_run_files") != PLANNED_LANES
    ):
        fail("public execution receipt changed")
    if (
        privacy.get("status") != "EXTERNAL_AGENT_POLICY_PUBLIC_PRIVACY_PASS"
        or privacy.get("study_id") != STUDY_ID
        or privacy.get("public_run_files") != PLANNED_LANES
        or privacy.get("public_terminal_records") != PLANNED_CELLS
        or privacy.get("raw_response_text_retained") is not False
        or privacy.get("provider_response_identifiers_retained") is not False
        or privacy.get("hidden_reasoning_retained") is not False
        or privacy.get("account_identifiers_retained") is not False
        or privacy.get("credentials_retained") is not False
        or privacy.get("aggregate_sha256") != sha256_file(aggregate_path)
        or privacy.get("execution_receipt_sha256") != sha256_file(receipt_path)
    ):
        fail("privacy receipt changed")
    gold, pairs, item_ids = selected_support()
    runs_dir = results_dir / "runs"
    aggregate_by_configuration = {
        str(row["configuration_id"]): row for row in aggregate["configurations"]
    }
    if set(aggregate_by_configuration) != {str(row["configuration_id"]) for row in CONFIGURATIONS}:
        fail("aggregate configuration set changed")
    public_records: list[Json] = []
    expected_hashes: Json = {}
    cost_values: list[float] = []
    for configuration in CONFIGURATIONS:
        configuration_id = str(configuration["configuration_id"])
        aggregate_row = aggregate_by_configuration[configuration_id]
        metrics_by_replication: dict[int, Json] = {}
        records_by_replication: dict[int, list[Json]] = {}
        configuration_records: list[Json] = []
        for replication in range(1, REPLICATIONS + 1):
            current_lane_id = lane_id(configuration_id, replication)
            path = runs_dir / f"{current_lane_id}.jsonl"
            records = load_jsonl(path)
            if len(records) != 20 or {str(row["item_id"]) for row in records} != set(item_ids):
                fail(f"public lane coverage changed: {current_lane_id}")
            for index, record in enumerate(records):
                validate_with_schema(record, RUN_SCHEMA, f"{current_lane_id}[{index}]")
                if (
                    record.get("study_id") != STUDY_ID
                    or record.get("lane_id") != current_lane_id
                    or record.get("model_requested") != configuration["model"]
                    or record.get("model_family") != configuration["model_family"]
                    or record.get("raw_response_text") is not None
                    or record.get("provider_response_id") is not None
                    or record.get("system_fingerprint") is not None
                    or record.get("postgate_decision") is not None
                ):
                    fail(f"public lane binding or privacy changed: {current_lane_id}[{index}]")
                if isinstance(record.get("actual_cost_usd"), (int, float)):
                    cost_values.append(float(record["actual_cost_usd"]))
            public_records.extend(records)
            configuration_records.extend(records)
            records_by_replication[replication] = records
            metrics = derive_metrics(gold, pairs, records)
            metrics_by_replication[replication] = metrics
            reported = next(
                row["metrics"]
                for row in aggregate_row["per_replication"]
                if row["replication"] == replication
            )
            if metrics != reported:
                fail(f"per-replication metrics changed: {current_lane_id}")
            expected_hashes[path.name] = sha256_file(path)
        pooled = combine_metrics(
            [metrics_by_replication[index] for index in range(1, REPLICATIONS + 1)]
        )
        if pooled != aggregate_row["pooled_three_replications"]:
            fail(f"pooled metrics changed: {configuration_id}")
        if stability_metrics(records_by_replication, gold, pairs) != aggregate_row["stability"]:
            fail(f"stability metrics changed: {configuration_id}")
        if failure_cause_summary(configuration_records) != aggregate_row["failure_causes"]:
            fail(f"failure-cause summary changed: {configuration_id}")
    if len(public_records) != PLANNED_CELLS:
        fail("public terminal-record count changed")
    if receipt.get("lane_output_sha256") != expected_hashes:
        fail("public run hashes changed")
    if privacy.get("public_run_sha256") != expected_hashes:
        fail("privacy run hashes changed")
    expected_scanned_files = 2 + len(expected_hashes)
    if privacy.get("files_scanned") != expected_scanned_files:
        fail("privacy file count is stale")
    reported_quota = aggregate.get("budget", {}).get("host_usage_derived_quota_value_usd")
    if len(cost_values) == PLANNED_CELLS:
        if (
            not isinstance(reported_quota, (int, float))
            or abs(float(reported_quota) - sum(cost_values)) > 1e-12
        ):
            fail("host usage-derived quota value changed")
    elif reported_quota is not None:
        fail("partial usage cannot be reported as complete quota value")
    return {
        "status": "EXTERNAL_AGENT_POLICY_RESULTS_VALID",
        "study_id": STUDY_ID,
        "configurations": len(CONFIGURATIONS),
        "public_run_files": len(expected_hashes),
        "public_terminal_records": len(public_records),
        "files_scanned": expected_scanned_files,
        "host_usage_derived_quota_value_usd": reported_quota,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    args = parser.parse_args()
    print(
        canonical_json(
            validate_results(
                args.plan.resolve(), args.schedule.resolve(), args.results_dir.resolve()
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
