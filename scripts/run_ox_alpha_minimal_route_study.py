#!/usr/bin/env python3
"""Run the frozen 20-cell Ox Alpha minimum-route smoke replay without retries."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from freeze_ox_alpha_minimal_route_study import (  # noqa: E402
    DATASET_ROOT,
    DECISION_SCHEMA,
    EXPECTED_ROOT,
    RUN_SCHEMA,
    request_body,
)
from run_public_model_breadth_study import (  # noqa: E402
    append_durable,
    atomic_output_directory,
    call_openai_compatible,
    sanitize_text,
    verify_frozen_plan,
    write_durable_json,
)
from run_slsa_portability_study import diagnose_content, utc_now  # noqa: E402
from slsa_policy import load_slsa_policy  # noqa: E402
from validate_ox_alpha_minimal_route_study import validate_freeze  # noqa: E402

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_with_schema,
    write_jsonl,
)
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
POLICY_PATH = ROOT / "v2" / "slsa-portability-v1" / "policy-contract.json"


def fail(message: str) -> None:
    raise SystemExit(f"ox-alpha-minimal-route-run: {message}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=EXPECTED_ROOT / "study-plan.json")
    parser.add_argument("--schedule", type=Path, default=EXPECTED_ROOT / "request-schedule.json")
    parser.add_argument("--frozen-plan-commit", required=True)
    parser.add_argument("--journal-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=float)
    args = parser.parse_args()

    os.umask(0o077)
    plan_path = args.plan.resolve()
    schedule_path = args.schedule.resolve()
    frozen_commit = args.frozen_plan_commit.lower()
    verify_frozen_plan(plan_path, frozen_commit)
    validate_freeze(plan_path, schedule_path)
    plan = load_json(plan_path)
    schedule = load_json(schedule_path)
    packet = load_json(DATASET_ROOT / "evaluation-prompt-packet.json")
    api_key = os.environ.get("OPENCODE_GO_API_KEY")
    if not api_key or api_key != api_key.strip():
        fail("OPENCODE_GO_API_KEY is absent or malformed")
    if schedule.get("planned_cells") != 20:
        fail("frozen schedule does not contain 20 cells")

    journal_dir = args.journal_dir.resolve()
    out_dir = args.out_dir.resolve()
    if journal_dir.exists() or out_dir.exists():
        fail("journal or output directory already exists; resume and overwrite are forbidden")
    journal_dir.mkdir(parents=True, mode=0o700)
    intents_path = journal_dir / "request-intents.jsonl"
    terminals_path = journal_dir / "terminal-records.jsonl"
    started_at = utc_now()
    write_durable_json(
        journal_dir / "run-start.json",
        {
            "schema_version": "1.0.0",
            "status": "EXECUTION_STARTED",
            "study_id": plan["study_id"],
            "frozen_plan_commit": frozen_commit,
            "schedule_sha256": schedule["schedule_sha256"],
            "started_at_utc": started_at,
            "planned_cells": 20,
            "credentials_retained": False,
            "hidden_reasoning_retained": False,
            "provider_response_ids_retained": False,
        },
    )

    records_by_id = {str(row["item_id"]): row for row in packet["records"]}
    item_rows = load_jsonl(DATASET_ROOT / "evaluation-items.jsonl")
    items = {str(row["id"]): row["model_visible"] for row in item_rows}
    policy = load_slsa_policy(POLICY_PATH)
    lane = plan["route"]
    timeout = float(
        args.timeout if args.timeout is not None else plan["execution"]["timeout_seconds"]
    )
    minimum_interval = float(plan["execution"]["minimum_global_request_interval_seconds"])
    previous_request_start: float | None = None
    completed: list[Json] = []
    manifest_hash = sha256_file(DATASET_ROOT / "manifest.json")
    response_contract_hash = sha256_bytes(
        canonical_json(
            {
                "mode": lane["response_format"],
                "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
                "single_json_object_extraction": lane["allow_single_json_object_extraction"],
            }
        ).encode("utf-8")
    )

    for cell in schedule["cells"]:
        if previous_request_start is not None:
            remaining = minimum_interval - (time.perf_counter() - previous_request_start)
            if remaining > 0:
                time.sleep(remaining)
        sequence = int(cell["sequence"])
        item_id = str(cell["item_id"])
        packet_record = records_by_id[item_id]
        body = request_body(lane, str(packet_record["prompt"]))
        request_hash = sha256_bytes(canonical_json(body).encode("utf-8"))
        if request_hash != cell["request_body_sha256"]:
            fail(f"request body differs from the frozen schedule: {cell['cell_id']}")

        requested_at = utc_now()
        append_durable(
            intents_path,
            {
                "schema_version": "1.0.0",
                "study_id": plan["study_id"],
                "frozen_plan_commit": frozen_commit,
                "sequence": sequence,
                "cell_id": cell["cell_id"],
                "lane_id": lane["lane_id"],
                "item_id": item_id,
                "request_body_sha256": request_hash,
                "intent_at_utc": requested_at,
                "application_posts_authorized_for_cell": 1,
                "client_retries_authorized": 0,
            },
        )
        previous_request_start = time.perf_counter()
        transport_status = "OK"
        transport_error: str | None = None
        content: str | None = None
        metadata: Json = {"model_returned": None, "finish_reason": None}
        usage: Json = {
            "input_tokens": None,
            "cached_input_tokens": None,
            "output_tokens": None,
            "reasoning_tokens": None,
            "total_tokens": None,
        }
        try:
            observed_metadata, content, usage = call_openai_compatible(lane, body, api_key, timeout)
            metadata = {
                "model_returned": observed_metadata.get("model_returned"),
                "finish_reason": observed_metadata.get("finish_reason"),
            }
        except RuntimeError as exc:
            transport_status = "ERROR"
            transport_error = sanitize_text(str(exc), api_key)
        latency_ms = (time.perf_counter() - previous_request_start) * 1000.0
        response_at = utc_now()
        content = sanitize_text(content, api_key)
        raw_response_hash = sha256_bytes(content.encode("utf-8")) if content is not None else None
        if transport_status == "ERROR":
            parse_status = "TRANSPORT_ERROR"
            parse_detail = transport_error
            raw_decision = None
        elif content is None:
            parse_status = "SCHEMA_ERROR"
            parse_detail = "provider returned no final response text"
            raw_decision = None
        else:
            parse_status, raw_decision, parse_detail = diagnose_content(
                content, items[item_id], policy
            )
            parse_detail = sanitize_text(parse_detail, api_key)
        record: Json = {
            "schema_version": "1.0.0",
            "study_id": plan["study_id"],
            "frozen_plan_commit": frozen_commit,
            "packet_sha256": packet["packet_sha256"],
            "dataset_manifest_sha256": manifest_hash,
            "phase": "full",
            "lane_id": lane["lane_id"],
            "provider": lane["provider"],
            "model_requested": lane["model"],
            "model_returned": metadata["model_returned"],
            "model_identity_status": lane["model_identity_status"],
            "item_id": item_id,
            "pair_id": packet_record["pair_id"],
            "request_sha256": request_hash,
            "prompt_sha256": packet_record["prompt_sha256"],
            "response_contract_sha256": response_contract_hash,
            "finish_reason": metadata["finish_reason"],
            "request_started_at_utc": requested_at,
            "response_received_at_utc": response_at,
            "transport_status": transport_status,
            "transport_error": transport_error,
            "raw_response_text": content,
            "raw_response_sha256": raw_response_hash,
            "parse_status": parse_status,
            "parse_error_detail": parse_detail,
            "raw_decision": raw_decision,
            "latency_ms": latency_ms,
            "usage": usage,
            "actual_cost_usd": 0.0,
            "cost_status": "OFFICIAL_FREE_ROUTE_LISTING",
            "evidence_ceiling": "TIME_STAMPED_ROUTE_SMOKE_ONLY",
        }
        validate_with_schema(record, RUN_SCHEMA, str(cell["cell_id"]))
        append_durable(
            terminals_path,
            {
                "schema_version": "1.0.0",
                "sequence": sequence,
                "cell_id": cell["cell_id"],
                "record": record,
            },
        )
        completed.append(record)
        if (sequence + 1) % 5 == 0 or sequence + 1 == 20:
            print(
                canonical_json(
                    {
                        "status": "RUNNING",
                        "completed_cells": sequence + 1,
                        "planned_cells": 20,
                        "valid_decisions": sum(row["parse_status"] == "OK" for row in completed),
                        "transport_errors": sum(
                            row["transport_status"] == "ERROR" for row in completed
                        ),
                    }
                ),
                flush=True,
            )

    if len(completed) != 20:
        fail("execution ended without every frozen terminal cell")
    with atomic_output_directory(out_dir) as staging:
        run_path = staging / f"{lane['lane_id']}.jsonl"
        write_jsonl(run_path, completed)
        receipt: Json = {
            "schema_version": "1.0.0",
            "status": "COMPLETE_ALL_FROZEN_CELLS_TERMINAL",
            "study_id": plan["study_id"],
            "frozen_plan_commit": frozen_commit,
            "schedule_sha256": schedule["schedule_sha256"],
            "started_at_utc": started_at,
            "completed_at_utc": utc_now(),
            "planned_cells": 20,
            "durable_terminal_records": 20,
            "application_posts": 20,
            "client_retry_count": 0,
            "partial_resume_used": False,
            "route_output_file": run_path.name,
            "route_output_sha256": sha256_file(run_path),
            "valid_decisions": sum(row["parse_status"] == "OK" for row in completed),
            "transport_errors": sum(row["transport_status"] == "ERROR" for row in completed),
            "credentials_retained": False,
            "provider_response_ids_retained": False,
            "hidden_reasoning_retained": False,
            "incremental_cash_cost_usd": 0.0,
        }
        (staging / "execution-receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(
        canonical_json(
            {
                "status": "COMPLETE",
                "records": 20,
                "valid_decisions": sum(row["parse_status"] == "OK" for row in completed),
                "transport_errors": sum(row["transport_status"] == "ERROR" for row in completed),
                "incremental_cash_cost_usd": 0.0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
