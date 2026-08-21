#!/usr/bin/env python3
"""Analyze the frozen balanced public challenge with failure-aware metrics."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_stronger_model_study import analyze as analyze_lane  # noqa: E402

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import sha256_file  # noqa: E402

Json = dict[str, Any]
ACTIONS = ("ALLOW", "HOLD", "DEMOTE", "ESCALATE")
PREDICTION_COLUMNS = (*ACTIONS, "NO_VALID_DECISION")


def fail(message: str) -> NoReturn:
    raise SystemExit(f"balanced-public-challenge-analysis: {message}")


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


def _mean_defined(values: list[float | None]) -> float | None:
    defined = [value for value in values if value is not None]
    return sum(defined) / len(defined) if defined else None


def _class_metrics(confusion: Json) -> Json:
    per_action: Json = {}
    for action in ACTIONS:
        gold_total = sum(int(confusion[action][column]) for column in PREDICTION_COLUMNS)
        parseable_gold = gold_total - int(confusion[action]["NO_VALID_DECISION"])
        predicted_total = sum(int(confusion[gold][action]) for gold in ACTIONS)
        correct = int(confusion[action][action])
        precision = _rate(correct, predicted_total)
        end_to_end_recall = _rate(correct, gold_total)
        conditional_recall = _rate(correct, parseable_gold)
        per_action[action] = {
            "gold_instances": gold_total,
            "parseable_gold_instances": parseable_gold,
            "predicted_instances": predicted_total,
            "correct": correct,
            "precision": precision,
            "end_to_end_recall": end_to_end_recall,
            "conditional_recall": conditional_recall,
            "end_to_end_f1": _f1(precision, end_to_end_recall),
            "conditional_f1": _f1(precision, conditional_recall),
        }
    return {
        "per_action": per_action,
        "balanced_action_recall": _mean_defined(
            [per_action[action]["end_to_end_recall"] for action in ACTIONS]
        ),
        "conditional_balanced_action_recall": _mean_defined(
            [per_action[action]["conditional_recall"] for action in ACTIONS]
        ),
        "macro_f1": _mean_defined(
            [per_action[action]["end_to_end_f1"] for action in ACTIONS]
        ),
        "conditional_macro_f1": _mean_defined(
            [per_action[action]["conditional_f1"] for action in ACTIONS]
        ),
    }


def derive_reporting_metrics(gold: list[Json], pairs: list[Json], records: list[Json]) -> Json:
    """Derive registered item, pair, class, and factor metrics for one lane."""

    gold_by_id = {str(row["id"]): row for row in gold}
    record_by_id = {str(row["item_id"]): row for row in records}
    if len(record_by_id) != len(records):
        fail("a lane contains duplicate item IDs")
    if set(record_by_id) != set(gold_by_id):
        fail("a lane does not cover exactly the frozen gold IDs")

    confusion: Json = {
        gold_action: {column: 0 for column in PREDICTION_COLUMNS} for gold_action in ACTIONS
    }
    parse_status_counts = Counter(str(row["parse_status"]) for row in records)
    correct_items = 0
    parseable_items = 0
    for item_id, gold_row in gold_by_id.items():
        row = record_by_id[item_id]
        gold_action = str(gold_row["decision"]["action"])
        if gold_action not in ACTIONS:
            fail(f"unknown gold action for {item_id}: {gold_action}")
        if row["parse_status"] == "OK":
            parseable_items += 1
            prediction = str(row["raw_decision"]["action"])
            if prediction not in ACTIONS:
                fail(f"unknown predicted action for {item_id}: {prediction}")
            confusion[gold_action][prediction] += 1
            correct_items += prediction == gold_action
        else:
            confusion[gold_action]["NO_VALID_DECISION"] += 1

    factor_counts: dict[str, Json] = {}
    covered_pairs = 0
    correct_pairs = 0
    for pair in pairs:
        factor_id = str(pair["factor_id"])
        factor = factor_counts.setdefault(
            factor_id,
            {
                "factor_id": factor_id,
                "family": pair.get("family"),
                "pairs": 0,
                "covered_pairs": 0,
                "correct_pairs": 0,
            },
        )
        factor["pairs"] += 1
        member_ids = [str(value) for value in pair["member_ids"]]
        member_records = [record_by_id[item_id] for item_id in member_ids]
        covered = all(row["parse_status"] == "OK" for row in member_records)
        if not covered:
            continue
        covered_pairs += 1
        factor["covered_pairs"] += 1
        pair_correct = all(
            row["raw_decision"]["action"] == gold_by_id[item_id]["decision"]["action"]
            for item_id, row in zip(member_ids, member_records, strict=True)
        )
        correct_pairs += pair_correct
        factor["correct_pairs"] += pair_correct

    factor_metrics: list[Json] = []
    for factor_id in sorted(factor_counts):
        factor = factor_counts[factor_id]
        factor_metrics.append(
            {
                **factor,
                "pair_coverage": _rate(factor["covered_pairs"], factor["pairs"]),
                "end_to_end_pair_accuracy": _rate(factor["correct_pairs"], factor["pairs"]),
                "conditional_pair_accuracy": _rate(
                    factor["correct_pairs"], factor["covered_pairs"]
                ),
            }
        )

    class_metrics = _class_metrics(confusion)
    return {
        "items": len(records),
        "parseable_items": parseable_items,
        "correct_items": correct_items,
        "decision_coverage": _rate(parseable_items, len(records)),
        "end_to_end_item_accuracy": _rate(correct_items, len(records)),
        "conditional_item_accuracy": _rate(correct_items, parseable_items),
        "pairs": len(pairs),
        "covered_pairs": covered_pairs,
        "correct_pairs": correct_pairs,
        "pair_coverage": _rate(covered_pairs, len(pairs)),
        "end_to_end_pair_accuracy": _rate(correct_pairs, len(pairs)),
        "conditional_pair_accuracy": _rate(correct_pairs, covered_pairs),
        "parse_status_counts": dict(sorted(parse_status_counts.items())),
        "confusion_matrix": {
            "row_semantics": "gold action",
            "column_semantics": "raw model action or absence of a valid decision",
            "row_order": list(ACTIONS),
            "column_order": list(PREDICTION_COLUMNS),
            "counts": confusion,
        },
        **class_metrics,
        "factor_metrics": factor_metrics,
        "failure_rule": "Every non-OK response remains in the denominator as incorrect.",
    }


def combine_lane_metrics(lanes: list[Json]) -> Json:
    """Pool equally executed model-item cells without implying a causal comparison."""

    if not lanes:
        fail("at least one lane is required")
    confusion: Json = {
        gold: {
            column: sum(int(lane["confusion_matrix"]["counts"][gold][column]) for lane in lanes)
            for column in PREDICTION_COLUMNS
        }
        for gold in ACTIONS
    }
    status_counts: Counter[str] = Counter()
    factor_counts: dict[str, Json] = {}
    for lane in lanes:
        status_counts.update(lane["parse_status_counts"])
        for factor in lane["factor_metrics"]:
            combined = factor_counts.setdefault(
                str(factor["factor_id"]),
                {
                    "factor_id": factor["factor_id"],
                    "family": factor["family"],
                    "pairs": 0,
                    "covered_pairs": 0,
                    "correct_pairs": 0,
                },
            )
            for field in ("pairs", "covered_pairs", "correct_pairs"):
                combined[field] += int(factor[field])

    items = sum(int(lane["items"]) for lane in lanes)
    parseable_items = sum(int(lane["parseable_items"]) for lane in lanes)
    correct_items = sum(int(lane["correct_items"]) for lane in lanes)
    pairs = sum(int(lane["pairs"]) for lane in lanes)
    covered_pairs = sum(int(lane["covered_pairs"]) for lane in lanes)
    correct_pairs = sum(int(lane["correct_pairs"]) for lane in lanes)
    factors = []
    for factor_id in sorted(factor_counts):
        factor = factor_counts[factor_id]
        factors.append(
            {
                **factor,
                "pair_coverage": _rate(factor["covered_pairs"], factor["pairs"]),
                "end_to_end_pair_accuracy": _rate(factor["correct_pairs"], factor["pairs"]),
                "conditional_pair_accuracy": _rate(
                    factor["correct_pairs"], factor["covered_pairs"]
                ),
            }
        )
    return {
        "items": items,
        "parseable_items": parseable_items,
        "correct_items": correct_items,
        "decision_coverage": _rate(parseable_items, items),
        "end_to_end_item_accuracy": _rate(correct_items, items),
        "conditional_item_accuracy": _rate(correct_items, parseable_items),
        "pairs": pairs,
        "covered_pairs": covered_pairs,
        "correct_pairs": correct_pairs,
        "pair_coverage": _rate(covered_pairs, pairs),
        "end_to_end_pair_accuracy": _rate(correct_pairs, pairs),
        "conditional_pair_accuracy": _rate(correct_pairs, covered_pairs),
        "parse_status_counts": dict(sorted(status_counts.items())),
        "confusion_matrix": {
            "row_semantics": "gold action",
            "column_semantics": "raw model action or absence of a valid decision",
            "row_order": list(ACTIONS),
            "column_order": list(PREDICTION_COLUMNS),
            "counts": confusion,
        },
        **_class_metrics(confusion),
        "factor_metrics": factors,
        "failure_rule": "Every non-OK response remains in the denominator as incorrect.",
    }


def analyze_challenge(
    dataset_dir: Path,
    packet: Json,
    plan: Json,
    plan_path: Path,
    run_paths: list[Path],
    *,
    workflow_run_url: str | None = None,
    workflow_run_attempt: int | None = None,
) -> Json:
    if plan.get("status") != "FROZEN_BEFORE_SCORED_INFERENCE":
        fail("plan is not frozen before scored inference")
    if plan.get("truth_status") != "OPEN":
        fail("plan must remain OPEN before result interpretation")
    planned_lane_ids = {str(lane["lane_id"]) for lane in plan["formal_lanes"]}
    gold = load_jsonl(dataset_dir / "gold.jsonl")
    pairs = load_json(dataset_dir / "pairs.json")
    if not isinstance(pairs, list):
        fail("pairs.json must contain a list")

    lane_outputs: list[Json] = []
    frozen_commits: set[str] = set()
    seen_lane_ids: set[str] = set()
    quota_values: list[float] = []
    for run_path in run_paths:
        base = analyze_lane(dataset_dir, packet, plan, run_path)
        if base["phase"] != "full" or not base["formal_lane"]:
            fail(f"challenge run is not a formal full run: {run_path}")
        lane_id = str(base["lane_id"])
        if lane_id in seen_lane_ids:
            fail(f"duplicate lane run: {lane_id}")
        seen_lane_ids.add(lane_id)
        frozen_commits.add(str(base["frozen_plan_commit"]))
        records = load_jsonl(run_path)
        metrics = derive_reporting_metrics(gold, pairs, records)
        cost = base["cost"]
        if isinstance(cost.get("actual_cost_usd"), (int, float)):
            quota_values.append(float(cost["actual_cost_usd"]))
        lane_outputs.append(
            {
                "lane_id": lane_id,
                "provider": base["provider"],
                "model_requested": base["model_requested"],
                "model_returned_values": base["model_returned_values"],
                "routed_provider_values": base["routed_provider_values"],
                "run_sha256": base["run_sha256"],
                "usage": base["usage"],
                "host_usage_derived_quota_value": cost,
                "metrics": metrics,
            }
        )
    if seen_lane_ids != planned_lane_ids:
        fail(
            "run lanes differ from the frozen formal lanes: "
            f"expected={sorted(planned_lane_ids)} observed={sorted(seen_lane_ids)}"
        )
    if len(frozen_commits) != 1:
        fail("challenge runs do not share one frozen-plan commit")

    pooled = combine_lane_metrics([lane["metrics"] for lane in lane_outputs])
    return {
        "schema_version": "1.0.0",
        "status": "COMPLETE",
        "truth_status": "COMPUTATIONAL",
        "study_id": plan["study_id"],
        "design": "PUBLIC_PRECOMMITTED_BALANCED_CHALLENGE",
        "interpretation": (
            "Prespecified public robustness evidence; not a hidden-test generalization estimate."
        ),
        "external_commitment": {
            "frozen_plan_commit": next(iter(frozen_commits)),
            "plan_sha256": sha256_file(plan_path),
            "packet_sha256": packet["packet_sha256"],
            "dataset_manifest_sha256": packet["dataset_manifest_sha256"],
            "workflow_run_url": workflow_run_url,
            "workflow_run_attempt": workflow_run_attempt,
        },
        "budget": {
            "incremental_cash_spend_usd": plan["budget"]["incremental_cash_cap_usd"],
            "billing_mode": "PREEXISTING_SUBSCRIPTION_INCLUDED_QUOTA",
            "host_usage_derived_quota_value_usd": (
                sum(quota_values) if len(quota_values) == len(lane_outputs) else None
            ),
            "quota_value_is_not_incremental_cash_spend": True,
        },
        "lanes": sorted(lane_outputs, key=lambda row: str(row["lane_id"])),
        "pooled_model_item_cells": pooled,
        "deterministic_policy_executor": {
            "items": pooled["items"],
            "pairs": pooled["pairs"],
            "end_to_end_item_accuracy": 1.0,
            "end_to_end_pair_accuracy": 1.0,
            "label": "DEFINITIONAL_POLICY_CEILING_NOT_A_LEARNED_EMPIRICAL_BASELINE",
        },
        "service_comparison": {
            "scope": "DESCRIPTIVE_ONLY",
            "causal_model_ablation_claimed": False,
            "reason": "The service stacks and output constraints differ by lane.",
        },
        "raw_prompts_or_responses_in_aggregate": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--workflow-run-url")
    parser.add_argument("--workflow-run-attempt", type=int)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    output = args.out.resolve()
    if output.exists():
        fail(f"refusing to overwrite existing output: {output}")
    result = analyze_challenge(
        args.dataset.resolve(),
        load_json(args.packet.resolve()),
        load_json(args.plan.resolve()),
        args.plan.resolve(),
        [path.resolve() for path in args.run],
        workflow_run_url=args.workflow_run_url,
        workflow_run_attempt=args.workflow_run_attempt,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "study_id": result["study_id"],
                "lanes": len(result["lanes"]),
                "out": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
