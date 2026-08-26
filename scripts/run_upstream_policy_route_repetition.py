#!/usr/bin/env python3
"""Run every frozen upstream-policy route-repetition cell once with durable intents."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from frozen_run_io import (  # noqa: E402
    append_durable,
    atomic_output_directory,
    verify_frozen_plan,
    write_durable_json,
)
from openai_compatible_call import call_openai_compatible  # noqa: E402
from upstream_route_repetition import (  # noqa: E402
    PACKET_PATH,
    RUN_SCHEMA,
    STUDY_ROOT,
    diagnose_response,
    request_body,
    sanitize_error,
    sanitize_response_text,
)
from validate_upstream_policy_route_repetition import validate_freeze  # noqa: E402

from claimpromotebench.dataset import load_json, validate_with_schema, write_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> NoReturn:
    raise SystemExit(f"upstream-route-repetition-run: {message}")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def empty_usage() -> Json:
    return {
        "input_tokens": None,
        "cached_input_tokens": None,
        "output_tokens": None,
        "reasoning_tokens": None,
        "total_tokens": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=STUDY_ROOT / "study-plan.json")
    parser.add_argument("--schedule", type=Path, default=STUDY_ROOT / "request-schedule.json")
    parser.add_argument("--frozen-plan-commit", required=True)
    parser.add_argument("--journal-dir", type=Path, default=STUDY_ROOT / "journal")
    parser.add_argument("--out-dir", type=Path, default=STUDY_ROOT / "private-results")
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
    packet = load_json(PACKET_PATH)
    if not isinstance(plan, dict) or not isinstance(schedule, dict) or not isinstance(packet, dict):
        fail("plan, schedule, and packet must be objects")
    api_key = os.environ.get("OPENCODE_GO_API_KEY")
    if api_key is None or not api_key or api_key != api_key.strip():
        fail("OPENCODE_GO_API_KEY is absent or malformed")

    journal_dir = args.journal_dir.resolve()
    out_dir = args.out_dir.resolve()
    if journal_dir.exists() or out_dir.exists():
        fail("journal or output directory already exists; resume and overwrite are forbidden")
    journal_dir.mkdir(parents=True, mode=0o700)
    intents_path = journal_dir / "request-intents.jsonl"
    terminals_path = journal_dir / "terminal-records.jsonl"
    started_at = utc_now()
    planned_cells = int(schedule["planned_cells"])
    write_durable_json(
        journal_dir / "run-start.json",
        {
            "schema_version": "1.0.0",
            "status": "EXECUTION_STARTED",
            "study_id": plan["study_id"],
            "frozen_plan_commit": frozen_commit,
            "schedule_sha256": schedule["schedule_sha256"],
            "started_at_utc": started_at,
            "planned_cells": planned_cells,
            "application_posts_per_cell": 1,
            "client_retries_authorized": 0,
            "credentials_retained": False,
            "provider_response_ids_retained": False,
            "hidden_reasoning_retained": False,
        },
    )

    packet_by_id = {str(row["item_id"]): row for row in packet["records"]}
    lane_by_id = {str(row["lane_id"]): row for row in plan["formal_lanes"]}
    response_contract_sha = sha256_bytes(canonical_json(plan["response_contract"]).encode("utf-8"))
    timeout = float(
        args.timeout if args.timeout is not None else plan["execution"]["default_timeout_seconds"]
    )
    minimum_interval = float(plan["execution"]["minimum_global_request_interval_seconds"])
    previous_request_start: float | None = None
    completed: list[Json] = []
    grouped: dict[tuple[str, int], list[Json]] = defaultdict(list)

    for cell in schedule["cells"]:
        if previous_request_start is not None:
            remaining = minimum_interval - (time.perf_counter() - previous_request_start)
            if remaining > 0:
                time.sleep(remaining)
        sequence = int(cell["sequence"])
        cell_id = str(cell["cell_id"])
        lane_id = str(cell["lane_id"])
        repetition = int(cell["repetition"])
        item_id = str(cell["item_id"])
        lane = lane_by_id[lane_id]
        packet_record = packet_by_id[item_id]
        body = request_body(lane, str(packet_record["prompt"]))
        request_sha = sha256_bytes(canonical_json(body).encode("utf-8"))
        if request_sha != cell["request_body_sha256"]:
            fail(f"request body differs from the frozen schedule: {cell_id}")

        requested_at = utc_now()
        append_durable(
            intents_path,
            {
                "schema_version": "1.0.0",
                "study_id": plan["study_id"],
                "frozen_plan_commit": frozen_commit,
                "sequence": sequence,
                "cell_id": cell_id,
                "repetition": repetition,
                "lane_id": lane_id,
                "item_id": item_id,
                "request_body_sha256": request_sha,
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
        usage = empty_usage()
        try:
            metadata, content, usage = call_openai_compatible(lane, body, api_key, timeout)
        except RuntimeError as exc:
            transport_status = "ERROR"
            transport_error = sanitize_error(str(exc), api_key)
        latency_ms = (time.perf_counter() - previous_request_start) * 1000.0
        response_at = utc_now()
        content = sanitize_response_text(content, api_key)
        if transport_status == "ERROR":
            parse_status = "TRANSPORT_ERROR"
            action = None
            full_decision = None
            parse_detail = transport_error
        elif content is None:
            parse_status = "SCHEMA_ERROR"
            action = None
            full_decision = None
            parse_detail = "provider returned no final response text"
        else:
            parse_status, action, full_decision, parse_detail = diagnose_response(content)
            parse_detail = sanitize_error(parse_detail, api_key)
        record: Json = {
            "schema_version": "1.0.0",
            "study_id": plan["study_id"],
            "frozen_plan_commit": frozen_commit,
            "schedule_sha256": schedule["schedule_sha256"],
            "packet_sha256": packet["packet_sha256"],
            "sequence": sequence,
            "cell_id": cell_id,
            "repetition": repetition,
            "lane_id": lane_id,
            "provider": lane["provider"],
            "model_requested": lane["model"],
            "model_returned": metadata["model_returned"],
            "model_family": lane["model_family"],
            "routed_provider": metadata["routed_provider"],
            "item_id": item_id,
            "pair_id": packet_record["pair_id"],
            "request_sha256": request_sha,
            "prompt_sha256": packet_record["prompt_sha256"],
            "response_contract_sha256": response_contract_sha,
            "finish_reason": metadata["finish_reason"],
            "request_started_at_utc": requested_at,
            "response_received_at_utc": response_at,
            "transport_status": transport_status,
            "transport_error": transport_error,
            "raw_response_text": content,
            "raw_response_sha256": (
                sha256_bytes(content.encode("utf-8")) if content is not None else None
            ),
            "action_extraction_status": "EXTRACTED" if action is not None else "UNEXTRACTABLE",
            "extracted_action": action,
            "parse_status": parse_status,
            "parse_error_detail": parse_detail,
            "full_decision": full_decision,
            "latency_ms": latency_ms,
            "usage": usage,
            "billing_mode": lane["billing_mode"],
            "provider_response_id_retained": False,
            "hidden_reasoning_retained": False,
            "evidence_ceiling": "TIME_STAMPED_ROUTE_REPETITION",
        }
        validate_with_schema(record, RUN_SCHEMA, cell_id)
        append_durable(
            terminals_path,
            {
                "schema_version": "1.0.0",
                "sequence": sequence,
                "cell_id": cell_id,
                "record": record,
            },
        )
        completed.append(record)
        grouped[(lane_id, repetition)].append(record)
        if (sequence + 1) % 12 == 0 or sequence + 1 == planned_cells:
            print(
                canonical_json(
                    {
                        "status": "RUNNING",
                        "completed_cells": sequence + 1,
                        "planned_cells": planned_cells,
                        "action_extractable": sum(
                            row["action_extraction_status"] == "EXTRACTED" for row in completed
                        ),
                        "contract_valid": sum(row["parse_status"] == "OK" for row in completed),
                        "transport_errors": sum(
                            row["transport_status"] == "ERROR" for row in completed
                        ),
                    }
                ),
                flush=True,
            )

    if len(completed) != planned_cells:
        fail("execution ended without every frozen terminal cell")
    with atomic_output_directory(out_dir) as staging:
        outputs: list[Json] = []
        for lane_id in plan["execution"].get(
            "base_lane_order", [str(row["lane_id"]) for row in plan["formal_lanes"]]
        ):
            for repetition in range(1, 4):
                records = grouped[(str(lane_id), repetition)]
                if len(records) != 24:
                    fail(
                        "route repetition lacks twenty-four terminal records: "
                        f"{lane_id}/r{repetition}"
                    )
                path = staging / f"{lane_id}-r{repetition}.jsonl"
                write_jsonl(path, records)
                outputs.append(
                    {
                        "lane_id": lane_id,
                        "repetition": repetition,
                        "file": path.name,
                        "records": len(records),
                        "sha256": sha256_file(path),
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
            "planned_cells": planned_cells,
            "durable_intents": planned_cells,
            "durable_terminal_records": planned_cells,
            "application_posts": planned_cells,
            "client_retry_count": 0,
            "partial_resume_used": False,
            "outputs": outputs,
            "action_extractable": sum(
                row["action_extraction_status"] == "EXTRACTED" for row in completed
            ),
            "contract_valid": sum(row["parse_status"] == "OK" for row in completed),
            "transport_errors": sum(row["transport_status"] == "ERROR" for row in completed),
            "credentials_retained": False,
            "provider_response_ids_retained": False,
            "hidden_reasoning_retained": False,
            "workflow_initiated_purchase_or_recharge": False,
        }
        (staging / "execution-receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(
        canonical_json(
            {
                "status": "COMPLETE",
                "records": planned_cells,
                "action_extractable": receipt["action_extractable"],
                "contract_valid": receipt["contract_valid"],
                "transport_errors": receipt["transport_errors"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
