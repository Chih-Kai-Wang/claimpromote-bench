#!/usr/bin/env python3
"""Seal the first local-model attempt as ineligible without selecting an outcome."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> NoReturn:
    raise SystemExit(f"local-model-void-seal: {message}")


def self_digest(value: Json) -> str:
    payload = {key: child for key, child in value.items() if key != "self_digest"}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def derive(
    plan_path: Path,
    schedule_path: Path,
    journal_dir: Path,
    results_dir: Path,
    legacy_schema_path: Path,
) -> Json:
    plan = load_json(plan_path)
    schedule = load_json(schedule_path)
    run_start_path = journal_dir / "run-start.json"
    intents_path = journal_dir / "request-intents.jsonl"
    terminals_path = journal_dir / "terminal-records.jsonl"
    run_start = load_json(run_start_path)
    intents = load_jsonl(intents_path)
    schema = load_json(legacy_schema_path)
    if not all(isinstance(value, dict) for value in (plan, schedule, run_start, schema)):
        fail("attempt evidence is malformed")
    cells = schedule.get("cells")
    lanes = plan.get("formal_lanes")
    family_enum = schema.get("properties", {}).get("model_family", {}).get("enum")
    if (
        plan.get("status") != "PROSPECTIVELY_FROZEN_LOCAL_MODEL_REPLICATION"
        or plan.get("study_id") != "claimpromotebench-slsa-local-model-replication-2026-08-v1"
        or not isinstance(cells, list)
        or len(cells) != 240
        or not isinstance(lanes, list)
        or len(lanes) != 2
        or not isinstance(family_enum, list)
        or "Mistral" in family_enum
    ):
        fail("historical plan or schema boundary changed")
    if (
        run_start.get("status") != "EXECUTION_STARTED"
        or run_start.get("study_id") != plan.get("study_id")
        or run_start.get("schedule_sha256") != schedule.get("schedule_sha256")
        or len(intents) != 1
        or intents[0].get("sequence") != 0
        or intents[0].get("cell_id") != cells[0].get("cell_id")
        or intents[0].get("application_posts_authorized_for_cell") != 1
        or intents[0].get("client_retries_authorized") != 0
        or terminals_path.exists()
        or results_dir.exists()
    ):
        fail("void attempt is not exactly one intent and zero terminal records")
    first_lane = next(
        (row for row in lanes if row.get("lane_id") == intents[0].get("lane_id")), None
    )
    if not isinstance(first_lane, dict) or first_lane.get("model_family") != "Mistral":
        fail("first attempted lane is not the schema-incompatible family")

    receipt: Json = {
        "schema_version": "1.0.0",
        "status": "INELIGIBLE_LOCAL_ATTEMPT_PRE_TERMINAL_SCHEMA_REJECTION",
        "study_id": plan["study_id"],
        "frozen_plan_commit": run_start["frozen_plan_commit"],
        "source_bindings": {
            "plan_sha256": sha256_file(plan_path),
            "schedule_sha256": sha256_file(schedule_path),
            "run_start_sha256": sha256_file(run_start_path),
            "request_intents_sha256": sha256_file(intents_path),
            "legacy_run_schema_sha256": sha256_file(legacy_schema_path),
        },
        "observed_counts": {
            "scheduled_cells": 240,
            "application_invocations": 1,
            "durable_request_intents": 1,
            "durable_terminal_records": 0,
            "retained_model_outputs": 0,
        },
        "failure_boundary": {
            "class": "LOCAL_RECORD_SCHEMA_REJECTION",
            "schema_location": "model_family",
            "rejected_value": "Mistral",
            "model_outcome_unknown_and_unretained": True,
            "raw_generation_text_retained": False,
            "benchmark_label_or_accuracy_consulted": False,
        },
        "decision": {
            "attempt_enters_manuscript": False,
            "attempt_enters_anonymous_item_evidence": False,
            "resume_or_overwrite_used": False,
            "model_performance_interpreted": False,
            "replacement_requires_new_study_ids_and_schedule": True,
        },
        "interpretation": (
            "The first application invocation reached a legacy run-record schema whose model-"
            "family enum omitted the pinned local families. No terminal record or model output "
            "was retained, and no outcome or benchmark label was consulted. The attempt is "
            "ineligible in full and cannot be resumed or selected into the manuscript."
        ),
    }
    receipt["self_digest"] = self_digest(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--journal-dir", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--legacy-schema", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    receipt = derive(
        args.plan.resolve(),
        args.schedule.resolve(),
        args.journal_dir.resolve(),
        args.results_dir.resolve(),
        args.legacy_schema.resolve(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(canonical_json({"status": receipt["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
