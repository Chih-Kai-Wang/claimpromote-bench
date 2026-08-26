#!/usr/bin/env python3
"""Seal results and privacy receipts for the hosted minimum migration study."""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_balanced_public_challenge import derive_reporting_metrics  # noqa: E402
from analyze_minimal_policy_migration_hosted_study import selected_evaluation  # noqa: E402
from finalize_synthetic_policy_results import (  # noqa: E402
    PROVIDER_RESPONSE_PATTERNS,
    SECRET_PATTERNS,
    classify_transport,
    inspect_sensitive,
    self_digest,
    write_json,
)
from validate_minimal_policy_migration_hosted_study import validate_freeze  # noqa: E402

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_with_schema,
)
from claimpromotebench.hashing import canonical_json, sha256_file  # noqa: E402

Json = dict[str, Any]
RUN_SCHEMA = ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json"


def fail(message: str) -> None:
    raise SystemExit(f"minimal-policy-migration-hosted-finalize: {message}")


def finalize(
    plan_path: Path,
    schedule_path: Path,
    dataset_root: Path,
    baseline_root: Path,
    journal_root: Path,
    results_root: Path,
    aggregate_path: Path,
    privacy_path: Path,
    failure_path: Path,
    receipt_path: Path,
    credential_env: str | None,
) -> Json:
    if any(path.exists() for path in (privacy_path, failure_path, receipt_path)):
        fail("refusing to overwrite a finalization receipt")
    validate_freeze(plan_path, schedule_path, dataset_root, baseline_root)
    plan = load_json(plan_path)
    schedule = load_json(schedule_path)
    aggregate = load_json(aggregate_path)
    execution_path = results_root / "execution-receipt.json"
    execution = load_json(execution_path)
    if not all(isinstance(value, dict) for value in (plan, schedule, aggregate, execution)):
        fail("plan, schedule, aggregate, or execution receipt is malformed")
    lane_ids = [str(row["lane_id"]) for row in plan.get("formal_lanes", [])]
    cells = schedule.get("cells")
    if (
        len(lane_ids) != 2
        or lane_ids != plan.get("execution", {}).get("base_lane_order")
        or schedule.get("study_id") != plan.get("study_id")
        or not isinstance(cells, list)
        or len(cells) != 40
        or len({str(cell["cell_id"]) for cell in cells}) != 40
    ):
        fail("plan lane order or request-schedule coverage changed")
    if (
        execution.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or execution.get("study_id") != plan.get("study_id")
        or execution.get("planned_cells") != 40
        or execution.get("durable_request_intents") != 40
        or execution.get("durable_terminal_records") != 40
        or execution.get("application_posts_per_cell") != 1
        or execution.get("client_retry_count") != 0
        or execution.get("partial_resume_used") is not False
        or execution.get("schedule_sha256") != schedule.get("schedule_sha256")
        or execution.get("credentials_retained") is not False
        or execution.get("provider_response_identifiers_retained") is not False
        or execution.get("hidden_reasoning_blocks_retained") is not False
    ):
        fail("execution receipt does not seal the complete 40-cell protocol")
    if (
        aggregate.get("status") != "COMPLETE"
        or aggregate.get("study_id") != plan.get("study_id")
        or aggregate.get("freeze", {}).get("execution_receipt_sha256")
        != sha256_file(execution_path)
    ):
        fail("aggregate does not bind the completed protocol")

    gold, pairs, expected_ids = selected_evaluation(dataset_root)
    aggregate_lanes = {
        str(row["lane_id"]): row for row in aggregate.get("lanes", []) if isinstance(row, dict)
    }
    if set(aggregate_lanes) != set(lane_ids):
        fail("aggregate lane coverage changed")
    all_records: list[Json] = []
    run_files: Json = {}
    for lane_id in lane_ids:
        run_path = results_root / f"{lane_id}.jsonl"
        rows = load_jsonl(run_path)
        if (
            len(rows) != 20
            or {str(row["item_id"]) for row in rows} != expected_ids
            or {str(row["lane_id"]) for row in rows} != {lane_id}
        ):
            fail(f"run does not cover the frozen minimum suite: {lane_id}")
        for row in rows:
            validate_with_schema(row, RUN_SCHEMA, str(row["item_id"]))
        run_sha = sha256_file(run_path)
        if execution.get("lane_output_sha256", {}).get(run_path.name) != run_sha:
            fail(f"execution receipt run digest differs: {lane_id}")
        if aggregate_lanes[lane_id].get("run_sha256") != run_sha:
            fail(f"aggregate run digest differs: {lane_id}")
        metrics = derive_reporting_metrics(gold, pairs, rows)
        if canonical_json(metrics) != canonical_json(aggregate_lanes[lane_id].get("metrics")):
            fail(f"aggregate metrics differ from item-level records: {lane_id}")
        expected_pass = (
            metrics["parseable_items"] == 20
            and metrics["correct_items"] == 20
            and metrics["correct_pairs"] == 10
        )
        if aggregate_lanes[lane_id].get("strict_smoke_gate_pass") is not expected_pass:
            fail(f"strict smoke verdict differs from item-level records: {lane_id}")
        all_records.extend(rows)
        run_files[run_path.name] = run_sha

    intents_path = journal_root / "request-intents.jsonl"
    terminals_path = journal_root / "terminal-records.jsonl"
    intents = load_jsonl(intents_path)
    terminals = load_jsonl(terminals_path)
    if len(intents) != 40 or len(terminals) != 40:
        fail("durable journal does not contain 40 intents and terminal records")
    scheduled_cells = {str(cell["cell_id"]) for cell in cells}
    if {str(row["cell_id"]) for row in intents} != scheduled_cells or {
        str(row["cell_id"]) for row in terminals
    } != scheduled_cells:
        fail("durable journal cell coverage differs from the schedule")
    if execution.get("request_intent_journal_sha256") != sha256_file(intents_path):
        fail("request-intent journal digest differs")
    if execution.get("terminal_journal_sha256") != sha256_file(terminals_path):
        fail("terminal journal digest differs")
    terminal_records = [row.get("record") for row in terminals]
    if any(not isinstance(row, dict) for row in terminal_records):
        fail("terminal journal contains a malformed record")
    terminal_by_cell = {f"{row['lane_id']}\0{row['item_id']}": row for row in terminal_records}
    result_by_cell = {f"{row['lane_id']}\0{row['item_id']}": row for row in all_records}
    if canonical_json(terminal_by_cell) != canonical_json(result_by_cell):
        fail("sealed lane outputs differ from the durable terminal journal")

    findings: Counter[str] = Counter(
        {
            **{name: 0 for name in SECRET_PATTERNS},
            **{name: 0 for name in PROVIDER_RESPONSE_PATTERNS},
            "hidden_reasoning_fields": 0,
            "hidden_reasoning_blocks": 0,
            "hidden_reasoning_text_keys": 0,
            "provider_response_identifiers": 0,
            "exact_supplied_credential": 0,
        }
    )
    supplied_credential: str | None = None
    if credential_env is not None:
        supplied_credential = os.environ.get(credential_env)
        if not supplied_credential or supplied_credential != supplied_credential.strip():
            fail(f"credential environment variable is absent or malformed: {credential_env}")
    scan_paths = (
        plan_path,
        schedule_path,
        intents_path,
        terminals_path,
        execution_path,
        aggregate_path,
        *[results_root / name for name in run_files],
    )
    for path in scan_paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in {**SECRET_PATTERNS, **PROVIDER_RESPONSE_PATTERNS}.items():
            findings[name] += len(pattern.findall(text))
        if supplied_credential is not None:
            findings["exact_supplied_credential"] += text.count(supplied_credential)
    inspect_sensitive(all_records, "terminal records", findings)
    if any(findings.values()):
        fail(f"sensitive-field scan found nonzero counts: {dict(sorted(findings.items()))}")

    failure_counts: Json = {}
    for lane_id in lane_ids:
        rows = [row for row in all_records if row["lane_id"] == lane_id]
        parse_counts = Counter(str(row["parse_status"]) for row in rows)
        transport_categories = Counter(
            classify_transport(row.get("transport_error"))
            for row in rows
            if row.get("transport_status") == "ERROR"
        )
        failure_counts[lane_id] = {
            "terminal_records": 20,
            "parse_status_counts": dict(sorted(parse_counts.items())),
            "transport_failure_categories": dict(sorted(transport_categories.items())),
        }
    failure: Json = {
        "schema_version": "1.0.0",
        "status": "COMPLETE_FROZEN_FAILURE_TAXONOMY",
        "study_id": plan["study_id"],
        "failure_rule": plan["statistics"]["failure_rule"],
        "free_form_error_text_included": False,
        "lanes": failure_counts,
    }
    failure["self_digest"] = self_digest(failure, "self_digest")
    write_json(failure_path, failure)

    privacy: Json = {
        "schema_version": "1.0.0",
        "status": "PRIVATE_RESULTS_VALIDATED_ANONYMOUS_DERIVATIVE_REQUIRED",
        "study_id": plan["study_id"],
        "terminal_records_validated": 40,
        "credentials_included": False,
        "provider_response_identifiers_included": False,
        "hidden_reasoning_fields_included": False,
        "secret_pattern_findings": dict(sorted(findings.items())),
        "private_raw_final_response_text_retained": True,
        "anonymous_raw_final_response_text_allowed": False,
        "anonymous_free_form_error_text_allowed": False,
        "source_repository_or_commit_identity_allowed_in_anonymous_derivative": False,
        "dynamic_file_count_required": True,
        "validated_file_sha256": {
            "aggregate.json": sha256_file(aggregate_path),
            "execution-receipt.json": sha256_file(execution_path),
            **run_files,
        },
    }
    privacy["self_digest"] = self_digest(privacy, "self_digest")
    write_json(privacy_path, privacy)

    result_receipt: Json = {
        "schema_version": "1.0.0",
        "status": "MINIMAL_POLICY_MIGRATION_HOSTED_RESULTS_SEALED",
        "study_id": plan["study_id"],
        "planned_and_terminal_cells": 40,
        "selected_items": 20,
        "selected_pairs": 10,
        "application_posts_per_cell": 1,
        "client_retry_count": 0,
        "plan_sha256": sha256_file(plan_path),
        "schedule_sha256": sha256_file(schedule_path),
        "dataset_manifest_sha256": sha256_file(dataset_root / "manifest.json"),
        "baseline_report_sha256": sha256_file(baseline_root / "report.json"),
        "execution_receipt_sha256": sha256_file(execution_path),
        "aggregate_sha256": sha256_file(aggregate_path),
        "failure_taxonomy_sha256": sha256_file(failure_path),
        "privacy_receipt_sha256": sha256_file(privacy_path),
        "run_sha256": run_files,
        "all_failures_retained_in_end_to_end_denominator": True,
    }
    result_receipt["self_digest"] = self_digest(result_receipt, "self_digest")
    write_json(receipt_path, result_receipt)
    return result_receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--journal-root", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--privacy-out", type=Path, required=True)
    parser.add_argument("--failure-out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    parser.add_argument("--credential-env")
    args = parser.parse_args()
    receipt = finalize(
        args.plan.resolve(),
        args.schedule.resolve(),
        args.dataset_root.resolve(),
        args.baseline_root.resolve(),
        args.journal_root.resolve(),
        args.results_root.resolve(),
        args.aggregate.resolve(),
        args.privacy_out.resolve(),
        args.failure_out.resolve(),
        args.receipt_out.resolve(),
        args.credential_env,
    )
    print(canonical_json({"status": receipt["status"], "study_id": receipt["study_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
