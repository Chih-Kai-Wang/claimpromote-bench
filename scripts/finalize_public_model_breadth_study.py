#!/usr/bin/env python3
"""Seal an interrupted public breadth run without resuming or making model calls."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_public_model_breadth_study import (  # noqa: E402
    atomic_output_directory,
    verify_frozen_plan,
    write_durable_json,
)
from validate_public_model_breadth_study import validate_study  # noqa: E402

from claimpromotebench.dataset import load_json, validate_with_schema, write_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
RUN_SCHEMA = ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json"


def fail(message: str) -> None:
    raise SystemExit(f"public-model-breadth-finalize: {message}")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def load_complete_lines(path: Path) -> list[Json]:
    if not path.exists():
        return []
    lines = path.read_bytes().splitlines()
    records: list[Json] = []
    for index, raw in enumerate(lines):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            if index != len(lines) - 1:
                fail(f"malformed nonterminal journal line: {path}:{index + 1}")
            break
        if not isinstance(value, dict):
            fail(f"journal line is not an object: {path}:{index + 1}")
        records.append(value)
    return records


def missing_record(
    plan: Json,
    packet: Json,
    lane: Json,
    cell: Json,
    *,
    request_started: str,
    sealed_at: str,
    error: str,
) -> Json:
    return {
        "schema_version": "1.0.0",
        "study_id": plan["study_id"],
        "frozen_plan_commit": plan["_frozen_plan_commit"],
        "packet_sha256": packet["packet_sha256"],
        "dataset_manifest_sha256": packet["dataset_manifest_sha256"],
        "phase": "full",
        "lane_id": lane["lane_id"],
        "provider": lane["provider"],
        "model_requested": lane["model"],
        "model_returned": None,
        "model_family": lane["model_family"],
        "item_id": cell["item_id"],
        "pair_id": cell["pair_id"],
        "request_sha256": cell["request_body_sha256"],
        "prompt_sha256": cell["prompt_sha256"],
        "response_format_sha256": sha256_bytes(canonical_json({}).encode("utf-8")),
        "provider_response_id": None,
        "routed_provider": None,
        "system_fingerprint": None,
        "finish_reason": None,
        "request_started_at_utc": request_started,
        "response_received_at_utc": sealed_at,
        "transport_status": "ERROR",
        "transport_error": error,
        "raw_response_text": None,
        "raw_response_sha256": None,
        "parse_status": "TRANSPORT_ERROR",
        "parse_error_detail": error,
        "raw_decision": None,
        "postgate_decision": None,
        "latency_ms": 0.0,
        "usage": {
            "input_tokens": None,
            "cached_input_tokens": None,
            "output_tokens": None,
            "reasoning_tokens": None,
            "total_tokens": None,
        },
        "actual_cost_usd": None,
        "cost_status": "UNKNOWN",
        "evidence_ceiling": "COMPUTATIONAL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--frozen-plan-commit", required=True)
    parser.add_argument("--journal-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    os.umask(0o077)
    plan_path = args.plan.resolve()
    schedule_path = args.schedule.resolve()
    packet_path = args.packet.resolve()
    frozen_commit = args.frozen_plan_commit.lower()
    verify_frozen_plan(plan_path, frozen_commit)
    validate_study(plan_path, schedule_path, packet_path)
    plan = load_json(plan_path)
    plan["_frozen_plan_commit"] = frozen_commit
    schedule = load_json(schedule_path)
    packet = load_json(packet_path)
    lanes = {str(row["lane_id"]): row for row in plan["formal_lanes"]}

    journal_dir = args.journal_dir.resolve()
    out_dir = args.out_dir.resolve()
    if not journal_dir.exists():
        fail("journal directory does not exist")
    if out_dir.exists():
        fail("output directory already exists")
    intents_path = journal_dir / "request-intents.jsonl"
    terminals_path = journal_dir / "terminal-records.jsonl"
    intents = load_complete_lines(intents_path)
    terminals = load_complete_lines(terminals_path)
    run_start_path = journal_dir / "run-start.json"
    if run_start_path.exists():
        run_start = load_json(run_start_path)
        if (
            run_start.get("status") != "EXECUTION_STARTED"
            or run_start.get("study_id") != plan["study_id"]
            or run_start.get("frozen_plan_commit") != frozen_commit
            or run_start.get("schedule_sha256") != schedule["schedule_sha256"]
            or run_start.get("planned_cells") != schedule["planned_cells"]
            or run_start.get("credentials_retained") is not False
        ):
            fail("run-start receipt does not match the frozen execution")
    elif intents or terminals:
        fail("journal has request records but no matching run-start receipt")

    cells_by_id = {str(cell["cell_id"]): cell for cell in schedule["cells"]}
    intent_by_cell: dict[str, Json] = {}
    terminal_by_cell: dict[str, Json] = {}
    for value in intents:
        cell_id = str(value.get("cell_id"))
        cell = cells_by_id.get(cell_id)
        if cell_id in intent_by_cell or cell is None:
            fail(f"duplicate or unplanned durable intent: {cell_id}")
        if (
            value.get("study_id") != plan["study_id"]
            or value.get("frozen_plan_commit") != frozen_commit
            or value.get("sequence") != cell["sequence"]
            or value.get("lane_id") != cell["lane_id"]
            or value.get("item_id") != cell["item_id"]
            or value.get("request_body_sha256") != cell["request_body_sha256"]
            or value.get("application_posts_authorized_for_cell") != 1
            or value.get("client_retries_authorized") != 0
            or not isinstance(value.get("intent_at_utc"), str)
        ):
            fail(f"durable intent differs from frozen cell: {cell_id}")
        intent_by_cell[cell_id] = value
    for value in terminals:
        cell_id = str(value.get("cell_id"))
        cell = cells_by_id.get(cell_id)
        record = value.get("record")
        if cell_id in terminal_by_cell or cell is None or not isinstance(record, dict):
            fail(f"duplicate or malformed durable terminal: {cell_id}")
        lane = lanes[str(cell["lane_id"])]
        if (
            value.get("sequence") != cell["sequence"]
            or record.get("study_id") != plan["study_id"]
            or record.get("frozen_plan_commit") != frozen_commit
            or record.get("packet_sha256") != packet["packet_sha256"]
            or record.get("dataset_manifest_sha256") != packet["dataset_manifest_sha256"]
            or record.get("phase") != "full"
            or record.get("lane_id") != cell["lane_id"]
            or record.get("provider") != lane["provider"]
            or record.get("model_requested") != lane["model"]
            or record.get("model_family") != lane["model_family"]
            or record.get("item_id") != cell["item_id"]
            or record.get("pair_id") != cell["pair_id"]
            or record.get("request_sha256") != cell["request_body_sha256"]
            or record.get("prompt_sha256") != cell["prompt_sha256"]
        ):
            fail(f"durable terminal differs from frozen cell: {cell_id}")
        validate_with_schema(record, RUN_SCHEMA, cell_id)
        terminal_by_cell[cell_id] = record
    planned_ids = {str(cell["cell_id"]) for cell in schedule["cells"]}
    if not set(intent_by_cell).issubset(planned_ids) or not set(terminal_by_cell).issubset(
        planned_ids
    ):
        fail("journal contains an unplanned cell")
    if not set(terminal_by_cell).issubset(set(intent_by_cell)):
        fail("terminal record lacks a preceding durable intent")

    sealed_at = utc_now()
    lane_records: dict[str, list[Json]] = defaultdict(list)
    categories: Counter[str] = Counter()
    for cell in schedule["cells"]:
        cell_id = str(cell["cell_id"])
        lane = lanes[str(cell["lane_id"])]
        if cell_id in terminal_by_cell:
            record = terminal_by_cell[cell_id]
            categories["DURABLE_TERMINAL"] += 1
        elif cell_id in intent_by_cell:
            record = missing_record(
                plan,
                packet,
                lane,
                cell,
                request_started=str(intent_by_cell[cell_id]["intent_at_utc"]),
                sealed_at=sealed_at,
                error="AMBIGUOUS_ZERO_OR_ONE_POST_AFTER_DURABLE_INTENT_NO_TERMINAL_NO_RETRY",
            )
            categories["AMBIGUOUS_ZERO_OR_ONE_POST"] += 1
        else:
            record = missing_record(
                plan,
                packet,
                lane,
                cell,
                request_started=sealed_at,
                sealed_at=sealed_at,
                error="NOT_ATTEMPTED_AFTER_EXECUTION_INTERRUPTION_NO_RESUME",
            )
            categories["NOT_ATTEMPTED"] += 1
        validate_with_schema(record, RUN_SCHEMA, cell_id)
        lane_records[str(cell["lane_id"])].append(record)

    with atomic_output_directory(out_dir) as staging_dir:
        output_hashes: Json = {}
        for lane_id in plan["execution"]["base_lane_order"]:
            records = lane_records[str(lane_id)]
            if len(records) != 180:
                fail(f"sealed lane does not have 180 records: {lane_id}")
            path = staging_dir / f"{lane_id}.jsonl"
            write_jsonl(path, records)
            output_hashes[path.name] = sha256_file(path)
        receipt = {
            "schema_version": "1.0.0",
            "status": "SEALED_WITHOUT_RESUME",
            "study_id": plan["study_id"],
            "frozen_plan_commit": frozen_commit,
            "schedule_sha256": schedule["schedule_sha256"],
            "sealed_at_utc": sealed_at,
            "planned_cells": schedule["planned_cells"],
            "terminal_categories": dict(sorted(categories.items())),
            "durable_intents": len(intent_by_cell),
            "durable_terminals": len(terminal_by_cell),
            "client_retries": 0,
            "partial_resume_used": False,
            "model_calls_made_by_finalizer": 0,
            "credentials_loaded_by_finalizer": False,
            "request_intent_journal_sha256": (
                sha256_file(intents_path) if intents_path.exists() else None
            ),
            "terminal_journal_sha256": (
                sha256_file(terminals_path) if terminals_path.exists() else None
            ),
            "lane_output_sha256": output_hashes,
        }
        write_durable_json(staging_dir / "execution-receipt.json", receipt)
    print(canonical_json({"status": receipt["status"], "terminal_categories": categories}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
