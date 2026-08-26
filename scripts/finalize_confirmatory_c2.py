#!/usr/bin/env python3
"""Seal one outcome for every C1 cell before loading confirmatory gold."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json, load_jsonl, write_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def _existing(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.is_file()]


def finalize(
    schedule_path: Path,
    journal_paths: list[Path],
    run_paths: list[Path],
    out_dir: Path,
) -> tuple[Json, dict[str, list[Json]]]:
    schedule = load_json(schedule_path)
    payload = deepcopy(schedule)
    observed_schedule_sha = payload.pop("schedule_sha256", None)
    if observed_schedule_sha != sha256_bytes(canonical_json(payload).encode("utf-8")):
        raise ValueError("C1 schedule digest mismatch")
    cells = schedule.get("cells")
    if not isinstance(cells, list) or len(cells) != int(schedule.get("planned_cells", -1)):
        raise ValueError("C1 schedule cell count is malformed")
    scheduled = {(str(row["lane_id"]), str(row["item_id"])): row for row in cells}
    if len(scheduled) != len(cells):
        raise ValueError("C1 schedule contains duplicate cells")

    intents: dict[tuple[str, str], Json] = {}
    for path in _existing(journal_paths):
        for row in load_jsonl(path):
            key = (str(row.get("lane_id")), str(row.get("item_id")))
            if row.get("event") != "POST_INTENT" or key not in scheduled or key in intents:
                raise ValueError(f"request journal is malformed or duplicated: {path}: {key}")
            if row.get("request_body_sha256") != scheduled[key]["request_body_sha256"]:
                raise ValueError(f"request intent differs from C1: {key}")
            intents[key] = row

    results: dict[tuple[str, str], Json] = {}
    for path in _existing(run_paths):
        for row in load_jsonl(path):
            key = (str(row.get("lane_id")), str(row.get("item_id")))
            if key not in scheduled or key in results:
                raise ValueError(f"run record is malformed or duplicated: {path}: {key}")
            if key not in intents:
                raise ValueError(f"response record lacks a prior durable POST intent: {key}")
            if row.get("request_body_sha256") != scheduled[key]["request_body_sha256"]:
                raise ValueError(f"response record differs from C1: {key}")
            if row.get("application_post_count") != 1 or row.get("client_retry_count") != 0:
                raise ValueError(f"response record violates the one-POST rule: {key}")
            results[key] = row

    by_lane: dict[str, list[Json]] = {str(lane): [] for lane in schedule["lane_order"]}
    outcome_counts: Counter[str] = Counter()
    for key, cell in scheduled.items():
        lane_id, item_id = key
        if key in results:
            record = dict(results[key])
            outcome = "RESPONSE_RECORDED"
            record["sequence"] = cell["sequence"]
            record["pair_id"] = cell["pair_id"]
            record["prompt_sha256"] = cell["prompt_sha256"]
        elif key in intents:
            outcome = "AMBIGUOUS_REQUEST_LOSS"
            record = {
                "schema_version": "1.0.0",
                "study_id": schedule["study_id"],
                "schedule_sha256": schedule["schedule_sha256"],
                "packet_sha256": schedule["packet_sha256"],
                "lane_id": lane_id,
                "sequence": cell["sequence"],
                "item_id": item_id,
                "pair_id": cell["pair_id"],
                "prompt_sha256": cell["prompt_sha256"],
                "request_body_sha256": cell["request_body_sha256"],
                "application_post_count": None,
                "application_post_count_range": [0, 1],
                "request_accounting_status": "UNKNOWN_0_OR_1_POST",
                "client_retry_count": 0,
                "parse_status": outcome,
                "parse_detail": (
                    "A local POST intent was durable but no response record was sealed; the "
                    "process may have stopped immediately before or after the application POST."
                ),
                "raw_decision": None,
                "contains_gold": False,
                "deterministic_gate_applied": False,
            }
        else:
            outcome = "AMBIGUOUS_ORCHESTRATION_LOSS"
            record = {
                "schema_version": "1.0.0",
                "study_id": schedule["study_id"],
                "schedule_sha256": schedule["schedule_sha256"],
                "packet_sha256": schedule["packet_sha256"],
                "lane_id": lane_id,
                "sequence": cell["sequence"],
                "item_id": item_id,
                "pair_id": cell["pair_id"],
                "prompt_sha256": cell["prompt_sha256"],
                "request_body_sha256": cell["request_body_sha256"],
                "application_post_count": None,
                "application_post_count_range": [0, 1],
                "request_accounting_status": "UNKNOWN_0_OR_1_POST",
                "client_retry_count": 0,
                "parse_status": outcome,
                "parse_detail": (
                    "No journal record was recovered. Ephemeral-runner loss means zero versus one "
                    "application POST cannot be distinguished; the cell is incorrect and cannot "
                    "be sent later."
                ),
                "raw_decision": None,
                "contains_gold": False,
                "deterministic_gate_applied": False,
            }
        record["c2_cell_outcome"] = outcome
        outcome_counts[outcome] += 1
        by_lane[lane_id].append(record)
    for lane_id, rows in by_lane.items():
        rows.sort(key=lambda row: int(row["sequence"]))
        if len(rows) != len([cell for cell in cells if cell["lane_id"] == lane_id]):
            raise ValueError(f"C2 lane coverage mismatch: {lane_id}")
        out_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(out_dir / f"{lane_id}-c2-complete.jsonl", rows)
    receipt: Json = {
        "schema_version": "1.0.0",
        "commitment_stage": "C2_BEFORE_GOLD_UNBLINDING_OR_ANALYSIS",
        "study_id": schedule["study_id"],
        "schedule_sha256": schedule["schedule_sha256"],
        "planned_cells": len(cells),
        "sealed_cells": sum(outcome_counts.values()),
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "journal_files": {
            path.name: sha256_file(path) for path in sorted(_existing(journal_paths))
        },
        "raw_run_files": {path.name: sha256_file(path) for path in sorted(_existing(run_paths))},
        "complete_lane_files": {
            path.name: sha256_file(path) for path in sorted(out_dir.glob("*-c2-complete.jsonl"))
        },
        "contains_gold_labels": False,
        "gold_loaded_before_receipt": False,
        "analysis_executed_before_receipt": False,
        "missing_cells_are_incorrect_and_cannot_be_retried": True,
        "lost_cell_request_accounting": (
            "UNKNOWN_0_OR_1_POST_PER_CELL_WHEN_NO_RESPONSE_RECORD_IS_RECOVERED"
        ),
        "ephemeral_runner_loss_cannot_prove_zero_posts": True,
    }
    receipt["c2_receipt_sha256"] = sha256_bytes(canonical_json(receipt).encode("utf-8"))
    return receipt, by_lane


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--journal", type=Path, action="append", default=[])
    parser.add_argument("--run", type=Path, action="append", default=[])
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    receipt, _by_lane = finalize(
        args.schedule.resolve(),
        [path.resolve() for path in args.journal],
        [path.resolve() for path in args.run],
        args.out_dir.resolve(),
    )
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": receipt["commitment_stage"],
                "planned_cells": receipt["planned_cells"],
                "sealed_cells": receipt["sealed_cells"],
                "outcomes": receipt["outcome_counts"],
                "c2_receipt_sha256": receipt["c2_receipt_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
