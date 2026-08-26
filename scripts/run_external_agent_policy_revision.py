#!/usr/bin/env python3
"""Execute the frozen external agent-policy schedule once, without retries."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from itertools import groupby
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from external_agent_policy_revision import (  # noqa: E402
    DATASET_ROOT,
    DECISION_SCHEMA,
    PACKET_PATH,
    RUN_SCHEMA,
    STUDY_ID,
    request_body,
)
from run_factor_complete_route_breadth import (  # noqa: E402
    append_durable,
    atomic_output_directory,
    empty_usage,
    utc_now,
    write_durable_json,
)
from run_public_model_breadth_study import (  # noqa: E402
    call_anthropic_messages,
    call_openai_compatible,
    sanitize_text,
    verify_frozen_plan,
)
from run_stronger_model_study import (  # noqa: E402
    actual_cost_usd,
    call_openai_responses,
    extract_single_json_object,
    validate_api_key,
)
from validate_external_agent_policy_revision import validate_study  # noqa: E402

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_with_schema,
    write_jsonl,
)
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]

_ACTION_BY_REASON = {
    "POLICY_SATISFIED": "ALLOW",
    "DEPENDENCY_NOT_EXPLOITABLE": "DEMOTE",
    "SECURITY_REVIEW_REQUIRED": "ESCALATE",
    "BREAKING_INTERFACE_CHANGE": "HOLD",
    "PUBLIC_SYMBOL_RENAME_FORBIDDEN": "HOLD",
    "PUBLIC_HOOK_ARGUMENT_REMOVAL": "HOLD",
    "BC_IMPACT_REVIEW_REQUIRED": "ESCALATE",
}


def fail(message: str) -> None:
    raise SystemExit(f"external-agent-policy-run: {message}")


def diagnose(content: str, item: Json) -> tuple[str, Json | None, str | None]:
    parse_text = content
    extraction_used = False
    try:
        value = json.loads(parse_text)
    except json.JSONDecodeError as first_error:
        extracted = extract_single_json_object(content)
        if extracted is None:
            return (
                "JSON_SYNTAX_ERROR",
                None,
                f"{first_error.msg} at line {first_error.lineno} column {first_error.colno}",
            )
        parse_text = extracted
        extraction_used = True
        try:
            value = json.loads(parse_text)
        except json.JSONDecodeError as exc:
            return (
                "JSON_SYNTAX_ERROR",
                None,
                f"{exc.msg} at line {exc.lineno} column {exc.colno}",
            )
    if not isinstance(value, dict):
        return "SCHEMA_ERROR", None, "top-level JSON value is not an object"
    try:
        validate_with_schema(value, DECISION_SCHEMA, "external agent-policy decision")
    except Exception as exc:
        return "SCHEMA_ERROR", None, str(exc)
    if value["case_id"] != item["case_id"]:
        return "SEMANTIC_ERROR", None, "case_id does not match the requested case"
    if value["policy_version"] != item["policy_version"]:
        return "SEMANTIC_ERROR", None, "policy_version does not match the active source"
    reasons = set(value["reason_codes"])
    if any(_ACTION_BY_REASON[reason] != value["action"] for reason in reasons):
        return "SEMANTIC_ERROR", None, "action and reason_codes are inconsistent"
    detail = "DETERMINISTIC_SINGLE_JSON_OBJECT_EXTRACTION" if extraction_used else None
    return "OK", value, detail


def execute_cell(
    cell: Json,
    lane: Json,
    packet_row: Json,
    item: Json,
    api_key: str,
    timeout: float,
    frozen_commit: str,
    packet: Json,
    response_contract_sha256: str,
) -> Json:
    body = request_body(lane, str(packet_row["prompt"]))
    request_sha = sha256_bytes(canonical_json(body).encode("utf-8"))
    if request_sha != cell["request_body_sha256"]:
        raise RuntimeError(f"request body differs from frozen cell {cell['cell_id']}")
    started_at = utc_now()
    started = time.perf_counter()
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
        if lane["api_kind"] == "openai_compatible":
            metadata, content, usage = call_openai_compatible(lane, body, api_key, timeout)
        elif lane["api_kind"] == "anthropic_messages":
            metadata, content, usage = call_anthropic_messages(lane, body, api_key, timeout)
        elif lane["api_kind"] == "openai_responses":
            observed, content, usage = call_openai_responses(lane, body, api_key, timeout)
            metadata = {
                "model_returned": observed.get("model_returned"),
                "routed_provider": observed.get("routed_provider"),
                "finish_reason": observed.get("finish_reason"),
            }
        else:
            raise RuntimeError(f"unsupported adapter: {lane['api_kind']}")
    except RuntimeError as exc:
        transport_status = "ERROR"
        transport_error = sanitize_text(str(exc), api_key)
    latency_ms = (time.perf_counter() - started) * 1000.0
    response_at = utc_now()
    content = sanitize_text(content, api_key)
    raw_response_sha = sha256_bytes(content.encode("utf-8")) if content is not None else None
    if transport_status == "ERROR":
        parse_status = "TRANSPORT_ERROR"
        parse_detail = transport_error
        raw_decision = None
    elif content is None:
        parse_status = "SCHEMA_ERROR"
        parse_detail = "provider returned no final response text"
        raw_decision = None
    else:
        parse_status, raw_decision, parse_detail = diagnose(content, item)
        parse_detail = sanitize_text(parse_detail, api_key)
    quota_value = actual_cost_usd(usage, lane)
    record: Json = {
        "schema_version": "1.0.0",
        "study_id": STUDY_ID,
        "frozen_plan_commit": frozen_commit,
        "packet_sha256": packet["packet_sha256"],
        "dataset_manifest_sha256": packet["dataset_manifest_sha256"],
        "phase": "full",
        "lane_id": lane["lane_id"],
        "provider": lane["provider"],
        "model_requested": lane["model"],
        "model_returned": metadata["model_returned"],
        "model_family": lane["model_family"],
        "item_id": cell["item_id"],
        "pair_id": cell["pair_id"],
        "request_sha256": request_sha,
        "prompt_sha256": packet_row["prompt_sha256"],
        "response_format_sha256": response_contract_sha256,
        "provider_response_id": None,
        "routed_provider": metadata["routed_provider"],
        "system_fingerprint": None,
        "finish_reason": metadata["finish_reason"],
        "request_started_at_utc": started_at,
        "response_received_at_utc": response_at,
        "transport_status": transport_status,
        "transport_error": transport_error,
        "raw_response_text": content,
        "raw_response_sha256": raw_response_sha,
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
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
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
    validate_study(plan_path, schedule_path)
    plan = load_json(plan_path)
    schedule = load_json(schedule_path)
    packet = load_json(PACKET_PATH)
    api_key = validate_api_key(os.environ.get("OPENCODE_GO_API_KEY"), "OPENCODE_GO_API_KEY")
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
            "study_id": STUDY_ID,
            "frozen_plan_commit": frozen_commit,
            "schedule_sha256": schedule["schedule_sha256"],
            "started_at_utc": started_at,
            "planned_cells": schedule["planned_cells"],
            "credentials_retained": False,
            "provider_response_identifiers_retained": False,
            "hidden_reasoning_retained": False,
        },
    )
    packet_by_id = {str(row["item_id"]): row for row in packet["records"]}
    items = {str(row["id"]): row for row in load_jsonl(DATASET_ROOT / "inputs.jsonl")}
    lanes = {str(row["lane_id"]): row for row in plan["formal_lanes"]}
    timeout = float(
        args.timeout if args.timeout is not None else plan["execution"]["default_timeout_seconds"]
    )
    max_workers = int(plan["execution"]["max_concurrent_requests"])
    minimum_interval = float(plan["execution"]["minimum_inter_group_interval_seconds"])
    response_contract_sha256 = sha256_bytes(
        canonical_json(
            {
                "mode": "prompt_only_json",
                "single_json_object_extraction": True,
                "decision_schema_sha256": sha256_file(DECISION_SCHEMA),
                "max_output_tokens": plan["budget"]["max_output_tokens_per_call"],
            }
        ).encode("utf-8")
    )
    completed: list[Json] = []
    lane_records: dict[str, list[Json]] = defaultdict(list)
    grouped = groupby(schedule["cells"], key=lambda row: int(row["group_index"]))
    previous_group_start: float | None = None
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for group_index, group_iter in grouped:
            group = list(group_iter)
            if previous_group_start is not None:
                remaining = minimum_interval - (time.perf_counter() - previous_group_start)
                if remaining > 0:
                    time.sleep(remaining)
            previous_group_start = time.perf_counter()
            futures: dict[Future[Json], Json] = {}
            for cell in group:
                current_lane = lanes[str(cell["lane_id"])]
                packet_row = packet_by_id[str(cell["item_id"])]
                body = request_body(current_lane, str(packet_row["prompt"]))
                request_sha = sha256_bytes(canonical_json(body).encode("utf-8"))
                append_durable(
                    intents_path,
                    {
                        "schema_version": "1.0.0",
                        "study_id": STUDY_ID,
                        "frozen_plan_commit": frozen_commit,
                        "sequence": cell["sequence"],
                        "group_index": group_index,
                        "cell_id": cell["cell_id"],
                        "lane_id": cell["lane_id"],
                        "item_id": cell["item_id"],
                        "request_body_sha256": request_sha,
                        "intent_at_utc": utc_now(),
                        "application_posts_authorized_for_cell": 1,
                        "client_retries_authorized": 0,
                    },
                )
                future = executor.submit(
                    execute_cell,
                    cell,
                    current_lane,
                    packet_row,
                    items[str(cell["item_id"])],
                    api_key,
                    timeout,
                    frozen_commit,
                    packet,
                    response_contract_sha256,
                )
                futures[future] = cell
            for future in as_completed(futures):
                cell = futures[future]
                record = future.result()
                append_durable(
                    terminals_path,
                    {
                        "schema_version": "1.0.0",
                        "sequence": cell["sequence"],
                        "group_index": group_index,
                        "cell_id": cell["cell_id"],
                        "record": record,
                    },
                )
                completed.append(record)
                lane_records[str(cell["lane_id"])].append(record)
            if (group_index + 1) % 5 == 0 or group_index + 1 == schedule["planned_groups"]:
                print(
                    canonical_json(
                        {
                            "status": "RUNNING",
                            "completed_groups": group_index + 1,
                            "planned_groups": schedule["planned_groups"],
                            "completed_cells": len(completed),
                            "parseable_cells": sum(
                                row["parse_status"] == "OK" for row in completed
                            ),
                            "transport_error_cells": sum(
                                row["transport_status"] == "ERROR" for row in completed
                            ),
                        }
                    ),
                    flush=True,
                )
    if len(completed) != int(schedule["planned_cells"]):
        fail("execution ended without every frozen terminal cell")
    with atomic_output_directory(out_dir) as staging:
        output_hashes: Json = {}
        lane_summaries: list[Json] = []
        for lane in plan["formal_lanes"]:
            current_lane_id = str(lane["lane_id"])
            records = sorted(lane_records[current_lane_id], key=lambda row: str(row["item_id"]))
            if len(records) != 20:
                fail(f"lane does not contain 20 terminal records: {current_lane_id}")
            path = staging / f"{current_lane_id}.jsonl"
            write_jsonl(path, records)
            output_hashes[path.name] = sha256_file(path)
            lane_summaries.append(
                {
                    "lane_id": current_lane_id,
                    "configuration_id": lane["configuration_id"],
                    "replication": lane["replication"],
                    "records": len(records),
                    "parseable": sum(row["parse_status"] == "OK" for row in records),
                    "transport_errors": sum(row["transport_status"] == "ERROR" for row in records),
                }
            )
        receipt: Json = {
            "schema_version": "1.0.0",
            "status": "COMPLETE_ALL_FROZEN_CELLS_TERMINAL",
            "study_id": STUDY_ID,
            "frozen_plan_commit": frozen_commit,
            "schedule_sha256": schedule["schedule_sha256"],
            "started_at_utc": started_at,
            "completed_at_utc": utc_now(),
            "planned_cells": schedule["planned_cells"],
            "durable_request_intents": len(completed),
            "durable_terminal_records": len(completed),
            "application_posts": len(completed),
            "application_posts_per_cell": 1,
            "client_retry_count": 0,
            "partial_resume_used": False,
            "credentials_retained": False,
            "provider_response_identifiers_retained": False,
            "hidden_reasoning_retained": False,
            "request_intent_journal_sha256": sha256_file(intents_path),
            "terminal_journal_sha256": sha256_file(terminals_path),
            "lane_output_sha256": output_hashes,
            "lanes": lane_summaries,
        }
        write_durable_json(staging / "execution-receipt.json", receipt)
    print(
        canonical_json(
            {
                "status": receipt["status"],
                "records": len(completed),
                "parseable": sum(row["parse_status"] == "OK" for row in completed),
                "transport_errors": sum(row["transport_status"] == "ERROR" for row in completed),
                "host_usage_derived_quota_value_usd": sum(
                    float(row["actual_cost_usd"])
                    for row in completed
                    if isinstance(row.get("actual_cost_usd"), (int, float))
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
