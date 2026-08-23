#!/usr/bin/env python3
"""Bind the full-study exclusion of the quota-confounded hosted policy-switch run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from finalize_synthetic_policy_results import classify_transport  # noqa: E402

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> NoReturn:
    raise SystemExit(f"policy-switch-hosted-exclusion: {message}")


def self_digest(value: Json) -> str:
    payload = {key: child for key, child in value.items() if key != "self_digest"}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def derive(
    plan_path: Path,
    journal_path: Path,
    results_root: Path,
    local_catalog_path: Path,
) -> Json:
    plan = load_json(plan_path)
    aggregate = load_json(results_root / "aggregate.json")
    execution = load_json(results_root / "execution-receipt.json")
    failure = load_json(results_root / "failure-taxonomy.json")
    privacy = load_json(results_root / "privacy-receipt.json")
    result = load_json(results_root / "result-receipt.json")
    catalog = load_json(local_catalog_path)
    terminals = load_jsonl(journal_path)
    if not all(
        isinstance(value, dict)
        for value in (plan, aggregate, execution, failure, privacy, result, catalog)
    ):
        fail("source evidence is malformed")
    if (
        plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE"
        or execution.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or execution.get("planned_cells") != 240
        or execution.get("durable_terminal_records") != 240
        or execution.get("client_retry_count") != 0
        or aggregate.get("status") != "COMPLETE"
        or failure.get("status") != "COMPLETE_FROZEN_FAILURE_TAXONOMY"
        or privacy.get("status") != "PRIVATE_RESULTS_VALIDATED_ANONYMOUS_DERIVATIVE_REQUIRED"
        or result.get("status") != "SYNTHETIC_POLICY_RESULTS_SEALED"
        or result.get("all_failures_retained_in_end_to_end_denominator") is not True
        or len(terminals) != 240
    ):
        fail("hosted policy-switch seal is incomplete")
    if (
        catalog.get("status") != "PREINFERENCE_LOCAL_MODEL_CATALOG"
        or catalog.get("selection_boundary", {}).get(
            "models_selected_before_any_benchmark_inference"
        )
        is not True
        or catalog.get("selection_boundary", {}).get("benchmark_accuracy_or_labels_consulted")
        is not False
    ):
        fail("local replacement was not selected prospectively")

    records = [row.get("record") for row in terminals]
    if any(not isinstance(row, dict) for row in records):
        fail("terminal journal contains a malformed record")
    quota_sequences = sorted(
        int(terminal["sequence"])
        for terminal, record in zip(terminals, records, strict=True)
        if record.get("transport_status") == "ERROR"
        and classify_transport(record.get("transport_error")) == "QUOTA_OR_RATE_LIMIT"
    )
    server_sequences = sorted(
        int(terminal["sequence"])
        for terminal, record in zip(terminals, records, strict=True)
        if record.get("transport_status") == "ERROR"
        and classify_transport(record.get("transport_error")) == "SERVER"
    )
    valid = sum(record.get("parse_status") == "OK" for record in records)
    semantic = sum(record.get("parse_status") == "SEMANTIC_ERROR" for record in records)
    if len(quota_sequences) != 114 or len(server_sequences) != 1 or valid != 113 or semantic != 12:
        fail("observed hosted failure totals changed")
    if not quota_sequences or quota_sequences[-1] != 239:
        fail("quota failures no longer reach the end of the frozen schedule")

    receipt: Json = {
        "schema_version": "1.0.0",
        "status": "HOSTED_POLICY_SWITCH_EXCLUDED_IN_FULL_SHARED_QUOTA_EXHAUSTION",
        "study_id": plan["study_id"],
        "source_bindings": {
            "plan_sha256": sha256_file(plan_path),
            "aggregate_sha256": sha256_file(results_root / "aggregate.json"),
            "execution_receipt_sha256": sha256_file(results_root / "execution-receipt.json"),
            "failure_taxonomy_sha256": sha256_file(results_root / "failure-taxonomy.json"),
            "privacy_receipt_sha256": sha256_file(results_root / "privacy-receipt.json"),
            "result_receipt_sha256": sha256_file(results_root / "result-receipt.json"),
            "terminal_journal_sha256": sha256_file(journal_path),
            "local_model_catalog_sha256": sha256_file(local_catalog_path),
        },
        "observed_terminal_counts": {
            "scheduled_and_terminal": 240,
            "valid_decisions": valid,
            "semantic_errors": semantic,
            "quota_or_rate_limit_errors": len(quota_sequences),
            "server_errors": len(server_sequences),
            "first_quota_or_rate_limit_sequence": quota_sequences[0],
            "last_quota_or_rate_limit_sequence": quota_sequences[-1],
        },
        "decision": {
            "hosted_model_rows_enter_manuscript": False,
            "successful_row_subset_selected": False,
            "conditional_model_efficacy_interpreted": False,
            "dataset_policy_and_preinference_comparators_retained": True,
            "private_terminal_evidence_retained": True,
            "hosted_study_resumed_or_retried": False,
            "replacement_kind": "PROSPECTIVELY_SELECTED_PINNED_LOCAL_MODEL_REPLICATION",
        },
        "interpretation": (
            "Shared subscription-quota exhaustion persisted through the end of the frozen "
            "schedule and confounds route coverage with request order. The hosted study is "
            "excluded in full; neither its valid subset nor its conditional metrics support "
            "model or policy-conditioning claims."
        ),
        "new_model_calls_performed_for_receipt": 0,
    }
    receipt["self_digest"] = self_digest(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--terminal-journal", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--local-catalog", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    receipt = derive(
        args.plan.resolve(),
        args.terminal_journal.resolve(),
        args.results_root.resolve(),
        args.local_catalog.resolve(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(canonical_json({"status": receipt["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
