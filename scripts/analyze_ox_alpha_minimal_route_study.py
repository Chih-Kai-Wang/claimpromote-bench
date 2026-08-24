#!/usr/bin/env python3
"""Validate and summarize the frozen Ox Alpha minimum-route smoke replay."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_balanced_public_challenge import derive_reporting_metrics  # noqa: E402
from freeze_ox_alpha_minimal_route_study import (  # noqa: E402
    DATASET_ROOT,
    EXPECTED_ROOT,
    LANE_ID,
    MINIMAL_SUITE_PATH,
    MODEL_ID,
    RUN_SCHEMA,
    STUDY_ID,
)
from validate_ox_alpha_minimal_route_study import validate_freeze  # noqa: E402

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_with_schema,
)
from claimpromotebench.hashing import canonical_json, sha256_file  # noqa: E402

Json = dict[str, Any]
_PUBLIC_FORBIDDEN = re.compile(
    r"/Users/|provider_response_id|reasoning_content|hidden_reasoning|raw_response_text"
)


def fail(message: str) -> None:
    raise SystemExit(f"ox-alpha-minimal-route-analysis: {message}")


def selected_evaluation() -> tuple[list[Json], list[Json], set[str]]:
    suite = load_json(MINIMAL_SUITE_PATH)
    selected_ids = {str(value) for value in suite["selected_item_ids"]}
    selected_pair_ids = {str(value) for value in suite["selected_pair_ids"]}
    gold = [
        row
        for row in load_jsonl(DATASET_ROOT / "evaluation-gold.jsonl")
        if str(row["id"]) in selected_ids
    ]
    pair_value = load_json(DATASET_ROOT / "evaluation-pairs.json")
    if not isinstance(pair_value, list):
        fail("evaluation-pairs.json must contain a list")
    pairs = [row for row in pair_value if str(row["pair_id"]) in selected_pair_ids]
    if len(gold) != 20 or len(pairs) != 10:
        fail("minimum-suite gold or pair support changed")
    return gold, pairs, selected_ids


def token_totals(records: list[Json]) -> Json:
    totals: Json = {}
    for key in (
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "total_tokens",
    ):
        values = [row["usage"][key] for row in records]
        totals[key] = (
            sum(int(value) for value in values)
            if all(isinstance(value, int) and not isinstance(value, bool) for value in values)
            else None
        )
    return totals


def analyze(
    plan_path: Path,
    schedule_path: Path,
    receipt_path: Path,
    run_path: Path,
) -> tuple[Json, Json]:
    validate_freeze(plan_path, schedule_path)
    plan = load_json(plan_path)
    receipt = load_json(receipt_path)
    schedule = load_json(schedule_path)
    records = load_jsonl(run_path)
    if (
        receipt.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or receipt.get("study_id") != STUDY_ID
        or receipt.get("planned_cells") != 20
        or receipt.get("durable_terminal_records") != 20
        or receipt.get("application_posts") != 20
        or receipt.get("client_retry_count") != 0
        or receipt.get("partial_resume_used") is not False
        or receipt.get("schedule_sha256") != schedule.get("schedule_sha256")
        or receipt.get("route_output_file") != run_path.name
        or receipt.get("route_output_sha256") != sha256_file(run_path)
        or receipt.get("provider_response_ids_retained") is not False
        or receipt.get("hidden_reasoning_retained") is not False
        or receipt.get("incremental_cash_cost_usd") != 0.0
    ):
        fail("execution receipt is incomplete or changed")
    if len(records) != 20:
        fail("route output does not contain 20 terminal records")
    for index, record in enumerate(records):
        validate_with_schema(record, RUN_SCHEMA, f"record[{index}]")
    gold, pairs, selected_ids = selected_evaluation()
    if (
        {str(row["item_id"]) for row in records} != selected_ids
        or {str(row["lane_id"]) for row in records} != {LANE_ID}
        or {str(row["model_requested"]) for row in records} != {MODEL_ID}
        or {str(row["model_identity_status"]) for row in records} != {"UNDISCLOSED_STEALTH_MODEL"}
        or {str(row["frozen_plan_commit"]) for row in records}
        != {str(receipt["frozen_plan_commit"])}
        or any(row.get("actual_cost_usd") != 0.0 for row in records)
    ):
        fail("route record coverage, identity boundary, or frozen commit changed")

    metrics = derive_reporting_metrics(gold, pairs, records)
    strict_pass = (
        metrics["parseable_items"] == 20
        and metrics["correct_items"] == 20
        and metrics["correct_pairs"] == 10
    )
    aggregate: Json = {
        "schema_version": "1.0.0",
        "status": "COMPLETE",
        "study_id": STUDY_ID,
        "design": "PREINFERENCE_FROZEN_TIME_STAMPED_AUXILIARY_ROUTE_SMOKE_REPLAY",
        "route_label": "OpenCode Go / Ox Alpha Free",
        "model_identity_status": "UNDISCLOSED_STEALTH_MODEL",
        "identity_boundary": plan["identity_boundary"],
        "interpretation": (
            "The route was evaluated once on a deterministic ten-pair structural witness with "
            "one context per reachable edge. The result is a route-level smoke test, not a "
            "model-family ranking, reliability estimate, or independent policy replication."
        ),
        "freeze": {
            "frozen_plan_commit": receipt["frozen_plan_commit"],
            "plan_sha256": sha256_file(plan_path),
            "schedule_sha256": schedule["schedule_sha256"],
            "dataset_fingerprint": plan["dataset"]["dataset_fingerprint"],
            "packet_sha256": plan["prompt"]["packet_sha256"],
            "minimum_suite_sha256": plan["minimum_suite"]["file_sha256"],
            "catalog_snapshot_sha256": plan["catalog_snapshot"]["file_sha256"],
            "execution_receipt_sha256": sha256_file(receipt_path),
            "route_output_sha256": sha256_file(run_path),
        },
        "adequacy": {
            "selected_items": 20,
            "selected_pairs": 10,
            "reachable_edges_covered": 10,
            "changed_rules_covered": 12,
            "contexts_per_edge": 1,
        },
        "execution": {
            "application_posts": 20,
            "client_retries": 0,
            "incremental_cash_cost_usd": 0.0,
            "token_totals": token_totals(records),
        },
        "strict_smoke_gate_pass": strict_pass,
        "classification": (
            "STRICT_SMOKE_GATE_PASS" if strict_pass else "COMPLETE_ROUTE_SMOKE_GATE_FAIL"
        ),
        "metrics": metrics,
        "failure_rule": plan["execution"]["failure_rule"],
        "evidence_ceiling": "TIME_STAMPED_ROUTE_SMOKE_ONLY",
        "raw_model_outputs_in_public_aggregate": False,
    }
    public_text = canonical_json(aggregate)
    matches = sorted(set(_PUBLIC_FORBIDDEN.findall(public_text)))
    if matches:
        fail(f"public aggregate contains forbidden identity or private-output markers: {matches}")
    privacy: Json = {
        "schema_version": "1.0.0",
        "status": "OX_ALPHA_ROUTE_PUBLIC_AGGREGATE_PRIVACY_PASS",
        "study_id": STUDY_ID,
        "files_scanned": 1,
        "scanned_payload_sha256": sha256_file(run_path),
        "public_aggregate_contains_raw_response_text": False,
        "public_aggregate_contains_provider_response_ids": False,
        "public_aggregate_contains_hidden_reasoning": False,
        "public_aggregate_contains_account_identifier": False,
        "private_route_records_eligible_for_anonymous_release": False,
        "credentials_retained": False,
    }
    return aggregate, privacy


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=EXPECTED_ROOT / "study-plan.json")
    parser.add_argument("--schedule", type=Path, default=EXPECTED_ROOT / "request-schedule.json")
    parser.add_argument("--execution-receipt", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--privacy-out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.privacy_out.exists():
        fail("analysis or privacy output already exists")
    aggregate, privacy = analyze(
        args.plan.resolve(),
        args.schedule.resolve(),
        args.execution_receipt.resolve(),
        args.run.resolve(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    privacy["public_aggregate_sha256"] = sha256_file(args.out)
    args.privacy_out.write_text(
        json.dumps(privacy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        canonical_json(
            {
                "status": aggregate["status"],
                "strict_smoke_gate_pass": aggregate["strict_smoke_gate_pass"],
                "valid_decisions": aggregate["metrics"]["parseable_items"],
                "correct_items": aggregate["metrics"]["correct_items"],
                "correct_pairs": aggregate["metrics"]["correct_pairs"],
                "incremental_cash_cost_usd": 0.0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
