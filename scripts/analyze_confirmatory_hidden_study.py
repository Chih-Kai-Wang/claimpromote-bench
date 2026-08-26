#!/usr/bin/env python3
"""Recompute preregistered confirmatory metrics, baselines, and paired tests."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import load_json, load_jsonl  # noqa: E402
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402

Json = dict[str, Any]
ACTIONS = ("ALLOW", "HOLD", "DEMOTE", "ESCALATE")
NO_DECISION = "NO_DECISION"


def fail(message: str) -> None:
    raise SystemExit(f"confirmatory-analysis: {message}")


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - index) + ordered[high] * (index - low)


def _score_core(
    predictions: dict[str, str | None],
    gold_actions: dict[str, str],
    pairs: list[Json],
) -> Json:
    expected_ids = {str(item_id) for pair in pairs for item_id in pair["member_ids"]}
    if set(predictions) != expected_ids or set(gold_actions) != expected_ids:
        fail("prediction, gold, and pair coverage differ")
    confusion = {gold: {predicted: 0 for predicted in (*ACTIONS, NO_DECISION)} for gold in ACTIONS}
    correct: dict[str, bool] = {}
    for item_id in sorted(expected_ids):
        gold = gold_actions[item_id]
        predicted = predictions[item_id]
        bucket = predicted if predicted in ACTIONS else NO_DECISION
        confusion[gold][bucket] += 1
        correct[item_id] = predicted == gold
    action_metrics: Json = {}
    recalls: list[float] = []
    f1_values: list[float] = []
    for action in ACTIONS:
        tp = confusion[action][action]
        support = sum(confusion[action].values())
        predicted_total = sum(confusion[gold][action] for gold in ACTIONS)
        recall = tp / support if support else None
        precision = tp / predicted_total if predicted_total else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if recall is not None and precision + recall
            else 0.0
        )
        if recall is not None:
            recalls.append(recall)
        f1_values.append(f1)
        action_metrics[action] = {
            "correct": tp,
            "support": support,
            "recall": recall,
            "precision": precision,
            "f1": f1,
        }
    pair_correct = {
        str(pair["pair_id"]): all(correct[str(item_id)] for item_id in pair["member_ids"])
        for pair in pairs
    }
    invalid_ids = {str(pair["invalid_id"]) for pair in pairs}
    valid_ids = {str(pair["valid_id"]) for pair in pairs}
    covered = sum(predictions[item_id] in ACTIONS for item_id in expected_ids)
    invalid_allow = sum(predictions[item_id] == "ALLOW" for item_id in invalid_ids)
    valid_allow = sum(predictions[item_id] == "ALLOW" for item_id in valid_ids)
    covered_invalid = sum(predictions[item_id] in ACTIONS for item_id in invalid_ids)
    covered_valid = sum(predictions[item_id] in ACTIONS for item_id in valid_ids)
    return {
        "instances": len(expected_ids),
        "pairs": len(pairs),
        "decision_coverage": covered / len(expected_ids),
        "item_accuracy": sum(correct.values()) / len(correct),
        "pair_accuracy": sum(pair_correct.values()) / len(pair_correct),
        "balanced_action_recall": sum(recalls) / len(recalls) if recalls else None,
        "balanced_action_recall_supported_classes": len(recalls),
        "macro_f1": sum(f1_values) / len(f1_values),
        "end_to_end_false_promotion_rate": invalid_allow / len(invalid_ids),
        "conditional_false_promotion_rate": (
            invalid_allow / covered_invalid if covered_invalid else None
        ),
        "end_to_end_valid_promotion_rate": valid_allow / len(valid_ids),
        "conditional_valid_promotion_rate": valid_allow / covered_valid if covered_valid else None,
        "per_action": action_metrics,
        "confusion": confusion,
        "correctness_by_item": correct,
        "correctness_by_pair": pair_correct,
    }


def _structured_sensitivity(
    predictions: dict[str, str | None],
    gold_actions: dict[str, str],
    pairs: list[Json],
    *,
    replicates: int,
    seed_label: str,
) -> Json:
    factors = sorted({str(pair["factor_id"]) for pair in pairs})
    by_factor = {
        factor: [pair for pair in pairs if str(pair["factor_id"]) == factor] for factor in factors
    }
    factor_metrics = {
        factor: _score_core(
            {item_id: predictions[item_id] for pair in rows for item_id in pair["member_ids"]},
            {item_id: gold_actions[item_id] for pair in rows for item_id in pair["member_ids"]},
            rows,
        )
        for factor, rows in by_factor.items()
    }
    factor_macro = {
        key: sum(float(value[key]) for value in factor_metrics.values()) / len(factor_metrics)
        for key in ("item_accuracy", "pair_accuracy")
    }
    leave_one_factor_out: Json = {}
    for omitted in factors:
        retained = [pair for pair in pairs if str(pair["factor_id"]) != omitted]
        ids = {str(item_id) for pair in retained for item_id in pair["member_ids"]}
        score = _score_core(
            {item_id: predictions[item_id] for item_id in ids},
            {item_id: gold_actions[item_id] for item_id in ids},
            retained,
        )
        leave_one_factor_out[omitted] = {
            "item_accuracy": score["item_accuracy"],
            "pair_accuracy": score["pair_accuracy"],
            "balanced_action_recall": score["balanced_action_recall"],
        }
    seed = int(sha256_bytes(seed_label.encode("utf-8")).removeprefix("sha256:"), 16)
    rng = random.Random(seed)
    bootstrap = {key: [] for key in ("item_accuracy", "pair_accuracy", "balanced_action_recall")}
    for _ in range(replicates):
        sampled: list[Json] = []
        for factor in factors:
            rows = by_factor[factor]
            sampled.extend(rng.choice(rows) for _ in rows)
        # Repeated pairs receive synthetic identities but retain paired members and factor strata.
        sampled_predictions: dict[str, str | None] = {}
        sampled_gold: dict[str, str] = {}
        synthetic_pairs: list[Json] = []
        for index, pair in enumerate(sampled):
            synthetic_members: list[str] = []
            original_members = [str(value) for value in pair["member_ids"]]
            for side, original_id in enumerate(original_members):
                synthetic_id = f"bootstrap-{index}-{side}"
                synthetic_members.append(synthetic_id)
                sampled_predictions[synthetic_id] = predictions[original_id]
                sampled_gold[synthetic_id] = gold_actions[original_id]
            valid_index = original_members.index(str(pair["valid_id"]))
            invalid_index = original_members.index(str(pair["invalid_id"]))
            synthetic_pairs.append(
                {
                    "pair_id": f"bootstrap-{index}",
                    "member_ids": synthetic_members,
                    "valid_id": synthetic_members[valid_index],
                    "invalid_id": synthetic_members[invalid_index],
                    "factor_id": pair["factor_id"],
                }
            )
        score = _score_core(sampled_predictions, sampled_gold, synthetic_pairs)
        for key in bootstrap:
            bootstrap[key].append(float(score[key]))
    intervals = {
        key: {
            "low": _percentile(values, 0.025),
            "high": _percentile(values, 0.975),
            "replicates": replicates,
            "resampling_unit": "pair_stratified_within_each_registered_factor_template",
        }
        for key, values in bootstrap.items()
    }
    templates = sorted({str(pair.get("template_id")) for pair in pairs})
    if not templates or "None" in templates:
        fail("confirmatory pairs lack evaluator-only template_id")
    pair_summaries = [
        {
            "factor_id": str(pair["factor_id"]),
            "template_id": str(pair["template_id"]),
            "item_correct": sum(
                predictions[str(item_id)] == gold_actions[str(item_id)]
                for item_id in pair["member_ids"]
            ),
            "pair_correct": int(
                all(
                    predictions[str(item_id)] == gold_actions[str(item_id)]
                    for item_id in pair["member_ids"]
                )
            ),
        }
        for pair in pairs
    ]

    def cluster_bootstrap(field: str) -> Json:
        labels = sorted({str(row[field]) for row in pair_summaries})
        groups = {label: [row for row in pair_summaries if row[field] == label] for label in labels}
        values = {"item_accuracy": [], "pair_accuracy": []}
        for _ in range(replicates):
            selected = [rng.choice(labels) for _ in labels]
            rows = [row for label in selected for row in groups[label]]
            values["item_accuracy"].append(
                sum(int(row["item_correct"]) for row in rows) / (2 * len(rows))
            )
            values["pair_accuracy"].append(
                sum(int(row["pair_correct"]) for row in rows) / len(rows)
            )
        return {
            key: {
                "low": _percentile(observed, 0.025),
                "high": _percentile(observed, 0.975),
                "replicates": replicates,
                "clusters": len(labels),
                "resampling_unit": field,
            }
            for key, observed in values.items()
        }

    factor_cluster = cluster_bootstrap("factor_id")
    template_cluster = cluster_bootstrap("template_id")
    multiway_values = {"item_accuracy": [], "pair_accuracy": []}
    while len(multiway_values["item_accuracy"]) < replicates:
        factor_weights = Counter(rng.choice(factors) for _ in factors)
        template_weights = Counter(rng.choice(templates) for _ in templates)
        weighted = [
            (row, factor_weights[str(row["factor_id"])] * template_weights[str(row["template_id"])])
            for row in pair_summaries
        ]
        total_pairs = sum(weight for _row, weight in weighted)
        if total_pairs == 0:
            continue
        multiway_values["item_accuracy"].append(
            sum(int(row["item_correct"]) * weight for row, weight in weighted) / (2 * total_pairs)
        )
        multiway_values["pair_accuracy"].append(
            sum(int(row["pair_correct"]) * weight for row, weight in weighted) / total_pairs
        )
    multiway = {
        key: {
            "low": _percentile(values, 0.025),
            "high": _percentile(values, 0.975),
            "replicates": replicates,
            "resampling_unit": "crossed_factor_by_template_product_weights",
        }
        for key, values in multiway_values.items()
    }
    robust_envelope = {
        key: {
            "low": min(
                intervals[key]["low"],
                factor_cluster[key]["low"],
                template_cluster[key]["low"],
                multiway[key]["low"],
            ),
            "high": max(
                intervals[key]["high"],
                factor_cluster[key]["high"],
                template_cluster[key]["high"],
                multiway[key]["high"],
            ),
            "selection_rule": "outer_envelope_across_all_preregistered_composition_resamples",
        }
        for key in ("item_accuracy", "pair_accuracy")
    }
    return {
        "factor_template_metrics": {
            factor: {
                key: value[key]
                for key in ("item_accuracy", "pair_accuracy", "balanced_action_recall")
            }
            for factor, value in factor_metrics.items()
        },
        "factor_template_macro": factor_macro,
        "leave_one_factor_template_out": leave_one_factor_out,
        "pair_cluster_stratified_bootstrap_95pct": intervals,
        "factor_cluster_bootstrap_95pct": factor_cluster,
        "template_cluster_bootstrap_95pct": template_cluster,
        "crossed_factor_template_multiway_bootstrap_95pct": multiway,
        "robust_composition_envelope_95pct": robust_envelope,
        "interval_interpretation": (
            "Benchmark-composition sensitivity only; not model sampling reliability or "
            "naturalistic generalization."
        ),
    }


def exact_pair_blocked_swap(
    correct_a: dict[str, bool],
    correct_b: dict[str, bool],
    pairs: list[Json],
) -> Json:
    """One-sided exact sign permutation, swapping complete two-member pair vectors."""

    expected_ids = {str(item_id) for pair in pairs for item_id in pair["member_ids"]}
    if set(correct_a) != expected_ids or set(correct_b) != expected_ids:
        fail("pair-blocked correctness vectors differ in item coverage")
    pair_differences: list[int] = []
    for pair in pairs:
        members = [str(item_id) for item_id in pair["member_ids"]]
        pair_differences.append(
            sum(correct_a[item_id] for item_id in members)
            - sum(correct_b[item_id] for item_id in members)
        )
    observed = sum(pair_differences)
    nonzero = [abs(value) for value in pair_differences if value]
    distribution: Counter[int] = Counter({0: 1})
    for magnitude in nonzero:
        updated: Counter[int] = Counter()
        for total, count in distribution.items():
            updated[total + magnitude] += count
            updated[total - magnitude] += count
        distribution = updated
    denominator = 1 << len(nonzero)
    upper_tail = sum(count for total, count in distribution.items() if total >= observed)
    p_value = upper_tail / denominator
    return {
        "pairs": len(pairs),
        "nonzero_pair_differences": len(nonzero),
        "sum_item_correctness_difference": observed,
        "action_accuracy_difference": observed / (2 * len(pairs)),
        "one_sided_exact_p": p_value,
        "test_unit": "controlled_pair",
        "permutation": "swap_complete_two_member_correctness_vectors_within_pair",
    }


def holm_adjust(tests: list[Json]) -> list[Json]:
    ordered = sorted(enumerate(tests), key=lambda value: float(value[1]["one_sided_exact_p"]))
    adjusted = [0.0] * len(tests)
    running = 0.0
    for rank, (original_index, test) in enumerate(ordered):
        running = max(running, min(1.0, (len(tests) - rank) * float(test["one_sided_exact_p"])))
        adjusted[original_index] = running
    result = deepcopy(tests)
    for row, value in zip(result, adjusted, strict=True):
        row["holm_adjusted_p"] = value
    return result


def _run_predictions(
    path: Path, plan: Json, packet: Json
) -> tuple[str, dict[str, str | None], dict[str, str | None]]:
    rows = load_jsonl(path)
    expected_ids = {str(row["item_id"]) for row in packet["records"]}
    if len(rows) != len(expected_ids):
        fail(f"run has incomplete record count: {path}")
    lanes = {str(lane["lane_id"]) for lane in plan["formal_lanes"]}
    observed_lanes = {str(row.get("lane_id")) for row in rows}
    if len(observed_lanes) != 1 or not observed_lanes <= lanes:
        fail(f"run lane is not registered: {path}")
    lane_id = next(iter(observed_lanes))
    raw: dict[str, str | None] = {}
    postgate: dict[str, str | None] = {}
    for row in rows:
        item_id = str(row["item_id"])
        if item_id in raw or item_id not in expected_ids:
            fail(f"run item coverage is malformed: {item_id}")
        raw_decision = row.get("raw_decision")
        postgate_decision = row.get("postgate_decision")
        raw[item_id] = (
            str(raw_decision.get("action"))
            if row.get("parse_status") == "OK" and isinstance(raw_decision, dict)
            else None
        )
        postgate[item_id] = (
            str(postgate_decision.get("action"))
            if row.get("parse_status") == "OK" and isinstance(postgate_decision, dict)
            else None
        )
    if set(raw) != expected_ids:
        fail(f"run item IDs differ from packet: {path}")
    return lane_id, raw, postgate


def analyze(
    test_dataset: Path,
    packet: Json,
    plan: Json,
    baseline_report: Json,
    run_paths: list[Path],
) -> Json:
    expected_analysis = plan.get("statistics", {}).get("analysis_script_sha256")
    observed_analysis = sha256_file(Path(__file__))
    if expected_analysis is not None and expected_analysis != observed_analysis:
        fail("analysis script differs from the frozen plan")
    baseline_payload = deepcopy(baseline_report)
    observed_baseline_sha = baseline_payload.pop("predictions_sha256", None)
    if observed_baseline_sha != sha256_bytes(canonical_json(baseline_payload).encode("utf-8")):
        fail("baseline prediction digest mismatch")
    if baseline_report.get("contains_test_gold") is not False:
        fail("baseline artifact does not preserve the test-gold boundary")
    pairs = load_json(test_dataset / "pairs.json")
    if not isinstance(pairs, list):
        fail("pairs.json must be a list")
    gold_actions = {
        str(row["id"]): str(row["decision"]["action"])
        for row in load_jsonl(test_dataset / "gold.jsonl")
    }
    baseline_rows = baseline_report.get("records")
    if not isinstance(baseline_rows, list):
        fail("baseline records are malformed")
    baseline_names = tuple(plan["baselines"]["registered_predictors"])
    baseline_predictions = {
        name: {str(row["item_id"]): str(row["predictions"][name]) for row in baseline_rows}
        for name in baseline_names
    }
    replicates = int(plan["statistics"]["bootstrap_replicates"])
    seed_label = str(plan["statistics"]["bootstrap_seed_label"])
    scored: Json = {}
    correctness: dict[str, dict[str, bool]] = {}
    for name, predictions in baseline_predictions.items():
        core = _score_core(predictions, gold_actions, pairs)
        correctness[name] = core.pop("correctness_by_item")
        core.pop("correctness_by_pair")
        core["structured_sensitivity"] = _structured_sensitivity(
            predictions,
            gold_actions,
            pairs,
            replicates=replicates,
            seed_label=f"{seed_label}:{name}",
        )
        scored[name] = {"raw": core, "kind": "DETERMINISTIC_BASELINE"}

    raw_by_lane: dict[str, dict[str, str | None]] = {}
    for path in run_paths:
        lane_id, raw, postgate = _run_predictions(path, plan, packet)
        if lane_id in raw_by_lane:
            fail(f"duplicate lane run: {lane_id}")
        raw_by_lane[lane_id] = raw
        raw_core = _score_core(raw, gold_actions, pairs)
        correctness[lane_id] = raw_core.pop("correctness_by_item")
        raw_core.pop("correctness_by_pair")
        raw_core["structured_sensitivity"] = _structured_sensitivity(
            raw,
            gold_actions,
            pairs,
            replicates=replicates,
            seed_label=f"{seed_label}:{lane_id}:raw",
        )
        postgate_core = _score_core(postgate, gold_actions, pairs)
        postgate_core.pop("correctness_by_item")
        postgate_core.pop("correctness_by_pair")
        scored[lane_id] = {
            "kind": "REGISTERED_MODEL_LANE",
            "raw": raw_core,
            "postgate_conformance_only": postgate_core,
            "run_sha256": sha256_file(path),
        }
    expected_lanes = {str(lane["lane_id"]) for lane in plan["formal_lanes"]}
    if set(raw_by_lane) != expected_lanes:
        fail("complete registered lane family was not supplied")

    comparators = tuple(plan["statistics"]["confirmatory_baseline_comparators"])
    tests: list[Json] = []
    for lane_id in sorted(expected_lanes):
        for comparator in comparators:
            row = exact_pair_blocked_swap(correctness[lane_id], correctness[comparator], pairs)
            row.update({"model_lane": lane_id, "baseline": comparator})
            tests.append(row)
    if len(tests) != int(plan["statistics"]["confirmatory_family_size"]):
        fail("confirmatory multiple-testing family size changed")
    adjusted_tests = holm_adjust(tests)
    minimum_effect = float(plan["statistics"]["minimum_superiority_effect"])
    for row in adjusted_tests:
        row["minimum_superiority_effect"] = minimum_effect
        row["superiority_supported"] = (
            float(row["action_accuracy_difference"]) >= minimum_effect
            and float(row["holm_adjusted_p"]) < 0.05
        )
    model_contrast = None
    if len(expected_lanes) == 2:
        a, b = sorted(expected_lanes)
        model_contrast = {
            "lane_a": a,
            "lane_b": b,
            **exact_pair_blocked_swap(correctness[a], correctness[b], pairs),
        }

    report: Json = {
        "schema_version": "1.0.0",
        "study_id": str(plan["study_id"]),
        "analysis_status": "CONFIRMATORY_IF_ALL_FROZEN_BOUNDARIES_VALIDATE",
        "dataset_manifest_sha256": sha256_file(test_dataset / "manifest.json"),
        "packet_sha256": str(packet["packet_sha256"]),
        "baseline_predictions_sha256": observed_baseline_sha,
        "analysis_script_sha256": observed_analysis,
        "scores": scored,
        "confirmatory_item_correctness_tests": {
            "family_size": len(adjusted_tests),
            "method": (
                "one-sided exact pair-blocked whole-vector swap permutation; Holm adjustment "
                "across the complete frozen family"
            ),
            "tests": adjusted_tests,
        },
        "descriptive_model_contrast": model_contrast,
        "gate_interpretation": (
            "Postgate scores are implementation-conformance checks because the deterministic gate "
            "uses the same policy oracle as the benchmark labels; raw model scores carry the "
            "claims."
        ),
        "raw_prompts_or_responses_in_aggregate": False,
    }
    report["aggregate_sha256"] = sha256_bytes(canonical_json(report).encode("utf-8"))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-dataset", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--baselines", type=Path, required=True)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(
        args.test_dataset.resolve(),
        load_json(args.packet.resolve()),
        load_json(args.plan.resolve()),
        load_json(args.baselines.resolve()),
        [path.resolve() for path in args.run],
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["analysis_status"],
                "aggregate_sha256": report["aggregate_sha256"],
                "confirmatory_tests": report["confirmatory_item_correctness_tests"]["family_size"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
