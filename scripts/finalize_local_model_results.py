#!/usr/bin/env python3
"""Apply the frozen generic sealer to replacement-v2 local records after execution."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import finalize_synthetic_policy_results as generic  # noqa: E402
from local_model_replication import REPLACEMENT_VERSION, load_object  # noqa: E402

from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
LOCAL_RUN_SCHEMA = ROOT / "v2" / "schemas" / "local-model-run-record.schema.json"
GENERIC_FINALIZER = ROOT / "scripts" / "finalize_synthetic_policy_results.py"


def fail(message: str) -> NoReturn:
    raise SystemExit(f"local-model-finalize: {message}")


def self_digest(value: Json) -> str:
    payload = {key: child for key, child in value.items() if key != "self_digest"}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def validate_post_execution_boundary(plan_path: Path, execution_path: Path) -> Json:
    plan = load_object(plan_path)
    execution = load_object(execution_path)
    runtime = plan.get("freeze", {}).get("runtime_source_sha256")
    if (
        plan.get("status") != "PROSPECTIVELY_FROZEN_LOCAL_MODEL_REPLICATION_REPLACEMENT_V2"
        or plan.get("replacement_version") != REPLACEMENT_VERSION
        or not isinstance(runtime, dict)
        or runtime.get("v2/schemas/local-model-run-record.schema.json")
        != sha256_file(LOCAL_RUN_SCHEMA)
        or runtime.get("scripts/finalize_synthetic_policy_results.py")
        != sha256_file(GENERIC_FINALIZER)
        or plan.get("freeze", {}).get("prior_ineligible_application_invocations") != 1
        or plan.get("freeze", {}).get("prior_durable_terminal_records") != 0
        or plan.get("freeze", {}).get("prior_retained_model_outputs") != 0
    ):
        fail("replacement-v2 frozen source boundary changed")
    if (
        execution.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or execution.get("study_id") != plan.get("study_id")
        or execution.get("replacement_version") != REPLACEMENT_VERSION
        or execution.get("planned_cells") != 240
        or execution.get("durable_terminal_records") != 240
        or execution.get("client_retry_count") != 0
        or execution.get("partial_resume_used") is not False
        or execution.get("prior_ineligible_application_invocations") != 1
    ):
        fail("replacement-v2 execution is not fully terminal")
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
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
    parser.add_argument("--adapter-receipt-out", type=Path, required=True)
    args = parser.parse_args()

    plan_path = args.plan.resolve()
    results_root = args.results_root.resolve()
    plan = validate_post_execution_boundary(plan_path, results_root / "execution-receipt.json")
    # The generic sealer is frozen source. Its only hosted-specific assumption is the record-schema
    # constant; bind it to the separately frozen local-only schema before any validation or scan.
    generic.RUN_SCHEMA = LOCAL_RUN_SCHEMA
    result = generic.finalize(
        plan_path,
        args.schedule.resolve(),
        args.dataset_root.resolve(),
        args.baseline_root.resolve(),
        args.journal_root.resolve(),
        results_root,
        args.aggregate.resolve(),
        args.privacy_out.resolve(),
        args.failure_out.resolve(),
        args.receipt_out.resolve(),
        None,
    )
    adapter: Json = {
        "schema_version": "1.0.0",
        "status": "LOCAL_SCHEMA_POST_EXECUTION_SEAL_VALIDATED",
        "study_id": plan["study_id"],
        "replacement_version": REPLACEMENT_VERSION,
        "generic_finalizer_sha256": sha256_file(GENERIC_FINALIZER),
        "local_run_schema_sha256": sha256_file(LOCAL_RUN_SCHEMA),
        "result_receipt_sha256": sha256_file(args.receipt_out.resolve()),
        "scope": {
            "post_execution_only": True,
            "model_calls_performed": 0,
            "terminal_records_changed": False,
            "structured_decisions_changed": False,
            "metrics_changed": False,
            "source_schema_constant_rebound_to_frozen_local_schema": True,
        },
    }
    adapter["self_digest"] = self_digest(adapter)
    args.adapter_receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.adapter_receipt_out.write_text(
        json.dumps(adapter, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(canonical_json({"status": adapter["status"], "study_id": result["study_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
