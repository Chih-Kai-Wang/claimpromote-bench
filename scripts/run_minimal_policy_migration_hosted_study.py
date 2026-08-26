#!/usr/bin/env python3
"""Run the frozen 40-cell hosted minimum policy-migration study without retries."""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from freeze_slsa_portability_study import request_body  # noqa: E402
from run_public_model_breadth_study import (  # noqa: E402
    append_durable,
    atomic_output_directory,
    call_anthropic_messages,
    call_openai_compatible,
    sanitize_text,
    verify_frozen_plan,
    write_durable_json,
)
from run_slsa_portability_study import diagnose_content, utc_now  # noqa: E402
from run_stronger_model_study import actual_cost_usd  # noqa: E402
from slsa_policy import load_slsa_policy  # noqa: E402
from validate_minimal_policy_migration_hosted_study import validate_freeze  # noqa: E402

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_with_schema,
    write_jsonl,
)
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
RUN_SCHEMA = ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json"
DECISION_SCHEMA = ROOT / "v2" / "schemas" / "slsa-agent-decision.schema.json"
BASE_POLICY_PATH = ROOT / "v2" / "slsa-portability-v1" / "policy-contract.json"


def fail(message: str) -> None:
    raise SystemExit(f"minimal-policy-migration-hosted-run: {message}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--frozen-plan-commit", required=True)
    parser.add_argument("--journal-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=float)
    args = parser.parse_args()

    os.umask(0o077)
    plan_path = args.plan.resolve()
    schedule_path = args.schedule.resolve()
    dataset_root = args.dataset_root.resolve()
    baseline_root = args.baseline_root.resolve()
    frozen_commit = args.frozen_plan_commit.lower()
    verify_frozen_plan(plan_path, frozen_commit)
    validate_freeze(plan_path, schedule_path, dataset_root, baseline_root)

    plan = load_json(plan_path)
    schedule = load_json(schedule_path)
    packet = load_json(dataset_root / "evaluation-prompt-packet.json")
    api_key = os.environ.get("OPENCODE_GO_API_KEY")
    if not api_key or api_key != api_key.strip():
        fail("OPENCODE_GO_API_KEY is absent or malformed")
    if schedule.get("planned_cells") != 40:
        fail("frozen schedule does not contain 40 cells")

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
            "planned_cells": 40,
            "credentials_retained": False,
        },
    )

    records_by_id = {str(row["item_id"]): row for row in packet["records"]}
    item_rows = load_jsonl(dataset_root / "evaluation-items.jsonl")
    items = {str(row["id"]): row["model_visible"] for row in item_rows}
    base_policy = load_slsa_policy(BASE_POLICY_PATH)
    lanes = {str(lane["lane_id"]): lane for lane in plan["formal_lanes"]}
    timeout = float(
        args.timeout if args.timeout is not None else plan["execution"]["timeout_seconds"]
    )
    minimum_interval = float(plan["execution"]["minimum_global_request_interval_seconds"])
    previous_request_start: float | None = None
    completed: list[Json] = []
    lane_records: dict[str, list[Json]] = defaultdict(list)
    schema_hash = sha256_file(DECISION_SCHEMA)
    manifest_hash = sha256_file(dataset_root / "manifest.json")

    for cell in schedule["cells"]:
        if previous_request_start is not None:
            remaining = minimum_interval - (time.perf_counter() - previous_request_start)
            if remaining > 0:
                time.sleep(remaining)
        sequence = int(cell["sequence"])
        lane_id = str(cell["lane_id"])
        item_id = str(cell["item_id"])
        lane = lanes[lane_id]
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
                "lane_id": lane_id,
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
        metadata: Json = {
            "model_returned": None,
            "routed_provider": None,
            "finish_reason": None,
        }
        usage: Json = {
            "input_tokens": None,
            "cached_input_tokens": None,
            "output_tokens": None,
            "reasoning_tokens": None,
            "total_tokens": None,
        }
        try:
            if lane["api_kind"] == "openai_compatible":
                metadata, content, usage = call_openai_compatible(lane, body, api_key, timeout)
            elif lane["api_kind"] == "anthropic_messages":
                metadata, content, usage = call_anthropic_messages(lane, body, api_key, timeout)
            else:
                fail(f"unsupported API adapter: {lane['api_kind']}")
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
                content, items[item_id], base_policy
            )
            parse_detail = sanitize_text(parse_detail, api_key)
        quota_value = actual_cost_usd(usage, lane)
        record: Json = {
            "schema_version": "1.0.0",
            "study_id": plan["study_id"],
            "frozen_plan_commit": frozen_commit,
            "packet_sha256": packet["packet_sha256"],
            "dataset_manifest_sha256": manifest_hash,
            "phase": "full",
            "lane_id": lane_id,
            "provider": lane["provider"],
            "model_requested": lane["model"],
            "model_returned": metadata["model_returned"],
            "model_family": lane["model_family"],
            "item_id": item_id,
            "pair_id": packet_record["pair_id"],
            "request_sha256": request_hash,
            "prompt_sha256": packet_record["prompt_sha256"],
            "response_format_sha256": schema_hash,
            "provider_response_id": None,
            "routed_provider": metadata["routed_provider"],
            "system_fingerprint": None,
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
            "postgate_decision": None,
            "latency_ms": latency_ms,
            "usage": usage,
            "actual_cost_usd": quota_value,
            "cost_status": "COMPUTED_FROM_HOST_USAGE" if quota_value is not None else "UNKNOWN",
            "evidence_ceiling": "COMPUTATIONAL",
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
        lane_records[lane_id].append(record)
        if (sequence + 1) % 10 == 0 or sequence + 1 == 40:
            print(
                canonical_json(
                    {
                        "status": "RUNNING",
                        "completed_cells": sequence + 1,
                        "planned_cells": 40,
                        "valid_decisions": sum(row["parse_status"] == "OK" for row in completed),
                        "transport_errors": sum(
                            row["transport_status"] == "ERROR" for row in completed
                        ),
                    }
                ),
                flush=True,
            )

    if len(completed) != 40:
        fail("execution ended without every frozen terminal cell")
    with atomic_output_directory(out_dir) as staging:
        output_hashes: Json = {}
        summaries: list[Json] = []
        for lane_id in plan["execution"]["base_lane_order"]:
            path = staging / f"{lane_id}.jsonl"
            records = lane_records[str(lane_id)]
            if len(records) != 20:
                fail(f"lane does not contain 20 terminal records: {lane_id}")
            write_jsonl(path, records)
            output_hashes[path.name] = sha256_file(path)
            summaries.append(
                {
                    "lane_id": lane_id,
                    "records": len(records),
                    "valid_decisions": sum(row["parse_status"] == "OK" for row in records),
                    "transport_errors": sum(row["transport_status"] == "ERROR" for row in records),
                }
            )
        receipt: Json = {
            "schema_version": "1.0.0",
            "status": "COMPLETE_ALL_FROZEN_CELLS_TERMINAL",
            "study_id": plan["study_id"],
            "frozen_plan_commit": frozen_commit,
            "schedule_sha256": schedule["schedule_sha256"],
            "started_at_utc": started_at,
            "completed_at_utc": utc_now(),
            "planned_cells": 40,
            "durable_request_intents": 40,
            "durable_terminal_records": 40,
            "application_posts_per_cell": 1,
            "client_retry_count": 0,
            "partial_resume_used": False,
            "credentials_retained": False,
            "provider_response_identifiers_retained": False,
            "hidden_reasoning_blocks_retained": False,
            "request_intent_journal_sha256": sha256_file(intents_path),
            "terminal_journal_sha256": sha256_file(terminals_path),
            "lane_output_sha256": output_hashes,
            "lanes": summaries,
        }
        write_durable_json(staging / "execution-receipt.json", receipt)
    print(canonical_json({"status": receipt["status"], "out_dir": str(out_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
