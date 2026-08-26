#!/usr/bin/env python3
"""Analyze one frozen stronger-model run without publishing raw prompts or responses."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_with_schema,
)
from claimpromotebench.hashing import sha256_file  # noqa: E402
from claimpromotebench.metrics import evaluate_records  # noqa: E402
from claimpromotebench.v2 import summarize_pilot  # noqa: E402

Json = dict[str, Any]
DEFAULT_PLAN = ROOT / "v2" / "stronger-model-study-plan.json"
RUN_SCHEMA = ROOT / "v2" / "schemas" / "stronger-model-run-record.schema.json"


def fail(message: str) -> NoReturn:
    raise SystemExit(f"stronger-model-analysis: {message}")


def pilot_gate(records: list[Json], minimum_parseable: int = 10) -> Json:
    """Apply the preregistered model-output-independent continuation gate."""

    transport_errors = sum(row.get("transport_status") == "ERROR" for row in records)
    parseable = sum(row.get("parse_status") == "OK" for row in records)
    go = transport_errors == 0 and parseable >= minimum_parseable
    return {
        "decision": "GO" if go else "STOP",
        "transport_errors": transport_errors,
        "parseable_decisions": parseable,
        "required_parseable_decisions": minimum_parseable,
        "accuracy_used_by_gate": False,
        "action_distribution_used_by_gate": False,
    }


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> Json:
    """Return a two-sided 95% Wilson interval for a descriptive binomial proportion."""

    if trials == 0:
        return {
            "successes": successes,
            "trials": trials,
            "estimate": None,
            "low": None,
            "high": None,
        }
    estimate = successes / trials
    z_squared = z * z
    denominator = 1.0 + z_squared / trials
    center = (estimate + z_squared / (2.0 * trials)) / denominator
    half_width = (
        z
        * math.sqrt(estimate * (1.0 - estimate) / trials + z_squared / (4.0 * trials * trials))
        / denominator
    )
    return {
        "successes": successes,
        "trials": trials,
        "estimate": estimate,
        "low": max(0.0, center - half_width),
        "high": min(1.0, center + half_width),
    }


def find_lane(plan: Json, lane_id: str) -> tuple[Json, bool]:
    for key, formal in (("formal_lanes", True), ("exploratory_lanes", False)):
        for lane in plan.get(key, []):
            if lane.get("lane_id") == lane_id:
                return lane, formal
    fail(f"unknown lane_id: {lane_id}")


def selected_benchmark(
    dataset_dir: Path, packet: Json, phase: str
) -> tuple[list[Json], list[Json], set[str]]:
    gold = load_jsonl(dataset_dir / "gold.jsonl")
    pairs = load_json(dataset_dir / "pairs.json")
    if not isinstance(pairs, list):
        fail("pairs.json must contain a list")
    if phase == "pilot":
        selected_pair_ids = {str(value) for value in packet["pilot_pair_ids"]}
        selected_pairs = [row for row in pairs if str(row["pair_id"]) in selected_pair_ids]
    else:
        selected_pairs = pairs
    selected_ids = {str(item_id) for pair in selected_pairs for item_id in pair["member_ids"]}
    selected_gold = [row for row in gold if str(row["id"]) in selected_ids]
    if len(selected_gold) != len(selected_ids):
        fail("selected gold coverage is incomplete")
    return selected_gold, selected_pairs, selected_ids


def usage_summary(records: list[Json]) -> Json:
    fields = (
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "total_tokens",
    )
    totals: Json = {}
    missing: Json = {}
    for field in fields:
        values = [row["usage"].get(field) for row in records]
        known = [value for value in values if isinstance(value, int)]
        totals[field] = sum(known) if known else None
        missing[field] = len(values) - len(known)
    return {"totals": totals, "records_missing_field": missing}


def cost_summary(records: list[Json]) -> Json:
    values = [row.get("actual_cost_usd") for row in records]
    known = [float(value) for value in values if isinstance(value, (int, float))]
    if not known:
        status = "UNKNOWN"
        total = None
    elif len(known) != len(values):
        status = "PARTIAL"
        total = sum(known)
    else:
        status = "COMPLETE"
        total = sum(known)
    return {
        "status": status,
        "actual_cost_usd": total,
        "records_with_computed_cost": len(known),
        "records": len(values),
    }


def analyze(
    dataset_dir: Path,
    packet: Json,
    plan: Json,
    run_path: Path,
) -> Json:
    records = load_jsonl(run_path)
    if not records:
        fail(f"empty run: {run_path}")
    lane_ids = {str(row.get("lane_id")) for row in records}
    phases = {str(row.get("phase")) for row in records}
    frozen_commits = {str(row.get("frozen_plan_commit")) for row in records}
    if len(lane_ids) != 1 or len(phases) != 1 or len(frozen_commits) != 1:
        fail("run mixes lane IDs, phases, or frozen-plan commits")
    lane_id = next(iter(lane_ids))
    phase = next(iter(phases))
    if phase not in {"pilot", "full"}:
        fail(f"unknown phase: {phase}")
    lane, formal = find_lane(plan, lane_id)
    if phase == "full" and not formal:
        fail("exploratory lane cannot be analyzed as a full run")

    packet_rows = {str(row["item_id"]): row for row in packet["records"]}
    selected_gold, selected_pairs, expected_ids = selected_benchmark(dataset_dir, packet, phase)
    observed_ids: set[str] = set()
    for row in records:
        item_id = str(row.get("item_id"))
        if item_id in observed_ids:
            fail(f"duplicate item_id: {item_id}")
        observed_ids.add(item_id)
        validate_with_schema(row, RUN_SCHEMA, item_id)
        if row.get("study_id") != plan["study_id"]:
            fail(f"study_id mismatch: {item_id}")
        if row.get("packet_sha256") != packet["packet_sha256"]:
            fail(f"packet digest mismatch: {item_id}")
        if row.get("dataset_manifest_sha256") != packet["dataset_manifest_sha256"]:
            fail(f"dataset digest mismatch: {item_id}")
        if row.get("model_requested") != lane["model"]:
            fail(f"requested model mismatch: {item_id}")
        if item_id not in packet_rows:
            fail(f"run item is absent from packet: {item_id}")
        if row.get("prompt_sha256") != packet_rows[item_id]["prompt_sha256"]:
            fail(f"prompt digest mismatch: {item_id}")
    if observed_ids != expected_ids:
        missing = sorted(expected_ids - observed_ids)
        extra = sorted(observed_ids - expected_ids)
        fail(f"run coverage mismatch: missing={missing}, extra={extra}")

    metric_summary = summarize_pilot(selected_gold, selected_pairs, records)
    all_statuses = (
        "OK",
        "JSON_SYNTAX_ERROR",
        "SCHEMA_ERROR",
        "SEMANTIC_ERROR",
        "TRANSPORT_ERROR",
    )
    metric_summary["status_counts"] = {
        status: sum(row["parse_status"] == status for row in records) for status in all_statuses
    }
    raw_actions = Counter(
        str(row["raw_decision"]["action"]) for row in records if row["parse_status"] == "OK"
    )
    postgate_actions = Counter(
        str(row["postgate_decision"]["action"]) for row in records if row["parse_status"] == "OK"
    )
    gold_by_id = {str(row["id"]): row for row in selected_gold}
    ok_records = [row for row in records if row["parse_status"] == "OK"]
    covered_pair_rows = [row for row in metric_summary["pair_metrics"] if row["covered"]]
    invalid_records = [
        row
        for row in ok_records
        if gold_by_id[str(row["item_id"])]["decision"]["action"] != "ALLOW"
    ]
    valid_records = [
        row
        for row in ok_records
        if gold_by_id[str(row["item_id"])]["decision"]["action"] == "ALLOW"
    ]
    uncertainty = {
        "method": "two-sided 95% Wilson intervals; descriptive only",
        "decision_coverage": wilson_interval(len(ok_records), len(records)),
        "pair_coverage": wilson_interval(len(covered_pair_rows), len(selected_pairs)),
        "raw_action_accuracy": wilson_interval(
            sum(
                row["raw_decision"]["action"]
                == gold_by_id[str(row["item_id"])]["decision"]["action"]
                for row in ok_records
            ),
            len(ok_records),
        ),
        "postgate_action_accuracy": wilson_interval(
            sum(
                row["postgate_decision"]["action"]
                == gold_by_id[str(row["item_id"])]["decision"]["action"]
                for row in ok_records
            ),
            len(ok_records),
        ),
        "raw_pair_accuracy": wilson_interval(
            sum(bool(row["raw_pair_correct"]) for row in covered_pair_rows),
            len(covered_pair_rows),
        ),
        "postgate_pair_accuracy": wilson_interval(
            sum(bool(row["postgate_pair_correct"]) for row in covered_pair_rows),
            len(covered_pair_rows),
        ),
        "raw_false_promotion_rate": wilson_interval(
            sum(row["raw_decision"]["action"] == "ALLOW" for row in invalid_records),
            len(invalid_records),
        ),
        "raw_valid_promotion_rate": wilson_interval(
            sum(row["raw_decision"]["action"] == "ALLOW" for row in valid_records),
            len(valid_records),
        ),
    }
    end_to_end_correct = sum(
        row["parse_status"] == "OK"
        and row["raw_decision"]["action"] == gold_by_id[str(row["item_id"])]["decision"]["action"]
        for row in records
    )
    end_to_end_pair_correct = sum(
        bool(row.get("covered")) and bool(row.get("raw_pair_correct"))
        for row in metric_summary["pair_metrics"]
    )
    uncertainty["end_to_end_action_accuracy"] = wilson_interval(end_to_end_correct, len(records))
    uncertainty["end_to_end_pair_accuracy"] = wilson_interval(
        end_to_end_pair_correct, len(selected_pairs)
    )

    joined_records: list[Json] = []
    pair_by_member = {
        str(item_id): pair for pair in selected_pairs for item_id in pair["member_ids"]
    }
    for row in records:
        item_id = str(row["item_id"])
        joined_records.append(
            {
                "id": item_id,
                "pair_id": str(row["pair_id"]),
                "family": pair_by_member[item_id].get("family"),
                "gold": gold_by_id[item_id]["decision"],
                "prediction": row["raw_decision"],
                "parse_status": ("OK" if row["parse_status"] == "OK" else "FORMAT_ERROR"),
            }
        )
    complete_metrics = evaluate_records(joined_records, bootstrap_samples=0)
    complete_metrics["end_to_end"] = {
        "action_accuracy": end_to_end_correct / len(records),
        "correct_actions": end_to_end_correct,
        "actions": len(records),
        "pair_accuracy": end_to_end_pair_correct / len(selected_pairs),
        "correct_pairs": end_to_end_pair_correct,
        "pairs": len(selected_pairs),
        "failure_handling": "Every non-OK response counts as incorrect.",
    }

    if phase == "pilot" and formal:
        continuation_gate: Json = pilot_gate(records)
    elif phase == "pilot":
        continuation_gate = {
            "decision": "NOT_APPLICABLE_EXPLORATORY",
            **pilot_gate(records),
        }
        continuation_gate["decision"] = "NOT_APPLICABLE_EXPLORATORY"
    else:
        continuation_gate = {"decision": "NOT_APPLICABLE_FULL"}

    expected_ceiling = "COMPUTATIONAL" if formal else lane["evidence_ceiling"]
    ceilings = {str(row["evidence_ceiling"]) for row in records}
    if ceilings != {expected_ceiling}:
        fail(f"unexpected evidence ceiling: {sorted(ceilings)}")

    return {
        "schema_version": "1.0.0",
        "status": "COMPLETE",
        "truth_status": expected_ceiling,
        "study_id": plan["study_id"],
        "lane_id": lane_id,
        "provider": lane["provider"],
        "model_requested": lane["model"],
        "model_returned_values": sorted(
            {str(row["model_returned"]) for row in records if row["model_returned"] is not None}
        ),
        "routed_provider_values": sorted(
            {
                str(row["routed_provider"])
                for row in records
                if row.get("routed_provider") is not None
            }
        ),
        "phase": phase,
        "formal_lane": formal,
        "run_path": str(run_path),
        "run_sha256": sha256_file(run_path),
        "packet_sha256": packet["packet_sha256"],
        "frozen_plan_commit": next(iter(frozen_commits)),
        "records": len(records),
        "continuation_gate": continuation_gate,
        "usage": usage_summary(records),
        "cost": cost_summary(records),
        "raw_action_distribution": dict(sorted(raw_actions.items())),
        "postgate_action_distribution": dict(sorted(postgate_actions.items())),
        "metrics": metric_summary,
        "complete_metrics": complete_metrics,
        "uncertainty": uncertainty,
        "raw_prompts_or_responses_in_aggregate": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    output = args.out.resolve()
    if output.exists():
        fail(f"refusing to overwrite existing output: {output}")
    result = analyze(
        args.dataset.resolve(),
        load_json(args.packet.resolve()),
        load_json(args.plan.resolve()),
        args.run.resolve(),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "COMPLETE",
                "lane_id": result["lane_id"],
                "phase": result["phase"],
                "gate": result["continuation_gate"]["decision"],
                "out": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
