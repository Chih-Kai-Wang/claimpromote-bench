#!/usr/bin/env python3
"""Apply the frozen all-or-nothing resource rule to the hosted graph study."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from derive_policy_switch_hosted_replacement_eligibility import classify_records  # noqa: E402
from freeze_policy_transition_graph_hosted_study import (  # noqa: E402
    RESOURCE_EXHAUSTION_RULE,
    STUDY_ID,
)
from validate_policy_transition_graph_hosted_study import validate_freeze  # noqa: E402

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]


def fail(message: str) -> None:
    raise SystemExit(f"policy-transition-graph-hosted-eligibility: {message}")


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
    execution_path = results_root / "execution-receipt.json"
    execution = load_json(execution_path)
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
    if {str(row.get("cell_id")) for row in terminals} != {
        str(cell["cell_id"]) for cell in schedule["cells"]
    }:
        fail("terminal cells differ from the frozen schedule")
    classification = classify_records(terminals)
    eligible = bool(classification["eligible_for_model_efficacy_reporting"])
    receipt: Json = {
        "schema_version": "1.0.0",
        "status": (
            "HOSTED_TRANSITION_GRAPH_ELIGIBLE_COMPLETE_PROTOCOL"
            if eligible
            else "HOSTED_TRANSITION_GRAPH_EXCLUDED_IN_FULL_PERSISTENT_SHARED_RESOURCE_EXHAUSTION"
        ),
        "study_id": STUDY_ID,
        "rule_frozen_before_inference": RESOURCE_EXHAUSTION_RULE,
        "classification": classification,
        "decision": {
            "all_240_terminal_outcomes_considered": True,
            "hosted_model_rows_enter_manuscript": eligible,
            "conditional_success_subset_selected": False,
        },
        "free_form_error_text_included": False,
        "new_model_calls_performed_for_receipt": 0,
        "source_bindings": {
            "plan_sha256": sha256_file(plan_path),
            "schedule_sha256": sha256_file(schedule_path),
            "execution_receipt_sha256": sha256_file(execution_path),
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
