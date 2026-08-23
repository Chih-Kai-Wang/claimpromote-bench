#!/usr/bin/env python3
"""Apply the frozen all-or-nothing resource rule to the hosted replacement."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from freeze_policy_switch_hosted_replacement import (  # noqa: E402
    RESOURCE_EXHAUSTION_RULE,
    STUDY_ID,
)
from validate_policy_switch_hosted_replacement import validate_freeze  # noqa: E402

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
MINIMUM_PERSISTENT_TAIL = 20
EXPLICIT_EXHAUSTION_PATTERNS = (
    re.compile(
        r"\b(?:quota|allowance|credits?|usage\s+limit|subscription\s+limit|weekly\s+limit)\b"
        r".{0,120}\b(?:exhausted|exceeded|depleted|insufficient|reached|used\s+up)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:exhausted|exceeded|depleted|insufficient|reached|used\s+up)\b"
        r".{0,120}\b(?:quota|allowance|credits?|usage\s+limit|subscription\s+limit|weekly\s+limit)\b",
        re.IGNORECASE,
    ),
)


def fail(message: str) -> None:
    raise SystemExit(f"policy-switch-hosted-replacement-eligibility: {message}")


def explicit_resource_exhaustion(detail: Any) -> bool:
    text = str(detail or "")
    return any(pattern.search(text) is not None for pattern in EXPLICIT_EXHAUSTION_PATTERNS)


def classify_records(terminals: list[Json]) -> Json:
    if len(terminals) != 240:
        fail("eligibility requires all 240 terminal records")
    ordered = sorted(terminals, key=lambda row: int(row["sequence"]))
    if [int(row["sequence"]) for row in ordered] != list(range(240)):
        fail("terminal sequences must cover 0 through 239 exactly once")
    records = [row.get("record") for row in ordered]
    if any(not isinstance(row, dict) for row in records):
        fail("terminal journal contains a malformed record")
    explicit_sequences = [
        index
        for index, row in enumerate(records)
        if row.get("transport_status") == "ERROR"
        and explicit_resource_exhaustion(row.get("transport_error"))
    ]
    trigger_sequence: int | None = None
    for sequence in explicit_sequences:
        tail = records[sequence + 1 :]
        if len(tail) >= MINIMUM_PERSISTENT_TAIL and all(
            row.get("transport_status") == "ERROR" for row in tail
        ):
            trigger_sequence = sequence
            break
    excluded = trigger_sequence is not None
    return {
        "eligible_for_model_efficacy_reporting": not excluded,
        "explicit_resource_exhaustion_errors": len(explicit_sequences),
        "persistent_exhaustion_trigger_sequence": trigger_sequence,
        "minimum_persistent_tail_cells": MINIMUM_PERSISTENT_TAIL,
        "transport_status_counts": dict(
            sorted(Counter(str(row.get("transport_status")) for row in records).items())
        ),
        "parse_status_counts": dict(
            sorted(Counter(str(row.get("parse_status")) for row in records).items())
        ),
    }


def derive(
    *,
    plan_path: Path,
    schedule_path: Path,
    dataset_root: Path,
    baseline_root: Path,
    journal_root: Path,
    results_root: Path,
    out_path: Path,
) -> Json:
    if out_path.exists():
        fail("refusing to overwrite an eligibility receipt")
    validate_freeze(plan_path, schedule_path, dataset_root, baseline_root)
    plan = load_json(plan_path)
    schedule = load_json(schedule_path)
    execution = load_json(results_root / "execution-receipt.json")
    terminals_path = journal_root / "terminal-records.jsonl"
    terminals = load_jsonl(terminals_path)
    if (
        plan.get("study_id") != STUDY_ID
        or schedule.get("study_id") != STUDY_ID
        or execution.get("study_id") != STUDY_ID
        or execution.get("status") != "COMPLETE_ALL_FROZEN_CELLS_TERMINAL"
        or execution.get("durable_terminal_records") != 240
        or execution.get("terminal_journal_sha256") != sha256_file(terminals_path)
        or plan.get("execution", {}).get("resource_exhaustion_eligibility_rule")
        != RESOURCE_EXHAUSTION_RULE
    ):
        fail("freeze, execution, or resource rule changed")
    scheduled_cells = {str(cell["cell_id"]) for cell in schedule["cells"]}
    if {str(row.get("cell_id")) for row in terminals} != scheduled_cells:
        fail("terminal cells differ from the frozen schedule")
    classification = classify_records(terminals)
    eligible = bool(classification["eligible_for_model_efficacy_reporting"])
    receipt: Json = {
        "schema_version": "1.0.0",
        "status": (
            "HOSTED_REPLACEMENT_ELIGIBLE_COMPLETE_PROTOCOL"
            if eligible
            else "HOSTED_REPLACEMENT_EXCLUDED_IN_FULL_PERSISTENT_SHARED_RESOURCE_EXHAUSTION"
        ),
        "study_id": STUDY_ID,
        "rule_frozen_before_inference": RESOURCE_EXHAUSTION_RULE,
        "classification": classification,
        "decision": {
            "all_240_terminal_outcomes_considered": True,
            "hosted_model_rows_enter_manuscript": eligible,
            "conditional_success_subset_selected": False,
            "predecessor_outputs_enter_manuscript": False,
        },
        "free_form_error_text_included": False,
        "new_model_calls_performed_for_receipt": 0,
        "source_bindings": {
            "plan_sha256": sha256_file(plan_path),
            "schedule_sha256": sha256_file(schedule_path),
            "execution_receipt_sha256": sha256_file(results_root / "execution-receipt.json"),
            "terminal_journal_sha256": sha256_file(terminals_path),
        },
    }
    receipt["self_digest"] = sha256_bytes(canonical_json(receipt).encode("utf-8"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--journal-root", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = derive(
        plan_path=args.plan.resolve(),
        schedule_path=args.schedule.resolve(),
        dataset_root=args.dataset_root.resolve(),
        baseline_root=args.baseline_root.resolve(),
        journal_root=args.journal_root.resolve(),
        results_root=args.results_root.resolve(),
        out_path=args.out.resolve(),
    )
    print(
        canonical_json(
            {
                "status": result["status"],
                "eligible": result["decision"]["hosted_model_rows_enter_manuscript"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
